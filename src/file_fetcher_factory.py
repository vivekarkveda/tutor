import os
from pathlib import Path

class FileFetcherFactory:
    """Factory for different types of file fetchers."""

    BASE_INPUT_PATH = r"C:\Vivek_Main\Manim_project\inputbox"
    BASE_JSON_PATH = r"C:\Vivek_Main\Manim_project\jsonfiles\Pythagoras.json"

    @staticmethod
    def _get_latest_folder(base_path):
        """Return the path to the latest folder inside base_path."""
        folders = [f for f in Path(base_path).iterdir() if f.is_dir()]
        if not folders:
            return None
        # Sort by creation/modification time and pick the latest
        latest_folder = max(folders, key=lambda f: f.stat().st_mtime)
        return latest_folder

    @staticmethod
    def get_python_files():
        """Fetch all .py files inside the latest folder of inputbox."""
        latest_folder = FileFetcherFactory._get_latest_folder(FileFetcherFactory.BASE_INPUT_PATH)
        if not latest_folder:
            return []
        return [str(f) for f in Path(latest_folder).rglob("*.py")]

    @staticmethod
    def get_narration_files():
        """Fetch all .txt narration files inside the latest folder of inputbox."""
        latest_folder = FileFetcherFactory._get_latest_folder(FileFetcherFactory.BASE_INPUT_PATH)
        if not latest_folder:
            return []
        return [str(f) for f in Path(latest_folder).rglob("*.txt")]

    @staticmethod
    def get_json_file():
        """Fetch JSON config file."""
        json_file = FileFetcherFactory.BASE_JSON_PATH
        print("JSON file path:", json_file)
        return json_file
