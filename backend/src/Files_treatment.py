import os
from dotenv import load_dotenv
import shutil
import subprocess
import pandas as pd
import json
from jira import JIRA
import fitz
import yaml


def move_files(input_folder, target_folder):
    """
    Move all files from input_folder to target_folder.
    
    Args:
    input_folder (str): Path to the source folder containing files to be moved
    target_folder (str): Path to the destination folder where files will be moved
    
    Returns:
    int: Number of files successfully moved
    """
    # Ensure the target folder exists
    os.makedirs(target_folder, exist_ok=True)
    
    # Counter for successfully moved files
    files_moved = 0
    
    # Iterate through all files in the input folder
    for filename in os.listdir(input_folder):
        # Create full file paths
        source_path = os.path.join(input_folder, filename)
        destination_path = os.path.join(target_folder, filename)
        
        # Skip if it's a directory
        if os.path.isdir(source_path):
            continue
        
        try:
            # Move the file
            shutil.move(source_path, destination_path)
            files_moved += 1
        except Exception as e:
            print(f"Error moving {filename}: {e}")
    
    return files_moved


def concatenate_json_files_to_text(input_folder_path):
    combined_data = []
    output_file_path_json=""
    
    # Define the output path where the combined text file will be stored
    output_file_path_txt = os.path.join(input_folder_path, "Combined_us_file.txt")
    
    nb=0

    # Loop through all files in the input folder
    for file_name in os.listdir(input_folder_path):
        # Only process JSON files
        if file_name.endswith(".json"):
            nb+=1
            file_path = os.path.join(input_folder_path, file_name)
            
            # Open and read each JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                combined_data.extend(data)  # Add the content to the combined data
                
    if nb != 1:
        # Write the combined content to a new JSON file
        output_file_path_json = os.path.join(input_folder_path, "Combined_json_file.json")
        with open(output_file_path_json, 'w', encoding='utf-8') as output_file:
            json.dump(combined_data, output_file, ensure_ascii=False, indent=4)
        print(f"Ensemble json US concatenated and saved to path {output_file_path_json}")
        
        ## Turn into txt combined file
        df = pd.read_json(output_file_path_json)
        content_as_text = df.to_string(index=False)
        
        # Save content to a text file
        with open(output_file_path_txt, 'w', encoding='utf-8') as f:
            f.write(content_as_text)
        print(f"Ensemble Text US saved to path {output_file_path_txt}")
    
    elif nb==1:
        df = pd.read_json(file_path)
        # output_path = os.path.join(input_folder_path, "US_text_file.txt")
        content_as_text = df.to_string(index=False)
        # Save content to a text file
        with open(output_file_path_txt, 'w', encoding='utf-8') as f:
            f.write(content_as_text)
        print(f"Textual US saved to path {output_file_path_txt}")
        
    else : 
        print(f"Aucun fichier json n'existe dans le chemin fourni {input_folder_path}.")
        
    return df, output_file_path_json, output_file_path_txt   

def concatenate_text_pdf_files(input_folder_path):
    # Define the path for storing the combined files
    combined_file_path = os.path.join(input_folder_path, "combined_context_files.txt")
    
    # Concatenate contents of all files in input folder into the combined file
    with open(combined_file_path, 'w', encoding="utf-8") as combined_file:
        for file_name in os.listdir(input_folder_path):
            input_path = os.path.join(input_folder_path, file_name)
            
            # Process text files
            if os.path.isfile(input_path) and file_name.endswith('.txt'):
                with open(input_path, 'r', encoding="utf-8") as input_file:
                    # Write file content to the combined file with a newline separator
                    combined_file.write(input_file.read() + "\n")
                    
            # Process PDF files
            elif os.path.isfile(input_path) and file_name.endswith('.pdf'):
                with fitz.open(input_path) as pdf_file:
                    for page_num in range(pdf_file.page_count):
                        page = pdf_file.load_page(page_num)
                        combined_file.write(page.get_text("text") + "\n")
    return combined_file_path