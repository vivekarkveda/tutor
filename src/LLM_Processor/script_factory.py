from fastapi import FastAPI, Query
import cohere
import requests
from abc import ABC, abstractmethod


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
        prompt = f"""
You are an expert in storytelling and Manim Community Edition animation design.
Your task:
Generate a JSON script that describes the full video in a step-by-step, highly detailed way.
Each scene/sequence should have a flexible length between 25 to 45 seconds.
You can break the video into multiple sequences/scenes if needed to explain the concept clearly.
Narration and animations must be tightly synchronized:
Step i in "script_for_manim" must align exactly with step i in "script_voice_over".
Ensure pacing: narration should match animation timing naturally.
"script_length" should reflect the realistic duration of each scene.

Each JSON object must include:
- "script_seq" → scene number.
- "script_for_manim" → array of detailed English animation steps (no Manim code).
- "script_voice_over" → array of narration lines aligned step-by-step with visuals.
- "script_length" → approximate duration of the scene (25–45 seconds).

Rules:
- Use descriptive English for visuals (no code).
- Narration must align with visuals.
- Describe each animation step precisely.
- Break complex ideas into smaller, smooth transitions.
- Maintain consistent references between scenes.
- Scene 1: Introduction
- Scene 2: Concept Demonstration
- Scene 3: Application/Example
- Scene 4: Recap/Closing
📌 Continuity Rule: The last frame of a scene becomes the first frame of the next.

Output format:
Return only a valid JSON array (no extra text).

📌 Topic: {topic}
"""
        print(f"🧠 Generating script for topic: {topic}")
        response = self.client.chat(
            model="command-a-03-2025",
            messages=[{"role": "user", "content": prompt}]
        )
        script_json = response.message.content[0].text.strip()
        print("✅ Script generated successfully.")
        return script_json


# === Concrete Product: Mock Generator (for testing) ===
class MockScriptGenerator(ScriptGenerator):
    """
    Mock generator for testing without calling external APIs.
    """

    def generate_script(self, topic: str) -> str:
        print(f"🧪 Mock generating script for topic: {topic}")
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

