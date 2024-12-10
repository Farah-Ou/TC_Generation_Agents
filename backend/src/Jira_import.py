import os
import pandas as pd
from jira import JIRA
import re

def Jira_import(user_paths, project_folder_path, ticket_name_field="To Test"):
    ### Define credentials
    # Jira server URL and credentials
    jira_url = user_paths.get('jira_url')
    jira_user = user_paths.get('jira_user')
    jira_token = os.getenv("JIRA_TOKEN")
    
    # Connect to Jira
    jira = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
    
    # Access the project by project key (or project ID)
    project_key = user_paths.get('project_key')
    project = jira.project(project_key)

    ### Define path where the text file of US will be saved
    imported_US = os.path.join(project_folder_path, "Imported_US.txt")
    print(f"1 ************************* {imported_US} ****************")
    
    df = pd.DataFrame(columns=['US_ID', 'Titre', 'Description', 'Règles de gestion', "Critères d'acceptance"])
    ids_list = []
    titles_list = []
    description_list = []
    RG_list = []
    CA_list = []

    ### Retrieve TICKETS FIELDS AND SAVE THEM TO A TEXT FILE
    # Create a dictionary mapping field names to their IDs
    fields = jira.fields()
    field_name_to_id = {field['name']: field['id'] for field in fields}
    print(f"2 ************************* {field_name_to_id} ****************")

    # Define the custom field names you want to retrieve
    custom_field_names = ["Règles de Gestion", "Critères d'Acceptance"]
    print(f"3 ************************* {custom_field_names} ****************")

    # Define the JQL query for the project
    jql_query = f'project = {project_key}'
    tickets = jira.search_issues(jql_query, maxResults=1000)
    
    # Open the file to write the information with proper encoding
    with open(imported_US, "w", encoding='utf-8') as file:
        print(f" ************************* file opened ****************")
        for ticket in tickets:
            print(f"************************* {ticket.fields.status.name} ****************")
            if ticket.fields.status.name == ticket_name_field:
                # Retrieve title and description, ensuring they are correctly decoded
                ticket_key = ticket.key
                title = ticket.fields.summary
                description = ticket.fields.description if ticket.fields.description else ""  # Ensure description is never None
                
                ## save them for future dataframe identification of TC related to US
                ids_list.append(ticket_key)
                titles_list.append(title)
                description_list.append(description)
                
                print("\n appended to list Ticket ID:", ticket_key)

                # Write title and description to the file
                file.write(f"Ticket ID: {ticket.key}\n")
                file.write(f"Title: {title}\n")
                file.write(f"Description: {description}\n")
                print("saved to file Ticket ID:", ticket_key)

                # Retrieve each custom field's value by name
                for field_name in custom_field_names:
                    field_id = field_name_to_id.get(field_name)
                    if field_id:
                        field_value = getattr(ticket.fields, field_id, None)
                        field_value = field_value if field_value is not None else "Field not found"  # Replace None with a default value
                        file.write(f"{field_name} ({field_id}): {field_value}\n")
                        
                        if field_name == "Règles de Gestion":
                            RG_list.append(field_value)
                        elif field_name == "Critères d'Acceptance":
                            CA_list.append(field_value)
                    else:
                        file.write(f"{field_name} not found\n")
    
                file.write("\n" + "="*40 + "\n\n")

    # Create DataFrame
    df = pd.DataFrame({
        'US_ID': ids_list,
        'Titre': titles_list,
        'Description': description_list,
        'Règles de gestion': RG_list,
        "Critères d'acceptance": CA_list
    })

    print(f"Ticket details have been saved to {imported_US}.")

    return imported_US, ids_list, titles_list, df



def extract_scenarios_and_titles_description(Test_case):
    # Updated regular expression to match the original and new patterns
    pattern = r"(" \
              r"### Cas de test \d+: .*?(\n(?:.|\n)*?)(?=### Cas de test \d+:|$)" \
              r"(Scenario \d+ : .*?)(?=Scenario \d+ :|\Z) |"  \
              r"(Test Case \d+ : .*?)(?=\n) |" \
              r"(TC \d+: .*?)(?=\n) |" \
              r"(Cas de Test \d+ : .*?)(?=\n) |" \
              r"(CT \d+ : .*?)(?=\n) |" \
              r"(Scénario \d+ : .*?)(?=\n) |" \
              r"(Cas Passant : .*?)(?=\n) |" \
              r"(Cas non passant \d+ : .*?)(?=\n))"
    
    # Extracting all scenarios
    scenarios = re.findall(pattern, Test_case, re.DOTALL)

    scenario_data = []
    for scenario in scenarios:
        # Flattening the tuple and filtering out empty matches
        scenario = [s for s in scenario if s]
        
        if scenario:
            # Each scenario should have one matched pattern, we handle the first match
            scenario_text = scenario[0]
            lines = scenario_text.strip().split('\n', 1)  # Split into first line and the rest
            title = lines[0].strip()  # First line is the title
            description = lines[1].strip() if len(lines) > 1 else ""
            scenario_data.append({"title": title, "description": description})
    
    return scenario_data




# ------------------------------------------------------------------------------------
# def extract_scenarios_and_titles_description(Test_case):
#     # Regular expression to extract scenarios
#     pattern = r"(Scenario \d+ : .*?)(?=Scenario \d+ :|\Z)"
    
#     # Extracting all scenarios
#     scenarios = re.findall(pattern, Test_case, re.DOTALL)
    
#     scenario_data = []
#     for scenario in scenarios:
#         lines = scenario.strip().split('\n', 1)  # Split into first line and the rest
#         title = lines[0].strip()  # First line is the title
#         description = lines[1].strip() if len(lines) > 1 else ""
#         scenario_data.append({"title": title, "description": description})
    
#     return scenario_data

# ------------------------------------------------------------------------------------

# def extract_scenarios_and_titles_description(Test_case):
#     # Updated regular expression to match the pattern
#     pattern = r"([A-Za-z0-9\s]+: [A-Za-z0-9\s]+)(?=\n)|([A-Za-z0-9\s]+(?:\n[A-Za-z0-9\s]+)*)"
    
#     # Extracting all scenarios using the regex pattern
#     scenarios = re.findall(pattern, Test_case)
    
#     scenario_data = []
#     for scenario in scenarios:
#         title = scenario[0].strip() if scenario[0] else scenario[1].split('\n', 1)[0].strip()
#         description = scenario[1].strip() if scenario[1] else ""
        
#         scenario_data.append({"title": title, "description": description})
    
#     return scenario_data


#  ------------------------------------------------------------------------------------
# import os
# import pandas as pd
# from jira import JIRA
# import re

# def Jira_import(user_paths, project_folder_path, ticket_name_field="To Test"):
#     ### Define credentials
#     # Jira server URL and credentials
#     jira_url = user_paths.get('jira_url')
#     jira_user = user_paths.get('jira_user')
#     jira_token = os.getenv("JIRA_TOKEN")
    
#     # Connect to Jira
#     jira = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
    
#     # Access the project by project key (or project ID)
#     project_key = user_paths.get('project_key')
#     project = jira.project(project_key)

#     ### Define path where the text file of US will be saved
#     imported_US = os.path.join(project_folder_path, "Imported_US.txt")
#     print(f"1 ************************* {imported_US} ****************")
    
#     df = pd.DataFrame(columns=['US_ID', 'Titre', 'Description', 'Règles de gestion', "Critères d'acceptance"])
#     ids_list = []
#     titles_list = []
#     description_list = []
#     RG_list = []
#     CA_list = []

#     ### Retrieve TICKETS FIELDS AND SAVE THEM TO A TEXT FILE
#     # Create a dictionary mapping field names to their IDs
#     fields = jira.fields()
#     field_name_to_id = {field['name']: field['id'] for field in fields}
#     print(f"2 ************************* {field_name_to_id} ****************")

#     # Define the custom field names you want to retrieve
#     custom_field_names = ["Règles de Gestion", "Critères d'Acceptance"]
#     print(f"3 ************************* {custom_field_names} ****************")

#     # Define the JQL query for the project
#     jql_query = f'project = {project_key}'
#     tickets = jira.search_issues(jql_query, maxResults=1000)
    
#     # Open the file to write the information with proper encoding
#     with open(imported_US, "w", encoding='utf-8') as file:
#         print(f" ************************* file opened ****************")
#         for ticket in tickets:
#             print(f"************************* {ticket.fields.status.name} ****************")
#             if ticket.fields.status.name == ticket_name_field:
#                 # Retrieve title and description, ensuring they are correctly decoded
#                 ticket_key = ticket.key
#                 title = ticket.fields.summary
#                 description = ticket.fields.description or ""  # Ensure description is never None
                
#                 ## save them for future dataframe identification of TC related to US
#                 ids_list.append(ticket_key)
#                 titles_list.append(title)
#                 description_list.append(description)
                
#                 print("\n appended to list Ticket ID:", ticket_key)

#                 # Write title and description to the file
#                 file.write(f"Ticket ID: {ticket.key}\n")
#                 file.write(f"Title: {title}\n")
#                 file.write(f"Description: {description}\n")
#                 print("saved to file Ticket ID:", ticket_key)

#                 # Retrieve each custom field's value by name
#                 for field_name in custom_field_names:
#                     field_id = field_name_to_id.get(field_name)
#                     if field_id:
#                         field_value = getattr(ticket.fields, field_id, 'Field not found')
#                         # Ensure proper handling of special characters
#                         file.write(f"{field_name} ({field_id}): {field_value}\n")
#                         if field_name == "Règles de Gestion":
#                             RG_list.append(field_value)
#                         elif field_name == "Critères d'Acceptance":
#                             CA_list.append(field_value)
#                     else:
#                         file.write(f"{field_name} not found\n")
    
#                 file.write("\n" + "="*40 + "\n\n")

#     # Create DataFrame
#     df = pd.DataFrame({
#         'US_ID': ids_list,
#         'Titre': titles_list,
#         'Description': description_list,
#         'Règles de gestion': RG_list,
#         "Critères d'acceptance": CA_list
#     })

#     print(f"Ticket details have been saved to {imported_US}.")

#     return imported_US, ids_list, titles_list, df

# def extract_scenarios_and_titles_description(Test_case):
#     # Regular expression to extract scenarios
#     pattern = r"(Scenario \d+ : .*?)(?=Scenario \d+ :|\Z)"
    
#     # Extracting all scenarios
#     scenarios = re.findall(pattern, Test_case, re.DOTALL)
    
#     scenario_data = []
#     for scenario in scenarios:
#         lines = scenario.strip().split('\n', 1)  # Split into first line and the rest
#         title = lines[0].strip()  # First line is the title
#         description = lines[1].strip() if len(lines) > 1 else ""
#         scenario_data.append({"title": title, "description": description})
    
#     return scenario_data


# ------------------------------------------------------------------------------------


# from dotenv import load_dotenv
# import os
# import pandas as pd
# import requests

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



# from jira import JIRA
# import re

# def Jira_import(user_paths, project_folder_path , ticket_name_field = "To Test" ):
#     ### Define credentials
#     # Jira server URL and credentials
#     jira_url = user_paths.get('jira_url')
#     jira_user = user_paths.get('jira_user')

#     jira_token =  os.getenv("JIRA_TOKEN")
    
#     # Connect to Jira
#     jira = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
    
#     # Access the project by project key (or project ID)
#     project_key = user_paths.get('project_key')
#     project = jira.project(project_key)

#     ### Define path where the text file of US will be saved
#     imported_US = os.path.join(project_folder_path, "Imported_US.txt") 
#     print(f"1 ************************* {imported_US} ****************")
#     df = pd.DataFrame(columns = ['US_ID', 'Titre', 'Description', 'Règles de gestion', "Critères d'acceptance"])
#     ids_list = []
#     titles_list = []
#     description_list = []
#     RG_list = []
#     CA_list = []
    

#     ###  Retrieve TICKETS FIELDS AND SAVE THEM TO A TEXT FILE
#     # Create a dictionary mapping field names to their IDs
#     fields = jira.fields()
#     field_name_to_id = {field['name']: field['id'] for field in fields}
#     print(f"2 ************************* {field_name_to_id} ****************")

#     # Define the custom field names you want to retrieve
#     custom_field_names = ["Règles de Gestion", "Critères d'Acceptance"]
#     print(f"3 ************************* {custom_field_names} ****************")

#     # Define the JQL query for the project
#     jql_query = f'project = {project_key}' 
#     tickets = jira.search_issues(jql_query, maxResults=1000) 
    
#     # Open the file to write the information
#     with open(imported_US, "w") as file:
#         print(f" ************************* file opnened ****************")
#         for ticket in tickets:
#             print(f"************************* {ticket.fields.status.name} ****************")
#             if ticket.fields.status.name == ticket_name_field:
#                 # Retrieve title and description
#                 ticket_key = ticket.key
#                 title = ticket.fields.summary
#                 description = ticket.fields.description

#                 ## save them for future dataframe identification of TC related to US
#                 ids_list.append(ticket_key)
#                 titles_list.append(title)
#                 description_list.append(description)
                
#                 print("\n appended to list Ticket ID:", ticket_key)

#                 # Write title and description to the file
#                 file.write(f"Ticket ID: {ticket.key}\n")
#                 file.write(f"Title: {title}\n")
#                 file.write(f"Description: {description}\n")
#                 print("saved to file Ticket ID:", ticket_key)

#                 # Retrieve each custom field's value by name
#                 for field_name in custom_field_names:
#                     field_id = field_name_to_id.get(field_name)
#                     if field_id:
#                         field_value = getattr(ticket.fields, field_id, 'Field not found')
#                         file.write(f"{field_name} ({field_id}): {field_value}\n")
#                         if field_name == "Règles de Gestion":
#                             RG_list.append(field_value)
#                         elif field_name == "Critères d'Acceptance":
#                             CA_list.append(field_value)
#                     else:
#                         file.write(f"{field_name} not found\n")
    
#                 file.write("\n" + "="*40 + "\n\n")

#     df = pd.DataFrame({
#         'US_ID': ids_list,
#         'Titre': titles_list,
#         'Description': description_list,
#         'Règles de gestion': RG_list,
#         "Critères d'acceptance": CA_list
#         })

#     print(f"Ticket details have been saved to {imported_US}.")

#     return imported_US, ids_list, titles_list, df

# def extract_scenarios_and_titles_description(Test_case) :
#     # Regular expression to extract scenarios
#     pattern = r"(Scenario \d+ : .*?)(?=Scenario \d+ :|\Z)"
    
#     # Extracting all scenarios
#     scenarios = re.findall(pattern, Test_case, re.DOTALL)
    

#     # # Printing each scenario
#     # for idx, scenario in enumerate(scenarios, start=1):
#     #     print(f"Scenario {idx}:\n{scenario.strip()}\n")

#     scenario_data = []
#     for scenario in scenarios:
#         lines = scenario.strip().split('\n', 1)  # Split into first line and the rest
#         title = lines[0].strip()  # First line is the title
#         description = lines[1].strip() if len(lines) > 1 else ""
#         scenario_data.append({"title": title, "description": description})
    
#     return scenario_data