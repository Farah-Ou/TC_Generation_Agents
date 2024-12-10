from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os
from fastapi.middleware.cors import CORSMiddleware
import json
import pandas as pd
import logging
from dotenv import load_dotenv
import traceback 
from typing import Optional


from src.Jira_export import create_link_tickets
from src.Jira_import import Jira_import, extract_scenarios_and_titles_description
from src.Files_treatment import concatenate_json_files_to_text, concatenate_text_pdf_files, move_files
from src.Graph_creation import Create_Graph_folder
from src.Agents_module import generate_TC, define_tc_reflection_module, Generate_prompt, define_prompt_generation_module, run_global_query, run_local_query

logging.basicConfig(level=logging.DEBUG)

os.environ["PYTHONIOENCODING"] = "utf-8"
load_dotenv(r".env")

api_key = os.environ.get("GRAPHRAG_API_KEY")
jira_token = os.environ.get("GRAPHRAG_API_KEY")

# Print the value of GRAPHRAG_API_KEY
print(api_key)

## Default paths created for the graphs
output_folder= "input"
graph_context="project_contxt_graph"
graph_US='us_graph'
Graphs_folder_path = "Graphs"
save_output_folder = "Generated_output"

Visual_graph_context="Context-Graph-Visual"
Visual_graph_US='US-Graph-Visual'


artifacts_graph_visualizer_path=os.path.join("graphrag-visualizer","public","artifacts")
# US_Visual_graph_folder = os.path.join("Visual_graphs","US_Graph_Visual", artifacts_graph_visualizer_path)
# Contxt_Visual_graph_folder = os.path.join("Visual_graphs","Context_Graph_Visual", artifacts_graph_visualizer_path)

US_Visual_graph_folder = os.path.join("..",Visual_graph_US,artifacts_graph_visualizer_path)
Contxt_Visual_graph_folder = os.path.join("..",Visual_graph_context, artifacts_graph_visualizer_path)

## Models Config
llm_config_gpt4turbo = {"model": "gpt-4-turbo"} ## Mainly used for the graph creation and TC generation phase 
llm_config_gpt4o_mini = {"model": "gpt-4o-mini"} ## Used for context extraction and prompt creation phase 
llm_config_gpt4o =  {"model": "gpt-4o"} ## Good for non english text, fast, less expensive than turbo

### TC GENERATION TEXT DEFAULT
TC_gen_msg = '''Tu es un générateur de Cas de Test en Gherkin. Etant donné un User Story, génère les cas de Test qui lui sont associés en tenant 
compte surtout de ses critères d'accpetance, ainsi que des informations pertinentes liées au projet. Fait attention surtout aux règles à respecter pour 
une fonctionnalité donnée qui proviennent d'une autre US mais qui est liée. \n '''
output_format_1 = '''
US: Créer mon compte : Authentification à l'application
Scenario 1 : Cas passant : Authentification réussie
[Précondition] : Le beneficiaire possède deja un compte
Etant donné que, le beneficiaire est sur la page d'accueil,
et il introduit son email correct et son mot de passe correct,
Lorsque, il clique sur le bouton 'Connexion'
Alors, il est authentifié correctement et redirigé vers la page Home de son compte.

Scenario 2 : Mot de passe incorrect
Etant donné que, le beneficiaire est sur la page d'accueil,
et il introduit son email correct et son mot de passe incorrect,
Lorsque, il clique sur le bouton 'Connexion'
Alors, il la connexion est refusée et il on lui demande de resaisir les données corrects.

Scenario 3 : Mot de passe vide
Etant donné que, le beneficiaire est sur la page d'accueil,
et il introduit son email correct et son mot de passe vide,
Lorsque, il clique sur le bouton 'Connexion'
Alors, il la connexion est refusée et il on lui demande de resaisir les données corrects.

'''
output_format_2 = ''' US: Création de rejet artificiel
Cas passant:
Given le JDD à utiliser est un utilisateur
And Je constitue un fichier json pour ma reqûete
And la valeur pour la clé code_cinématique est <code_cinématique>
And la valeur pour la clé mode est <mode>
And je constitue un <fichier>
When je fais un appel API avec la méthode POST au service OJE_MASSE_CREER_REJ_ART pour creer un rejet artificiiel
Then la réponse devrait être <code_retour>
And la valeur retour ID est ID
And Je constitue le fichier json pour ma requête
And la valeur pour la clé code_cinématique est <code_cinématique>
And la valeur pour la clé mode est <mode2>
And je constitue un <fichier>
When je fais un appel API avec la méthode POST au service OJE_MASSE_CREER_REJ_ART pour creer un rejet artificiiel
Then la réponse devrait être <code_retour>
When la valeur pour la clé job est <job>
And je refais un appel API avec la méthode GET au service OJE_BATCH pour démarrer le traitement
Then la réponse devrait être http <code_retour2>
When la valeur pour la clé ID est <ID>
And je fais un appel API avec la méthode GET au service OSD_telecharger_CR pour telecharger un compte rendu
Then la réponse devrait être http <code_retour2>

Cas non passant:
Given le JDD à utiliser est un utilisateur
And Je constitue un fichier json pour ma reqûete
And la valeur pour la clé code_cinématique est <code_cinématique>
And la valeur pour la clé mode est <mode>
And je constitue un <fichier>
When je fais un appel API avec la méthode POST au service OJE_MASSE_CREER_REJ_ART pour creer un rejet artificiiel
Then la réponse devrait être <code_retour>

Les valeurs entre <> représentent des variables qui seront remplacées par un jeu de données ensuite.
'''

output_format_3 = '''
US : Authentification au système
Scenario 1 : Authentification réussie
1- Je suis sur la page de login 
2- J'introduis mon adresse email sous format valide
3- J'introduis mon mot de passe contenant au moins 8 caractères, des alphanumeriques et des caractères spéciaux, associé à l'adresse email
4- Je vois un message de succès d'authentification
5- Je suis déplacé vers la page Home.
'''

app = FastAPI()

# Define the allowed origins
origins = [
    "http://localhost:3000",
    "http://10.70.0.208:3000",
    "http://10.70.0.208:3001",
    "http://10.70.0.208:3002",
    "http://10.70.0.208:3001/graphrag-visualizer",
    "http://192.168.1.13:3000",
    "http://192.168.1.13:3001",
    "http://192.168.1.13:3002",
    "http://127.0.0.1:8000",
]

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use the defined list of origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)



# Directory setup
us_folder = os.path.join("uploads", "user_stories")
ctx_folder = os.path.join("uploads", "context")
us_history_folder = os.path.join("uploads_us_history", "user_stories")
os.makedirs(us_folder, exist_ok=True)
os.makedirs(ctx_folder, exist_ok=True)
os.makedirs(us_history_folder, exist_ok=True)
logging.info(f"Directories created: {us_folder}, {ctx_folder}, {us_history_folder}")

moved_files = move_files(us_folder, us_history_folder)
logging.info(f"{moved_files} I. User story files moved to uploads us history folder.")

# Global settings for input and processing
class ProcessingState:
    jira_input = False
    us_file_uploaded = False
    context_file_uploaded = False
    context_graph_exists = False
    user_paths = {}
    selected_format = ""
    ids_list = []
    titles_list = []

state = ProcessingState()



@app.post("/upload/")
async def upload_files(
    user_stories_file: Optional[UploadFile] = File(None),
    context_file: Optional[UploadFile] = File(None),
    selected_format: Optional[str] = Form(""),
    jira_username: Optional[str] = Form(""),
    jira_project_id: Optional[str] = Form(""),
    jira_server_url: Optional[str] = Form(""),
    Tasks_list_name: Optional[str] = Form(""),
):
    try:
        
        # moved_files = move_files(us_folder, us_history_folder)
        # logging.info(f"{moved_files} I. User story files moved to uploads us history folder.")

        
        # Save user stories file
        if user_stories_file:
            us_path = os.path.join(us_folder, user_stories_file.filename.replace(" ", "_"))
            with open(us_path, "wb") as f:
                f.write(await user_stories_file.read())
            state.us_file_uploaded = True
            logging.info(f"User stories file saved at: {us_path}")

        # Save context file
        if context_file:
            ctx_path = os.path.join(ctx_folder, context_file.filename.replace(" ", "_"))
            with open(ctx_path, "wb") as f:
                f.write(await context_file.read())
            state.context_file_uploaded = True
            logging.info(f"Context file saved at: {ctx_path}")

        # Process Jira input
        state.user_paths = {
            "jira_user": jira_username or "",
            "project_key": jira_project_id or "",
            "jira_url": jira_server_url or "",
            "ticket_name_field": Tasks_list_name or "",
        }
        # state.jira_input = all(state.user_paths.values())
        # logging.info(f"*********************** {state.jira_input} ***********************")


        if (state.user_paths["jira_user"] != "" and 
            state.user_paths["project_key"] != "" and 
            state.user_paths["jira_url"] != "" and 
            state.user_paths["ticket_name_field"] != ""):
            state.jira_input = True
            logging.info("Jira input enabled.")
        else: 
            state.jira_input = False
            logging.info(f"Jira input disabled. {state.user_paths}")

        if state.jira_input:
            logging.info(f"\n ----------------- Jira input enabled. {state.jira_input} /// {state.user_paths}")
        else:
            logging.info(f"Jira input disabled. ------------------- {state.jira_input}")


        # state.context_graph_exists = not state.context_file_uploaded

        return {"message": "Files uploaded successfully"}
    except Exception as e:
        logging.error(f"Error in upload: {e}")
        return {"error": str(e)}

@app.post("/update_create_graph/")
async def create_graphs():
    try:
        # Replace the following with your graph creation logic
        logging.info("Starting graph creation...")
        Create_Graph_folder(
            False, False, Graphs_folder_path, graph_US, us_folder, output_folder, US_Visual_graph_folder
        )
        if state.context_file_uploaded == True:
            Create_Graph_folder(
                # state.context_graph_exists,
                # state.context_graph_exists,
                False,
                False,
                Graphs_folder_path,
                graph_context,
                ctx_folder,
                output_folder,
                Contxt_Visual_graph_folder,
            )
        logging.info("Graph folders created successfully.")
        return {"message": "Graphs created successfully"}
    except Exception as e:
        logging.error(f"Error creating graphs: {e}")
        return {"error": str(e)}

@app.post("/generate_test_cases/")
async def generate_test_cases():
    try:
        logging.info("Starting test case generation...")
        if not state.jira_input:
            df, concat_json, concat_text = concatenate_json_files_to_text(us_folder)
            logging.info("Concatenated files into text.")
        else:
            # Logic when Jira input is enabled
            imported_US, state.ids_list, state.titles_list, df = Jira_import(
                state.user_paths, us_folder, "To Test"
            )
            logging.info(f"Jira tickets imported successfully. Titles: {state.titles_list}")

        # Test case generation logic
        prompt_list = []
        full_prompt_list = []
        tc_list = []
        groupchat_prompt_generator_list = []
        grp_chat_res_list = []
        costs_list = []

        for index, row in df.iterrows():
            logging.info(f"Processing user story number: {index}")
            US = row['Titre'] + row['Description']
            RG = row['Règles de gestion']
            CA = row["Critères d'acceptance"]
            # if selected_format == "Format paramétré":
            #     parametres = row["Fichier Cinématique"]

            # Determine output format
            if state.selected_format == "Gherkin sans paramètres":
                output_format_choisi = output_format_1
            elif state.selected_format == "Gherkin avec paramètres":
                output_format_choisi = output_format_2
            elif state.selected_format ==  "Format en steps language naturel" : 
                output_format_choisi = output_format_3

            # Generate prompts
            Planner, Context_retrieval, CA_synthesizer, Related_US_Synthesizer, US_Synthesizer_critic, Context_Retrieval_Critic = define_prompt_generation_module(
                US, RG, graph_US, graph_context, CA, llm_config_gpt4o)
            groupchat_res, final_prompt = Generate_prompt(
                US, RG, Planner, Context_retrieval, CA_synthesizer, Related_US_Synthesizer, 
                US_Synthesizer_critic, Context_Retrieval_Critic, CA, 10)
            
            TC_Generator, CA_critic, TC_prompt = define_tc_reflection_module(US, CA, TC_gen_msg, output_format_choisi, llm_config_gpt4turbo, RG, "")
            grp_chat_res, TC = generate_TC(final_prompt, TC_Generator, CA_critic, 4)

            prompt_list.append(final_prompt)
            full_prompt_list.append(TC_prompt + final_prompt)
            tc_list.append(TC)
            groupchat_prompt_generator_list.append(groupchat_res.chat_history)
            grp_chat_res_list.append(grp_chat_res.chat_history)
            costs_list.append("\n --------- \n prompt generation COST : " + str(groupchat_res.cost) + "\n --------- \n TC Gen COST : " + str(grp_chat_res.cost))
            logging.info(f"Test case generated for user story number: {index}") 



        ########## ENd MAIN ##############

        # Save output Test Cases excel
        os.makedirs(save_output_folder, exist_ok=True)
        Final_output_path = os.path.join(save_output_folder, "Gen_TC_1.xlsx")

        if state.jira_input == False :
            df_resultat = pd.DataFrame({
                'Row_Generated Prompts': prompt_list,
                'Final input prompts': full_prompt_list,
                'Test Cases': tc_list,
                'groupchat_prompt': groupchat_prompt_generator_list,
                'groupchat_TC': grp_chat_res_list,
                'Costs': costs_list
            })
        else:
            df_resultat = pd.DataFrame({
                'id_US': state.ids_list,
                'Title': state.titles_list,
                'Row_Generated Prompts': prompt_list,
                'Final input prompts': full_prompt_list,
                'Test Cases': tc_list,
                'groupchat_prompt': groupchat_prompt_generator_list,
                'groupchat_TC': grp_chat_res_list,
                'Costs': costs_list
            })


        df_resultat.to_excel(Final_output_path, index=False, engine="openpyxl")
        logging.info(f"Test cases saved at: {Final_output_path}")
        
        if state.jira_input == True :
            # Save to Jira
            create_link_tickets(state.user_paths, df_resultat, link_type="Relates")
            logging.info("Jira tickets created and linked successfully.")

        return {"message": "Test cases generated successfully"}
    except Exception as e:
        logging.error(f"Error in test case generation: {e}")
        return {"error": str(e)}

@app.post("/launch_generation/")
async def launch_generation(
    user_stories_file: Optional[UploadFile] = File(None),
    context_file: Optional[UploadFile] = File(None),
    selected_format: Optional[str] = Form(""),
    jira_username: Optional[str] = Form(""),
    jira_project_id: Optional[str] = Form(""),
    jira_server_url: Optional[str] = Form(""),
    Tasks_list_name: Optional[str] = Form(""),
):
        # Update the selected format in the global state
    if selected_format:
        state.selected_format = selected_format
    # Determine output format with a default case
    if state.selected_format == "Gherkin sans paramètres":
        output_format_choisi = output_format_1
    elif state.selected_format == "Gherkin avec paramètres":
        output_format_choisi = output_format_2
    elif state.selected_format == "Format en steps language naturel":
        output_format_choisi = output_format_3

    try:
        logging.info("Starting the launch generation process...")

        # Step 1: Upload files
        upload_response = await upload_files(
            user_stories_file=user_stories_file,
            context_file=context_file,
            selected_format=selected_format,
            jira_username=jira_username,
            jira_project_id=jira_project_id,
            jira_server_url=jira_server_url,
            Tasks_list_name=Tasks_list_name,
        )
        if "error" in upload_response:
            return {"message": "File upload failed", "details": upload_response["error"]}

        # Step 2: Update and create graphs
        graph_response = await create_graphs()
        if "error" in graph_response:
            return {"message": "Graph creation failed", "details": graph_response["error"]}

        # Step 3: Generate test cases
        test_case_response = await generate_test_cases()
        if "error" in test_case_response:
            return {"message": "Test case generation failed", "details": test_case_response["error"]}

        # If all steps succeeded
        return {
            "message": "All steps executed successfully",
            "file_upload": upload_response,
            "graph_creation": graph_response,
            "test_case_generation": test_case_response,
        }

    except Exception as e:
        logging.error(f"Error in launch generation: {e}")
        return {
            "error": str(e),
            "message": "An error occurred during the launch generation process",
            "traceback": traceback.format_exc(),
        }       


@app.get("/download/")
async def download_file():
    Final_output_path = os.path.join(save_output_folder, "Gen_TC_1.xlsx")
    logging.info(f"{Final_output_path} ,, {os.path.exists(Final_output_path)}")
    if os.path.exists(Final_output_path):
        return FileResponse(
            path = Final_output_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="Gen_TC_1.xlsx",
            headers={"Cache-Control": "no-cache"}
        )
    return JSONResponse(content={"message": "File not found"}, status_code=404)

