import os

def get_files():
    base_path = r"C:\Vivek_Main\Manim_project\inputbox"

    script_files = []

    # Walk through all folders and subfolders
    for root, _, files in os.walk(base_path):
        for f in files:
            if f.endswith(".py"):  # only Python files
                script_files.append(os.path.join(root, f))

    return script_files

def get_naration_files():
    base_path = r"C:\Vivek_Main\Manim_project\inputbox"

    script_naration_files = []

    
    for root, _, files in os.walk(base_path):
        for f in files:
            if f.endswith(".txt"):  
                script_naration_files.append(os.path.join(root, f))

    return script_naration_files

def get_json_files():


    folderpath = r"C:\Vivek_Main\Manim_project\jsonfiles\Pythagoras.json"

    jsonFile = os.path.join(folderpath)
    print("json file path:", jsonFile)

    return jsonFile
