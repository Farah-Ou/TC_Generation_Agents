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

from src.Files_treatment import concatenate_json_files_to_text, concatenate_text_pdf_files

## GET this path at the end of the graph creation file
# graph_visualizer_path = r"Graphs\graphrag-visualizer"
# artifacts_graph_visualizer_path = os.path.join(graph_visualizer_path, "public", "artifacts")

os.environ["PYTHONIOENCODING"] = "utf-8"
load_dotenv(r".env")

## Default paths created for the graphs
output_folder= "input"
graph_context="project_contxt_graph"
graph_US='us_graph'
Graphs_folder_path = "Graphs"
# artifacts_graph_visualizer_path=os.path.join("graphrag-visualizer","public","artifacts") # verify the location where u'll create it

## Models Config
llm_config_gpt4turbo = {"model": "gpt-4-turbo"} ## Mainly used for the graph creation and TC generation phase 
llm_config_gpt4o_mini = {"model": "gpt-4o-mini"} ## Used for context extraction and prompt creation phase 
llm_config_gpt4o =  {"model": "gpt-4o"} ## Good for non english text, fast, less expensive than turbo


import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

# def safe_convert_large_integers(df):
#     for col in df.columns:
#         if df[col].dtype in ['int64', 'int32']:
#             # Convert large integers to strings or use safe casting
#             df[col] = df[col].astype(str)
#     return df

# # When saving Parquet files, use this approach
# def save_parquet_safely(df, output_path):
#     # Convert large integers to strings
#     df_safe = safe_convert_large_integers(df)
    
#     # Convert to PyArrow table
#     table = pa.Table.from_pandas(df_safe)
    
#     # Write Parquet file
#     pq.write_table(table, output_path)
    

## Graph creation
def Create_Graph_folder(graph_exists, visual_exists, Graphs_folder_path, graph_name, input_folder_path, output_folder, artifacts_graph_visualizer_path):
    # Define the working directory and create it if needed    
    working_directory = os.path.join(Graphs_folder_path, graph_name)

    
    os.environ["PYTHONIOENCODING"] = "utf-8"
    # load_dotenv(r".env")
    env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(env_file_path)
    
    # Retrieve the GRAPHRAG_API_KEY from the environment
    api_key = os.getenv("GRAPHRAG_API_KEY")

    # Check if the environment variable is set
    if api_key is None:
        raise ValueError("GRAPHRAG_API_KEY environment variable is not set.")

    # Set the environment variable explicitly
    os.environ["GRAPHRAG_API_KEY"] = api_key

    if graph_exists == False:
        # Define the working directory and create it if needed    
        working_directory = os.path.join(Graphs_folder_path, graph_name)

        # Ensure output folder exists
        os.makedirs(os.path.join(working_directory, output_folder), exist_ok=True)

        # Check if the input folder exists
        if not os.path.isdir(input_folder_path):
            raise FileNotFoundError(f"Input folder {input_folder_path} does not exist.")

        if graph_name == graph_US:
            df, file_path_json, output_file_path = concatenate_json_files_to_text(input_folder_path)
            output_file_name = "Combined_US_file.txt" 
        elif graph_name == graph_context:
            output_file_path = concatenate_text_pdf_files(input_folder_path)
            output_file_name = "Combined_Context_file.txt" 
            
        # Define the path for the output file in the output folder
        output_path = os.path.join(working_directory, output_folder, output_file_name)
        
        # Copy the combined file to the output folder
        shutil.copy(output_file_path, output_path)
        
        # Set encoding for subprocesses
        os.environ["PYTHONIOENCODING"] = "utf-8"
        
        # Initialize workspace and index data with Microsoft graphrag
        subprocess.run(['python', '-m', 'graphrag.index', '--init', '--root', working_directory], check=True)
        subprocess.run(['python', '-m', 'graphrag.index', '--root', working_directory], check=True)

        print(f"Graph created in {working_directory} with combined file copied to {output_path}.")


        ########## Visual graph 

        # Copy parquet files to artifacts graph visulaizer folder for automatic retrieval and visualization upon server launch
        graph_parquets = os.path.join(working_directory, "output")
        
            
        # File path needs to be as ::::::::::::: graphrag-visualizer\\public\\artifacts'

        for file_name in os.listdir(graph_parquets):
            source_path = os.path.join(graph_parquets, file_name)
            target_path = os.path.join(artifacts_graph_visualizer_path, file_name)
            # target_path = os.path.join(target_graph_folder, file_name)
            if os.path.isfile(source_path):
                shutil.copy2(source_path, target_path)  # copy2 preserves metadata
                print(f"Copied: {source_path} -> {target_path}")

        print(f"Graph artifacts copied to {artifacts_graph_visualizer_path}")


    else:
        print(f"Graph {graph_name} already exists in {Graphs_folder_path}.")

        if visual_exists == False:
            # Copy parquet files to artifacts graph visulaizer folder for automatic retrieval and visualization upon server launch
            graph_parquets = os.path.join(working_directory, "output")
            # target_graph_folder = os.path.join(artifacts_graph_visualizer_path, graph_name)
            # if not os.path.exists(target_graph_folder):
            #     os.makedirs(target_graph_folder)
                
            # File path needs to be as ::::::::::::: graphrag-visualizer\\public\\artifacts'

            for file_name in os.listdir(graph_parquets):
                source_path = os.path.join(graph_parquets, file_name)
                target_path = os.path.join(artifacts_graph_visualizer_path, file_name)
                # target_path = os.path.join(target_graph_folder, file_name)
                if os.path.isfile(source_path):
                    shutil.copy2(source_path, target_path)  # copy2 preserves metadata
                    print(f"Copied: {source_path} -> {target_path}")

            print(f"Graph artifacts copied to {artifacts_graph_visualizer_path}")
        else:
            print(f"Visual graph files already available, Graph artifacts already exist in {artifacts_graph_visualizer_path}")


    