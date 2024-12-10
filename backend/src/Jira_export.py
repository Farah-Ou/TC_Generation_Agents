from dotenv import load_dotenv
import os
from jira import JIRA

from src.Jira_import import extract_scenarios_and_titles_description

os.environ["PYTHONIOENCODING"] = "utf-8"
# load_dotenv(r".env")

env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_file_path)

# Retrieve the GRAPHRAG_API_KEY from the environment
jira_token = os.getenv("JIRA_TOKEN")

# Check if the environment variable is set
if jira_token is None:
    raise ValueError("JIRA_TOKEN environment variable is not set.")

# Set the environment variable explicitly
os.environ["JIRA_TOKEN"] = jira_token

# Function to link a ticket to another
def create_link_tickets(user_paths, df_res, link_type="Relates"):
    print("Starting to create and link tickets...")
    
    # Authentication
    jira_url = user_paths.get('jira_url')
    jira_user = user_paths.get('jira_user')
    jira_token = os.getenv("JIRA_TOKEN")
    project_key = user_paths.get("project_key")
    ISSUE_TYPE = 'Task'  # Change to the appropriate issue type
    ticket_name_field = user_paths.get('ticket_name_field')  # The status you want to set later

    # Debugging: Check user paths
    print(f"Jira URL: {jira_url}, Jira User: {jira_user}, Project Key: {project_key}")

    # Create Jira instance
    jira_options = {'server': jira_url}
    try:
        jira = JIRA(options=jira_options, basic_auth=(jira_user, jira_token))
        print("Jira connection established successfully.")
    except Exception as e:
        print(f"Failed to authenticate with Jira: {e}")
        return

    # Fetch project to ensure the connection is correct
    try:
        project = jira.project(project_key)
        print(f"Connected to project: {project_key}")
    except Exception as e:
        print(f"Failed to connect to project {project_key}: {e}")
        return

    # Iterate through each row in df_res and update the Jira ticket
    for index, row in df_res.iterrows():
        print(f"Processing row {index + 1}: {row}")  # Debugging: print the current row
        target_issue_key = row['id_US']
        test_case_content = row['Test Cases']
        scenario_data = extract_scenarios_and_titles_description(test_case_content)

        # Debugging: Print scenario data
        print(f"Extracted scenario data: {scenario_data}")

        for idx, data in enumerate(scenario_data, start=1):
            summary = data['title']
            description = data['description']
            print(f"Creating issue {idx}: {summary} - {description}")  # Debugging: print issue being created

            # Create the new issue without setting the status directly
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': ISSUE_TYPE},
            }

            try:
                new_issue = jira.create_issue(fields=issue_dict)
                print(f"Test case '{summary}' created with key: {new_issue.key}")
            except Exception as e:
                print(f"Failed to create issue for {summary}: {e}")
                continue

            # Transition the issue to the desired status
            try:
                transitions = jira.transitions(new_issue)
                print(f"Available transitions for issue {new_issue.key}: {transitions}")

                # Check if the desired status exists in the transitions
                for t in transitions:
                    if t['name'] == ticket_name_field:  # Match the transition with the status name
                        jira.transition_issue(new_issue, t['id'])
                        print(f"Transitioned issue {new_issue.key} to status: {ticket_name_field}")
                        break
                else:
                    print(f"No transition found for status: {ticket_name_field}")
            except Exception as e:
                print(f"Failed to transition issue {new_issue.key}: {e}")

            # Linking the new issue to the target issue
            try:
                jira.create_issue_link(
                    type=link_type,
                    inwardIssue=new_issue.key,
                    outwardIssue=target_issue_key
                )
                print(f"Linked {new_issue.key} to {target_issue_key} with link type '{link_type}'.")
            except Exception as e:
                print(f"Failed to link {new_issue.key} to {target_issue_key}: {e}")

    print("All tickets linked successfully.")
