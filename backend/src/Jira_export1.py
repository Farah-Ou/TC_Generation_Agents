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
    ### Authentication
    jira_url = user_paths.get('jira_url')
    jira_user = user_paths.get('jira_user')
    jira_token = os.getenv("JIRA_TOKEN")
    project_key = user_paths.get("project_key")
    ISSUE_TYPE = 'Task'
    ticket_name_field = user_paths.get('ticket_name_field')  # The status you want to set later
    
    jira_options = {'server': jira_url}
    jira = JIRA(options=jira_options, basic_auth=(jira_user, jira_token))

    project = jira.project(project_key)

    # Iterate through each row in df_res and update the Jira ticket
    for index, row in df_res.iterrows():
        target_issue_key = row['id_US']
        test_case_content = row['Test Cases']
        scenario_data = extract_scenarios_and_titles_description(test_case_content)

        for idx, data in enumerate(scenario_data, start=1):
            summary = data['title']
            description = data['description']

            # Create the new issue without setting the status directly
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': ISSUE_TYPE},
            }

            new_issue = jira.create_issue(fields=issue_dict)
            print(f"Test case '{summary}' created with key: {new_issue.key}")

            # Transition the issue to the desired status
            # Here, you would need the transition ID for the status you want to set
            # Assuming 'ticket_name_field' contains the status name you want to set
            transition = jira.transitions(new_issue)
            print("******************************************************")
            print(transition)
            print("******************************************************")
            print(ticket_name_field)
            for t in transition:
                if t['name'] == ticket_name_field:  # Match the transition with the status name
                    jira.transition_issue(new_issue, t['id'])
                    print(f"Transitioned issue {new_issue.key} to status: {ticket_name_field}")
                    break
            
            # Linking the new issue to the target issue
            source_issue_key = new_issue.key
            try:
                jira.create_issue_link(
                    type=link_type,
                    inwardIssue=source_issue_key,
                    outwardIssue=target_issue_key
                )
                print(f"Linked {source_issue_key} to {target_issue_key} with link type '{link_type}'.")
            except Exception as e:
                print(f"Failed to link {source_issue_key} to {target_issue_key}: {e}")

    print("All tickets linked successfully.")



# from dotenv import load_dotenv
# import os
# from jira import JIRA

# from src.Jira_import import extract_scenarios_and_titles_description

# os.environ["PYTHONIOENCODING"] = "utf-8"
# # load_dotenv(r".env")

# env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
# load_dotenv(env_file_path)

# # Retrieve the GRAPHRAG_API_KEY from the environment
# jira_token = os.getenv("JIRA_TOKEN")

# # Check if the environment variable is set
# if jira_token is None:
#     raise ValueError("JIRA_TOKEN environment variable is not set.")

# # Set the environment variable explicitly
# os.environ["JIRA_TOKEN"] = jira_token


# # Function to link a ticket to another
# def create_link_tickets(user_paths, df_res, link_type="Relates"):
#     ### Authentic
#     jira_url = user_paths.get('jira_url')
#     jira_user = user_paths.get('jira_user')
#     jira_token = os.getenv("JIRA_TOKEN")
#     project_key = user_paths.get("project_key")
#     ISSUE_TYPE = 'Task'  
#     status = user_paths.get('ticket_name_field')
    
#     jira_options = {'server': jira_url}
#     jira = JIRA(options=jira_options, basic_auth=(jira_user, jira_token))
    
#     project = jira.project(project_key)

    
#     # Iterate through each row in df_res and update the Jira ticket
#     for index, row in df_res.iterrows():
#         target_issue_key = row['id_US']
#         test_case_content = row['Test Cases']
#         scenario_data = extract_scenarios_and_titles_description(test_case_content)

#         for idx, data in enumerate(scenario_data, start=1):
#             summary = data['title']
#             description = data['description']

#             issue_dict = {
#                 'project': {'key': project_key},
#                 'summary': summary,
#                 'description': description,
#                 'issuetype': {'name': ISSUE_TYPE},
#                 'status': {'name' : status},
#             }

#             new_issue = jira.create_issue(fields=issue_dict)
#             print(f"Test case '{summary}' created with key: {new_issue.key}")
            
#             source_issue_key = new_issue.key
            
#             try:
#                 jira.create_issue_link(
#                     type=link_type, 
#                     inwardIssue=source_issue_key,
#                     outwardIssue=target_issue_key
#                 )
#                 print(f"Linked {source_issue_key} to {target_issue_key} with link type '{link_type}'.")
#             except Exception as e:
#                 print(f"Failed to link {source_issue_key} to {target_issue_key}: {e}")

#     print("All tickets linked successfully.")