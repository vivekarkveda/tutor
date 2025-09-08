import os
import json
from pathlib import Path


def pyfile_generator(jsonFile):
    print("Generating Python files from JSON:", jsonFile)

    # Load JSON data
    with open(jsonFile, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract base name of JSON (without extension) for folder name
    json_name = Path(jsonFile).stem  

    # Base folder location → C:\Vivek_Main\Manim_project\inputbox\{json_name}
    base_path = Path(r"C:\Vivek_Main\Manim_project\inputbox") / json_name
    base_path.mkdir(parents=True, exist_ok=True)

    # Loop through each script item
    for item in data:
        seq = item["script_seq"]
        script_for_manim = item["script_for_manim"]
        script_voice_over = item["script_voice_over"]

        # Create subfolder for each script
        folder_name = f"script_seq{seq}"
        folder_path = base_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        # Python file content
        py_content = f'''"""
{script_for_manim} 
{script_voice_over}
"""
'''

        py_file = folder_path / f"{folder_name}.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(py_content)

        # TXT file content (voice over only)
        txt_file = folder_path / f"{folder_name}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(script_voice_over)

        print(f"✅ Created: {py_file} and {txt_file}")

    print("🎉 All files generated inside:", base_path)



