# C:\Vivek_Main\tutter\src\file_fetcher_factory.py
from pathlib import Path
from parsers.base_handler import InputHandlerFactory  # <-- JsonHandler & PostgresHandler
from logger import pipeline_logger, validation_logger


class FileFetcherFactory:
    """Factory for fetching generated files from local JSON or Postgres."""

    BASE_INPUT_PATH = Path(r"C:\Vivek_Main\Manim_project\inputbox")
    BASE_JSON_PATH = Path(r"C:\Vivek_Main\Manim_project\jsonfiles\Pythagoras.json")

    @staticmethod
    def _get_latest_folder(base_path: Path):
        """Return the path to the latest folder inside base_path."""
        folders = [f for f in Path(base_path).iterdir() if f.is_dir()]
        if not folders:
            return None
        return max(folders, key=lambda f: f.stat().st_mtime)

    @staticmethod
    def get_files(handler_type: str, **kwargs):
        """
        Generate and fetch files depending on handler type.

        Args:
            handler_type (str): "local" or "postgres"
            kwargs:
                - local: {"json_file": str}
                - postgres: {"query": str, "credentials": dict}

        Returns:
            dict: {"py_files": [...], "txt_files": [...]}
        """
        handler = InputHandlerFactory.get_input_handler(handler_type)

        if handler_type == "local":
            json_file = kwargs.get("json_file", FileFetcherFactory.BASE_JSON_PATH)
            generated_files = handler.handle(json_file)

        elif handler_type == "postgres":
            credentials = kwargs["credentials"]
            query = kwargs["query"]
            handler.set_credentials(credentials)
            generated_files = handler.handle(query)

        else:
            validation_logger.error(f"❌ Invalid handler type: {handler_type}")
            raise ValueError(f"Invalid handler type: {handler_type}")

        return generated_files

    @staticmethod
    def get_latest_files():
        """
        Fetch all .py and .txt files from the latest folder in BASE_INPUT_PATH.
        Use after calling get_files().
        """
        latest_folder = FileFetcherFactory._get_latest_folder(FileFetcherFactory.BASE_INPUT_PATH)
        if not latest_folder:
            return {"py_files": [], "txt_files": []}

        # 🔑 Use as_posix() for cross-platform consistency
        py_files = [f.as_posix() for f in Path(latest_folder).rglob("*.py")]
        txt_files = [f.as_posix() for f in Path(latest_folder).rglob("*.txt")]

        return [{"py_files": py_files, "txt_files": txt_files},latest_folder]
