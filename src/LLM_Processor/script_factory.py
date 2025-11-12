import cohere
from abc import ABC, abstractmethod
from config import Settings
# === Abstract Base Product ===
# === Abstract Base Product ===
class ScriptGenerator(ABC):
    """
    Abstract base class for all script generators.
    """
    @abstractmethod
    def generate_script(self, topic: str) -> str:
        pass
# === Concrete Product: Cohere ===
class CohereScriptGenerator(ScriptGenerator):
    """
    Concrete implementation using Cohere's Command model.
    """
    def __init__(self, api_key: str):
        self.client = cohere.ClientV2(api_key)
    def generate_script(self, topic: str) -> str:
        # === Load prompt from external file ===
        with open(Settings.JSON_PROMPT_PATH , "r", encoding="utf-8") as f:
            prompt_template = f.read()
        # Replace {topic} placeholder with the actual topic
        prompt = prompt_template.replace("{topic}", topic)
        print(f":brain: Generating script for topic: {topic}")
        response = self.client.chat(
            model="command-a-03-2025",
            messages=[{"role": "user", "content": prompt}]
        )
        script_json = response.message.content[0].text.strip()
        print(":white_check_mark: Script generated successfully.")
        return script_json
# === Concrete Product: Mock Generator (for testing) ===
class MockScriptGenerator(ScriptGenerator):
    """
    Mock generator for testing without calling external APIs.
    """
    def generate_script(self, topic: str) -> str:
        print(f":test_tube: Mock generating script for topic: {topic}")
        return f"""[
            {{
                "script_seq": 1,
                "script_for_manim": ["Display topic title '{topic}'"],
                "script_voice_over": ["Welcome! Today we'll discuss {topic}."],
                "script_length": 30
            }}
        ]"""
# === Factory Class ===
class ScriptGeneratorFactory:
    """
    Factory class for creating appropriate ScriptGenerator instances.
    """
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
