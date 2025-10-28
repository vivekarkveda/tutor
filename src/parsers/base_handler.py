# src/processor/input_handler.py
import json
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
import psycopg2
from logger import pipeline_logger, validation_logger


class InputHandler(ABC):
    """Abstract base for input handlers."""

    BASE_INPUT_PATH = Path(r"C:\Vivek_Main\Manim_project\inputbox")

    def __init__(self):
        self.credentials = None

    @abstractmethod
    def set_credentials(self, credentials: dict):
        pass

    @abstractmethod
    def handle(self, data, file_types=None):
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

        total_words = 0
        total_tokens = 0

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
                    # fallback: save both parts as plain text
                    content = f"{script_for_manim}\n\n{script_voice_over}"

                if isinstance(content, (dict, list)):
                    file_path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
                else:
                    file_path.write_text(str(content), encoding="utf-8")

                # 🔍 Count words + estimate GPT tokens
                word_count, token_count = self.count_words_in_file(file_path)
                total_words += word_count
                total_tokens += token_count

                msg = (
                    f"🧮 File: {file_path.name} | "
                    f"base_handler Words: {word_count} | Approx. GPT Tokens: {token_count}"
                )
                print(msg)
                pipeline_logger.debug(msg)
                pipeline_logger.info(f"✅ Created {ft.upper()} file: {file_path}")

        summary = (
            f"🎯 Total Words: {total_words} | "
            f"Approx. Total GPT Tokens: {total_tokens}"
        )
        print("\n" + summary)
        pipeline_logger.info(summary)

        pipeline_logger.info(f"🎉 All files generated inside: {base_path}")
        return generated_files

    # 🧮 Helper to count words + estimate GPT tokens
    @staticmethod
    def count_words_in_file(file_path: Path):
        """Counts the number of words and approximates GPT tokens in a file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            words = content.split()
            word_count = len(words)
            approx_tokens = int(word_count / 0.75)  # 1 token ≈ 0.75 words
            return word_count, approx_tokens
        except Exception as e:
            validation_logger.error(f"❌ Failed to count words in {file_path}: {e}")
            return 0, 0


class JsonHandler(InputHandler):
    """Concrete handler for JSON input."""

    def set_credentials(self, credentials: dict):
        self.credentials = credentials

    def handle(self, json_file: str, file_types):
        pipeline_logger.info(f"📝 Generating Python and TXT files from JSON: {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._generate_files(data, Path(json_file).stem, file_types)


class PostgresHandler(InputHandler):
    """Concrete handler for fetching scripts from PostgreSQL."""

    def set_credentials(self, credentials: dict):
        """
        Save DB credentials.
        Expected keys: host, port, user, password, dbname
        """
        self.credentials = credentials

    def handle(self, query: str, file_types):
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
        return self._generate_files(data, "postgres_input", file_types)


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
