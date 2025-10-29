from fastapi import FastAPI, HTTPException
from typing import List, Dict
import cohere
import json

class CodeGenerator:
    def __init__(self, api_key: str):
        self.client = cohere.ClientV2(api_key)

    def generate_code(self, input_data: List[Dict]) -> List[Dict]:
        """
        For each script object, generate high-quality Manim animation Python code
        following strict spatial and mathematical rules.
        """

        result = []

        for obj in input_data:
            # Extract values from JSON object
            script_seq = obj.get("script_seq", "Unknown_Seq")
            script_for_manim = obj.get("script_for_manim", [])
            script_voice_over = obj.get("script_voice_over", [])
            script_length = obj.get("script_length", 30)

            # === Build Prompt ===
            prompt = f"""
You are a specialist in producing high-quality educational animations using Manim v0.19.0 (Python). 
Your goal is to turn a provided topic script into a visually clear, accurate, and fully executable Python animation that communicates concepts step-by-step.

Follow these CRITICAL INSTRUCTIONS exactly as described:
{(' ' * 4).join(open('prompt_rules.txt').read().splitlines()) if False else "..."}

Now, based on the following structured input:

SCRIPT_SEQ: {script_seq}
SCRIPT_FOR_MANIM: {json.dumps(script_for_manim, indent=2)}
SCRIPT_VOICE_OVER: {json.dumps(script_voice_over, indent=2)}
SCRIPT_LENGTH: {script_length}

Generate the FULL Manim Python code that:
- Follows all layout, geometry, boundary, and animation rules.
- Produces a step-by-step educational animation.
- Uses correct scaling and non-overlapping text.
- Is self-contained and executable without errors.
- Returns ONLY valid Python code (no explanations or Markdown formatting).
            """

            print(f"\n🧠 Generating Manim code for {script_seq}...")

            response = self.client.chat(
                model="command-a-03-2025",
                messages=[{"role": "user", "content": prompt}],
            )

            manim_code = response.message.content[0].text.strip()

            # Remove Markdown fences if Cohere adds them
            if manim_code.startswith("```"):
                manim_code = (
                    manim_code.replace("```python", "")
                    .replace("```Python", "")
                    .replace("```", "")
                    .strip()
                )

            print(f"✅ Code generated for {script_seq}")

            result.append({f"script_seq{script_seq}": manim_code})

        return result