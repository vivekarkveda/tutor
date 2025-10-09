import json
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
import psycopg2
from logger import pipeline_logger, validation_logger


class InputHandler(ABC):
    """Abstract base for input handlers."""

    BASE_INPUT_PATH = Path(r"D:\DemoScriptFolder")

    def __init__(self):
        self.credentials = None 

    @abstractmethod
    def set_credentials(self, credentials: dict):
        pass

    @abstractmethod
    def handle(self, data,file_types=None):
        pass

    # ✅ Common folder/file generation logic moved here
    def _generate_files(self, data: list[dict], base_name: str, file_types: list[str]):
        """Helper for creating files dynamically from scripts."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = self.BASE_INPUT_PATH / f"{base_name}_{timestamp}"
        base_path.mkdir(parents=True, exist_ok=True)
        pipeline_logger.debug(f"file_types: {file_types}")

        # Dict like {"py_files": [], "txt_files": [], "json_files": []}
        generated_files = {f"{ft}_files": [] for ft in file_types}
        pipeline_logger.debug(f"generated_files: {generated_files}")
 
        for item in data:
            seq = item["script_seq"]
            script_for_manim = item["script_for_manim"]
            script_voice_over = item["script_voice_over"]

            folder_path = base_path / f"script_seq{seq}"
            folder_path.mkdir(parents=True, exist_ok=True)

            # 🔑 Loop dynamically over file_types
            for ft in file_types:
                file_path = folder_path / f"script_seq{seq}.{ft}"

                if ft == "py":
                    content = f'"""{script_for_manim}\n{script_voice_over}"""'
                elif ft == "txt":
                    content = script_voice_over
                else:
                    # fallback: save both parts as JSON-like structure
                    content = f"{script_for_manim}\n\n{script_voice_over}"

                file_path.write_text(content, encoding="utf-8")
                generated_files[f"{ft}_files"].append(str(file_path))
                pipeline_logger.info(f"✅ Created {ft.upper()} file: {file_path}")

        pipeline_logger.info(f"🎉 All files generated inside: {base_path}")
        return generated_files


class JsonHandler(InputHandler):
    """Concrete handler for JSON input."""

    def set_credentials(self, credentials: dict):
        self.credentials = credentials

    def handle(self, json_file: str,file_types):
        pipeline_logger.info(f"📝 Generating Python and TXT files from JSON: {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._generate_files(data, Path(json_file).stem,file_types)


class PostgresHandler(InputHandler):
    """Concrete handler for fetching scripts from PostgreSQL."""

    def set_credentials(self, credentials: dict):
        """
        Save DB credentials.
        Expected keys: host, port, user, password, dbname
        """
        self.credentials = credentials

    def handle(self, query: str,file_types):
        if not self.credentials:
            raise ValueError("❌ No DB credentials set for PostgresHandler")

        conn = psycopg2.connect(
            host=self.credentials["host"],
            port=self.credentials["port"],
            user=self.credentials["user"],
            password=self.credentials["password"],
            dbname=self.credentials["dbname"],
        )
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        data = [dict(zip(col_names, row)) for row in rows]

        cursor.close()
        conn.close()

        pipeline_logger.info("📝 Generating Python and TXT files from Postgres data")
        return self._generate_files(data, "postgres_input",file_types)


class InputHandlerFactory:
    """Factory that returns handlers based on type."""

    @staticmethod
    def get_input_handler(handler_type: str) -> InputHandler:
        if handler_type == "local":
            return JsonHandler()
        elif handler_type == "postgres":
            return PostgresHandler()
        else:
            raise ValueError(f"Invalid handler type: {handler_type}")
