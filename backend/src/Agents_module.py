import os
import openai
from openai import OpenAI
import autogen
import graphrag
from dotenv import load_dotenv
import shutil
import subprocess
import pandas as pd
import json
from jira import JIRA
import fitz
import yaml

from autogen import ConversableAgent, AssistantAgent
from langchain_core.tools import tool
from typing_extensions import Annotated
from autogen import register_function

os.environ["PYTHONIOENCODING"] = "utf-8"
load_dotenv(r".env")


## Default paths created for the graphs
output_folder= "Input"
graph_context="project_contxt_graph"
graph_US='us_graph'
project_folder_path = "Graphs"

## Models Config
llm_config_gpt4turbo = {"model": "gpt-4-turbo"} ## Mainly used for the graph creation and TC generation phase 
llm_config_gpt4o_mini = {"model": "gpt-4o-mini"} ## Used for context extraction and prompt creation phase 
llm_config_gpt4o =  {"model": "gpt-4o"} ## Good for non english text, fast, less expensive than turbo
llm_config_o1_mini = {"model": "o1-mini"} ## Good for non english text, fast, less expensive than turbo



## Query Tools Definition
def run_local_query(
    project_folder_path: Annotated[str,"The folder path where the graph is located" ], 
    # input_contxt_path: Annotated[str,"The path where the context input is located" ], 
    # input_us_path: Annotated[str,"The path where the US input is located" ],
    graph_name: Annotated[str,"The end folder name where the graph is located" ],
    query_text: Annotated[str,"The Query text" ]) -> Annotated[str,"The retrieved content from the graph after a local call" ]:
    """ Makes a local call to the graph"""

    working_directory = os.path.join(project_folder_path, graph_name)
    
    # Set up the command arguments
    command = [
        'python', '-m', 'graphrag.query',
        '--root', working_directory,
        '--method', 'local',
        query_text
    ]

    # Execute the command and capture the output
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8'
    )

    # Capture the output and errors
    if result.returncode == 0:
        # Command was successful
        print ("local retrieval sucess")
        return result.stdout  # Return the captured output
    else:
        # Command failed, return the error message
        return f"Error: {result.stderr}"

def run_global_query(
    project_folder_path: Annotated[str,"The folder path where the graph is located" ], 
    # input_contxt_path: Annotated[str,"The path where the context input is located" ], 
    # input_us_path: Annotated[str,"The path where the US input is located" ],
    graph_name: Annotated[str,"The end folder name where the graph is located" ],
    query_text: Annotated[str,"The Query text" ]) -> Annotated[str,"The retrieved content from the graph after a global call" ]:
    """ Makes a global call to the graph"""

    working_directory = os.path.join(project_folder_path, graph_name)
    
    # Set up the command arguments
    command = [
        'python', '-m', 'graphrag.query',
        '--root', working_directory,
        '--method', 'global',
        query_text
    ]

    # Execute the command and capture the output
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8'
    )

    # Capture the output and errors
    if result.returncode == 0:
        # Command was successful
        print ("global retrieval sucess")
        return result.stdout  # Return the captured output
    else:
        # Command failed, return the error message
        return f"Error: {result.stderr}"



### AGENTS DEFINITION

def define_prompt_generation_module(US, RG, graph_US, graph_context, CA="", llm_config=llm_config_gpt4turbo, project_folder_path=project_folder_path):
    # Related US Synthesizer Agent 
    Related_US_Synthesizer = autogen.AssistantAgent(
    name="Related_US_Synthesizer",
    system_message="Tu es un analyste intelligent de User stories." 
        f"Tu lis le user story de reference, et tu appelles l'outil run_local_query(project_folder_path, graph_name, query_text) avec les paramètres" 
        f"suivants: {project_folder_path}, {graph_US}. La variable query_text prend cette phrase: '''Quels sont les Critères d'Acceptance des autres User Stories "
        f"liés à l'US {US}? Tiens compte des paramètres s'ils existent dans un fichier cinématique'''. Tu enregistres le contenu retourné par la fonction dans une variable V1. Ensuite, tu appelles le tool" 
        f"run_global_query(project_folder_path, graph_name, query_text) avec les mêmes valeurs de paramètres et tu enregistres son retour dans une variable V2."
        "Tu lis le contenu des variables V1 et V2 en relation avec les User stories du projet entier, et tu trouves les relations et les interdépendances "
        f"entre le contenu que tu lis et le User Story de référence. Tu extrais les critères d'acceptance des user stories du projet qui sont en "
        "relation avec une fonctionnalité du User Story de référence."

        "Renvoie seulement le résultat final : les critères d'acceptances et informations pertienentes en relation avec l'US de référence.",
    llm_config=llm_config,
    )

    ## US synthesizer critic
    US_Synthesizer_critic = autogen.AssistantAgent(
    name="Related_US_Synthesizer_critic",
    system_message="Tu es un critique du contenu acquéri par Related_US_Synthesizer Agent. Tu evalues si le contenu qu'il a aquéri contient des" 
        "critères d'acceptance liés à une même fonctionnalité provenant d'une autre US. Par exemple: dans l'US de référence, pour accepter l'enregistrement"
        "d'un utilisateur dans le système, il faut qu'il introduise le numero de sa carte nationale. Dans un autre US, on trouve aussi que l'utilisateur"
        "doit renseigner ses informations de compte bancaire, sinon il n'est pas accepté. Le Related_US_Synthesizer Agent doit retourner: "
        "Critères d'acceptance: L'utilisateur doit renseigner son numéro de carte nationale. L'utilisateur doit renseigner ses informations de compte bancaire."
        
        "Tu évalues le résultat du Related_US_Synthesizer, tu lui attribue une note sur 10." 
        "Après, tu suggères une variante de la question dans la variable 'query_text' que l'agent utilise pour faire appel au graph, pour optimiser" 
        "le résultat retourné.",        
    llm_config=llm_config,
    )

    ## CA synthesizer Agent : Synthesizes RG and CA into clear detailed CA if they both exist, if only RG eist, it synthesizes CA on its own
    CA_synthesizer = autogen.AssistantAgent(
    name="Acceptance_Criteria_Synthesizer",
    system_message=f"Tu es un synthétiseur des critères d'acceptance de User Story (US). " 
        f" En cas d'absence de Critères d'acceptance ({CA} est une chaine vide), etant donné un US {US}, tu lis avec beaucoup d'attention les "
        f"règles de gestion {RG} liées au User Story et tu determines les critères d'acceptance avec le maximum de détail, les noms des boutons dans"
        "l'interface de l'application, les noms des paramètres s'ils existent. Ne donne pas des informations non cités dans les RG"
        "Renvoie seulement le résultat final."

        f" En cas de présence de Critères d'acceptance ({CA} est n'est pas vide), etant donné un US {US}, tu lis avec beaucoup d'attention les "
        f" Critères d'acceptance (CA) et les règles de gestion 5RG) {RG} liées au User Story. Ensuite, tu fais une synthèse détaillée des CA et RG"
        "et tu retournes un ensemble de critères de gestion détaillés avec les noms des boutons dans l'interface de l'application, les noms des" 
        "paramètres s'ils existent. Ne donne pas des informations non cités dans les RG et CA. Renvoie seulement le résultat final."
        "Inclut tous les détails des exigences fonctionnelles et non fonctionnelles, n'ignore aucune exigence.",
    llm_config=llm_config,
    )

    # Context retrieval Agent
    Context_retrieval = autogen.AssistantAgent(
    name="Context_Retrieval",
    system_message="Tu es un context retriever. Tu réalises les étapes suivantes: "
        "1. Tu appelles l'outil run_local_query(project_folder_path, graph_name, query_text) avec les paramètres suivants: " 
        f"{project_folder_path}, {graph_context}. La variable query_text prend cette phrase: '''Quelles sont les informations clés concernant le projet ?''' "
        f"2. Tu enregistres le contenu retourné par la fonction dans une variable W1. " 
        "3. Ensuite, tu appelles le tool run_global_query(project_folder_path, graph_name, query_text) avec les mêmes valeurs de paramètres" 
        f"4. Tu enregistres son retour dans une variable W2."
        "5. Tu lis le contenu des variables W1 et W2 en relation avec le projet entier, et tu les résumes dans R1. Le résumé doit être concis." 
        
        "Ensuite, tu fais les mêmes étapes de 1 à 5, avec les mêmes parametres, en remplaçant la variable query_text par :" 
        " '''Quelles sont les informations fonctionnelles clés concernant le projet ?'''." 
        "Enregistre le résumé de l'étape 5 pour cette nouvelle query_text dans une variable Z1."
        "Finalement, tu as R1 relative à la première question, et Z1 relative à la deuxième question." 
        "Renvoie seulement le résultat final : le résumé du contexte de projet de compréhension: R1 et fonctionnel: Z1.",
    llm_config=llm_config,
    )

    # Context retrieval Critic Agent
    Context_Retrieval_Critic = autogen.AssistantAgent(
    name="Context_Retrieval_Critic",
    system_message="Tu es un critique de la qualité des résultats retournés par le context retriever agent."
        "Tu évalues le résultat du Context_Retrieval, tu lui attribue une note sur 10." 
        "Après, tu suggères une variante de la question pour acquérir des connaissances liées au projet, à des termes techniques liées au domaine métier"
        "spécifique, dans la variable 'query_text'.l'agent Context_Retrieval utilise le paramètre 'query_text' pour faire appel au graph, pour optimiser" 
        "le résultat retourné.",  
    llm_config=llm_config,
    )


    # Planner Agent
    ## stimulate multiple calls to graph if needed for context
    Planner = autogen.AssistantAgent(
    name="Planner",
    system_message="Tu es un planificateur des actions à prendre selon la situation." 
        "Etant donné un US (User Story) avec des informations: sa description, ses règles de gestion (RG) et ses critères d'acceptance (CA)," 
        "Extrait le contenu en relation avec le User story en question en faisant appel à: Context_Retrieval. Ensuite, fais appel à Context_retrieval_Critic"
        "et appelle-les 2 fois au plus si le Context_Retrieval_Critic donne une note inférieure à 5 sur 10 au résultat retourné par Context_Retrieval."
        "Ensuite, fais appel à Related_US_Synthesizer suivi de US_Synthesizer_critic et appelle-les 2 fois au plus si le US_Synthesizer_critic donne"
        "une note inférieure à 5 sur 10 au résultat retourné par Related_US_Synthesizer."
        "Extrait le contenu retourné par Related_US_Synthesizer ayant la meilleure note sur 10, et mentionne la note attribuée par US_Synthesizer_critic."
        "Cherche les correlations entre l'ensemble de ces US et notre US."
        
        "Il est très important de Faire appel à l'agent Acceptance_Criteria_Synthesizer pour synthétiser des critères d'acceptance détaillés."
        
        "Finalement, crée un prompt contenant l'US, sa description, la synthèse de ses critères d'acceptance retournée par Acceptance_Criteria_Synthesizer," 
        "et les informations synthétisées des US qui lui sont liés retournés par Related_US_Synthesizer et Context_Retrieval."
        "Renvoie le prompt final"
        "Si une étape échoue, ne renvoie pas un résultat vide, renvoie le contenu retourné des agents à succès." 
        "Une fois le prompt final généré, tu dois le retourner, ne dis pas des choses inutiles. Le dernier output doit être le prompt final généré par toi, et pas des commentaires inutiles.",
        
    llm_config=llm_config,
    )

    ## Tool Registration
    for caller in [Related_US_Synthesizer, Context_retrieval]:
        register_function(
            run_global_query,
            caller=caller,
            executor=Planner,
            name="run_global_query",
            description="Makes a global call to the graph.",
        )
        
        register_function(
            run_local_query,
            caller=caller,
            executor=Planner,
            name="run_local_query",
            description="Makes a local call to the graph.",
        )

    print(Related_US_Synthesizer.llm_config["tools"])
    print(Context_retrieval.llm_config["tools"])

    return Planner, Context_retrieval, CA_synthesizer, Related_US_Synthesizer, US_Synthesizer_critic, Context_Retrieval_Critic

def Generate_prompt(US, RG, Planner, Context_retrieval, CA_synthesizer, Related_US_Synthesizer, US_Synthesizer_critic, Context_Retrieval_Critic, CA="", max_rounds=10):
    groupchat = autogen.GroupChat(
    agents=[Planner, Context_retrieval, Context_Retrieval_Critic, Related_US_Synthesizer, US_Synthesizer_critic, CA_synthesizer],
    messages=[],
    max_round=max_rounds,
    # allowed_or_disallowed_speaker_transitions={
    #     Related_US_Synthesizer : [US_Synthesizer_critic, Planner],
    #     US_Synthesizer_critic : [Related_US_Synthesizer, Planner],
    #     CA_synthesizer: [Planner],
    #     Context_retrieval: [Planner],
    #     Planner: [Related_US_Synthesizer, US_Synthesizer_critic, CA_synthesizer, Context_retrieval],
    # },
    # speaker_transitions_type="allowed",
    )
    
    manager = autogen.GroupChatManager(
    # groupchat=groupchat, llm_config=llm_config_gpt4o
    groupchat=groupchat, llm_config=llm_config_gpt4turbo
    )

    groupchat_result = Planner.initiate_chat(
    manager,
    message= US +'\n'+ RG +'\n'+ CA
    )

    return groupchat_result, groupchat_result.summary

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


### Functions Definition
def define_tc_reflection_module(US, RG, TC_gen_msg, output_format=output_format_1, llm_config=llm_config_gpt4turbo, CA="", parametres=""):
    if parametres=="":
        TC_Gen_sys_msg = TC_gen_msg + "\n Retourne 'TERMINATE' quand tu termines." + "Retourne des Cas de Test dans ce format: " + output_format + " \n Inclut les cas passants et non passants, avec une couverture maximale des cas de test. Tiens compte des scénarios outline. Respecte le format d'output présenté.Lis les critères d'acceptance un à un, et crée des scénarios qui en tiennent compte complétement. Soit détaillé ! On vise une couverture exhaustive des cas de test."
    else:
        TC_Gen_sys_msg = TC_gen_msg + f"Les paramètres à utiliser dans les Test Cases sont: {parametres}" + "\n Retourne 'TERMINATE' quand tu termines." + "Retourne des Cas de Test dans ce format: " + output_format
    ## TC Generator Agent
    TC_Generator = autogen.AssistantAgent(
        name="Test Cases Generator",
        system_message = TC_Gen_sys_msg,
        llm_config=llm_config,
    )

    ## Reflection: Critic Agents
    CA_critic = autogen.AssistantAgent(
        name="Test_Cases_Acceptance_criteria_Critic",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        system_message="Vous êtes un critique des cas de test d'un User Story, relativement aux critères d'acceptance. Vous évaluez le travail du"
        f"générateur de cas de test et evaluez son respect et sa couverture principalement des critères d'acceptance du User Story : {CA}, et " 
        f"des Règles de gestion {RG}.  N'ignore aucune exigence, si une exigence est manquante, demande que le générateur la rajoute."
        # "Evalue aussi son respect des critères d'acceptance pouvant être associés à ce User Story."                                
        "Vous essayez d'améliorer la couverture des cas de test générés. Vous attrribuez une note sur 10 au Test Cases Generator concernant" 
        "son respect des Critères d'acceptance. Renvoyez votre critique et la note attribuée.",                                     
    )

    return TC_Generator, CA_critic, TC_Gen_sys_msg

def generate_TC(prompt_final, TC_Generator, CA_critic, nb_turns=4):
    reply = TC_Generator.generate_reply(messages=[{"content": prompt_final, "role": "user"}])
    
    enhanced_msg = prompt_final + " \n Inclut les cas passants et non passants, avec une couverture maximale des cas de test. Tiens compte des scénarios outline. Respecte le format d'output présenté.Lis les critères d'acceptance un à un, et crée des scénarios qui en tiennent compte complétement. Soit détaillé ! On vise une couverture exhaustive des cas de test."
    res = CA_critic.initiate_chat(
        recipient=TC_Generator,
        message=enhanced_msg,
        max_turns=nb_turns,
        summary_method="last_msg"
    )

    return res, res.summary