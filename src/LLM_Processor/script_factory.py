import cohere
from abc import ABC, abstractmethod
from config import Settings
from logger import pipeline_logger, validation_logger
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception
from logger import pipeline_logger, validation_logger
import traceback
# === Abstract Base Product ===
class ScriptGenerator(ABC):
    """Abstract base class for all script generators."""
    @abstractmethod
    def generate_script(self, topic: str,unique_id: str) -> str:
        pass
# === Concrete Product: Cohere ===
class CohereScriptGenerator(ScriptGenerator):
    """Concrete implementation using Cohere's Command model."""

    def __init__(self, api_key: str):
        self.client = cohere.ClientV2(api_key)

    def generate_script(
        self,
        topic: str,
        unique_id: str,
        scene_duration_range: str = Settings.DEFAULT_SCENE_DURATION_RANGE,
        total_video_length_target: str = Settings.DEFAULT_TOTAL_VIDEO_LENGTH_TARGET,
    ) -> str:
        """Generate a parameterized video JSON script using Cohere."""

        # === Load prompt from file ===
        try:
            with open(Settings.TEST_JSON_PROMPT_PATH, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            transaction(unique_id, script_gen_status="script generation successfull")
        except Exception as e:
            transaction(
                unique_id=unique_id,
                script_gen_status="script generation failed"
            )
            exception(unique_id, type="script" ,description="json script generation failed", module="CohereScriptGenerator")
            raise RuntimeError(f"Failed to load prompt template: {e}")

        # === Fill placeholders dynamically ===
        try:
            prompt = prompt_template.format(
                topic=topic,
                scene_duration_range=scene_duration_range,
                total_video_length_target=total_video_length_target
            )
        except KeyError as e:
            raise ValueError(f"Missing placeholder in prompt file: {e}")

        print(f":brain: Generating script for topic: {topic}")
        print(f":stopwatch: Scene duration range: {scene_duration_range}")
        print(f":clapper: Total video length target: {total_video_length_target}")

        # === Call Cohere inside try/except ===
        try:
            response = self.client.chat(
                model="command-a-03-2025",
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract result text
            script_json = response.message.content[0].text.strip()

            print(":white_check_mark: Script generated successfully.")

            transaction(
                unique_id,
                script_gen_status="script generated successfully"
            )

            return script_json

        except Exception as e:
            # Capture traceback + log
            error_trace = traceback.format_exc()

            transaction(
                unique_id,
                script_gen_status="script generation failed",
            )
            exception(unique_id, type="script" ,description="json script generation failed", module="script_factory")

            print(f":x: Script generation failed: {e}")
            raise RuntimeError(f"Script generation failed: {e}")
# === Concrete Product: Mock Generator ===
class MockScriptGenerator(ScriptGenerator):
    """Mock generator for offline testing."""
    def generate_script(
        self,
        topic: str,
        unique_id: str,
        scene_duration_range: str = "25–45 seconds",
        total_video_length_target: str = "2–3 minutes",
        ) -> str:
        try:
            print(f":test_tube: Mock generating script for topic: {topic}")
            mock_script = f"""[
                {{
                    "script_seq": 1,
                    "script_for_manim": ["Display topic title '{topic}'"],
                    "script_voice_over": ["Welcome! Today we'll discuss {topic}."],
                    "script_length": 30
                }}
            ]"""
            # :white_check_mark: Log success
            transaction(unique_id, script_gen_status="Mock script generated successfully")
            return mock_script
        except Exception as e:
            # :x: Log error
            exception(
                unique_id,
                script_gen_status="Mock script generation failed",
                exception_message=str(e),
                trace=traceback.format_exc()
            )
            raise
# === Factory ===
class ScriptGeneratorFactory:
    """Factory to create a script generator instance."""
    @staticmethod
    def get_generator(generator_type: str, **kwargs) -> ScriptGenerator:
        if generator_type == "cohere":
            api_key = kwargs.get("api_key")
            if not api_key:
                raise ValueError("API key required for Cohere generator.")
            return CohereScriptGenerator(api_key)
        elif generator_type == "mock":
            return MockScriptGenerator()
        else:
            raise ValueError(f"Unknown generator type: {generator_type}")