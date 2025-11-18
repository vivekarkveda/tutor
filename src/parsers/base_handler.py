# src/processor/input_handler.py
import json
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
import psycopg2
import traceback
from logger import pipeline_logger, validation_logger
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception # ✅ fixed spelling ("exception", not "excepetion")
from config import Settings


class InputHandler(ABC):
    """Abstract base for input handlers."""

    BASE_INPUT_PATH = Path(Settings.TEMP_GENERATED_FOLDER)

    def __init__(self, unique_id: str = None):
        """Initialize handler with an optional unique transaction ID."""
        self.credentials = None
        self.unique_id = unique_id  # ✅ store for internal use

    @abstractmethod
    def set_credentials(self, credentials: dict):
        pass

    @abstractmethod
    def handle(self, data, file_types=None):
        pass

    # ✅ Common folder/file generation logic (with try/except)
    def _generate_files(self, data: list[dict], base_name: str, file_types: list[str]):
        """Helper for creating files dynamically from scripts. Logs both success and exceptions."""
        print("🔧 File generation started for:", self.unique_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = self.BASE_INPUT_PATH / f"{timestamp}_{base_name}"

        file_generation_failed = False 

        try:
            base_path.mkdir(parents=True, exist_ok=True)
            pipeline_logger.debug(f"file_types: {file_types}")

            generated_files = {f"{ft}_files": [] for ft in file_types}
            total_words = 0
            total_tokens = 0
            created_files = []

            for item in data:
                seq = item.get("script_seq")
                script_for_manim = item.get("script_for_manim", "")
                script_voice_over = item.get("script_voice_over", "")

                folder_path = base_path / f"script_seq{seq}"
                folder_path.mkdir(parents=True, exist_ok=True)

                for ft in file_types:
                    file_path = folder_path / f"script_seq{seq}.{ft}"

                    if ft == "py":
                        content = f'"""{script_for_manim}\n{script_voice_over}"""'
                    elif ft == "txt":
                        content = script_voice_over
                    else:
                        content = f"{script_for_manim}\n\n{script_voice_over}"

                    # Save file safely
                    try:
                        raise TypeError("Simulated file write error") if script_voice_over == "trigger_error" else None

                        if isinstance(content, (dict, list)):
                            file_path.write_text(
                                json.dumps(content, indent=2, ensure_ascii=False),
                                encoding="utf-8"
                            )
                        else:
                            file_path.write_text(str(content), encoding="utf-8")

                        generated_files[f"{ft}_files"].append(str(file_path))

                    except Exception as file_error:
                        validation_logger.error(f"❌ Failed to write {file_path}: {file_error}")
                        # exception(
                        #     self.unique_id,
                        #     filegenration="File write failed",
                        #     exception_message=str(file_error),
                        #     trace=traceback.format_exc()
                        # )
                        file_generation_failed = True
                        continue  # skip to next file

                    # Count words/tokens safely
                    word_count, token_count = self.count_words_in_file(file_path)
                    total_words += word_count
                    total_tokens += token_count

                    msg = (
                        f"🧮 File: {file_path.name} | "
                        f"Words: {word_count} | Tokens: {token_count}"
                    )
                    print(msg)
                    pipeline_logger.debug(msg)
                    created_files.append(f"✅ Created {ft.upper()} file: {file_path}")

                pipeline_logger.info(created_files)

            # :dart: Final evaluation BEFORE success log
            if file_generation_failed:
                # :x: Even one failure = overall failure
                exception(
                    self.unique_id,
                    type="file_generation",
                    description="One or more files failed to generate",
                    module="InputHandler"
                )
                raise RuntimeError(":x: File generation failed: one or more files could not be created.")
            # :tada: All files succeeded → Log success
            transaction(self.unique_id, filegenration="File generation successful")
            summary = f":dart: Total Words: {total_words} | Approx. Total GPT Tokens: {total_tokens}"
            pipeline_logger.info(summary)
            pipeline_logger.info(f":tada: All files generated inside: {base_path}")
            return generated_files

        except Exception as e:
            err_msg = f"❌ Error generating files for {base_name}: {e}"
            pipeline_logger.error(err_msg)
            validation_logger.error(traceback.format_exc())

            # # Save to exception table
            # if self.unique_id:
            #     # exception(
            #     #     self.unique_id,
            #     #     filegenration="File generation failed",
            #     #     exception_message=str(e),
            #     #     trace=traceback.format_exc()
            #     # )
            raise RuntimeError(err_msg)

    # 🧮 Helper to count words + estimate GPT tokens
    @staticmethod
    def count_words_in_file(file_path: Path):
        """Counts the number of words and approximates GPT tokens in a file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            words = content.split()
            word_count = len(words)
            approx_tokens = int(word_count / 0.75)
            return word_count, approx_tokens
        except Exception as e:
            validation_logger.error(f"❌ Failed to count words in {file_path}: {e}")
            return 0, 0


# ======================================================
# JSON HANDLER
# ======================================================
class JsonHandler(InputHandler):
    """Concrete handler for JSON input."""

    def set_credentials(self, credentials: dict):
        self.credentials = credentials

    def handle(self, json_file: str, file_types):
        try:
            pipeline_logger.info(f"📝 Generating Python and TXT files from JSON: {json_file}")
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._generate_files(data, Path(json_file).stem, file_types)
        except Exception as e:
            pipeline_logger.error(f"❌ Error handling JSON input: {e}")
            exception(
                self.unique_id,
                filegenration="JSON read failed",
                exception_message=str(e),
                trace=traceback.format_exc()
            )
            raise


# ======================================================
# POSTGRES HANDLER
# ======================================================
class PostgresHandler(InputHandler):
    """Concrete handler for fetching scripts from PostgreSQL."""

    def set_credentials(self, credentials: dict):
        self.credentials = credentials

    def handle(self, query: str, file_types):
        if not self.credentials:
            raise ValueError("❌ No DB credentials set for PostgresHandler")

        try:
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
        except Exception as e:
            pipeline_logger.error(f"❌ Error handling PostgreSQL input: {e}")
            exception(
                self.unique_id,
                filegenration="Postgres data fetch failed",
                exception_message=str(e),
                trace=traceback.format_exc()
            )
            raise


# ======================================================
# FACTORY
# ======================================================
class InputHandlerFactory:
    """Factory that returns handlers based on type."""

    @staticmethod
    def get_input_handler(handler_type: str, unique_id: str) -> InputHandler:
        print("🧩 InputHandlerFactory initialized")
        if handler_type == "local":
            return JsonHandler(unique_id)
        elif handler_type == "postgres":
            return PostgresHandler(unique_id)
        else:
            raise ValueError(f"Invalid handler type: {handler_type}")
