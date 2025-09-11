import os
import json
from pathlib import Path
from datetime import datetime

class PyFileFactory:
    """Factory for generating Python and TXT files from a JSON input."""

    BASE_INPUT_PATH = Path(r"C:\Vivek_Main\Manim_project\inputbox")

    @staticmethod
    def pyfile_generator(jsonFile: str):
        print("📝 Generating Python and TXT files from JSON:", jsonFile)

        # Load JSON data
        with open(jsonFile, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract base name of JSON (without extension) for folder name
        json_name = Path(jsonFile).stem  

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Base folder location → inputbox / {json_name}_{timestamp}
        base_path = PyFileFactory.BASE_INPUT_PATH / f"{json_name}_{timestamp}"
        base_path.mkdir(parents=True, exist_ok=True)

        generated_files = {"py_files": [], "txt_files": []}

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

            generated_files["py_files"].append(str(py_file))
            generated_files["txt_files"].append(str(txt_file))

            print(f"✅ Created: {py_file} and {txt_file}")

        print("🎉 All files generated inside:", base_path)
        return generated_files
