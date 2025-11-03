from fastapi import FastAPI, HTTPException
from typing import List, Dict
import cohere
import json
import requests
# === Utility: Qdrant Integration ===
def merge_qdrant_snippet_into_prompt(
    prompt: str,
    query_text: str,
    collection: str = "CATALOG",
    placeholder: str = "{catalog}",
    qdrant_api_url: str = "http://127.0.0.1:8880/search",
    min_score: float = 0.70
) -> str:
    """
    Fetch the most relevant code snippet from Qdrant (matching Category with topic)
    and insert it into the given prompt at the specified placeholder.
    """
    try:
        payload = {"collection": collection, "query": query_text, "top_k": 1}
        response = requests.post(qdrant_api_url, json=payload)
        response.raise_for_status()
        results = response.json()
        if not results or not isinstance(results, list):
            print(":warning: No valid results returned from Qdrant API.")
            return prompt.replace(placeholder, "")
        best_match = results[0]
        score = float(best_match.get("score", 0))
        category = best_match.get("Category", "Unknown")
        code_snippet = best_match.get("Sample Snippet", "[No snippet found]")
        print(f":mag: Matched Category: {category} | Score: {score:.2f}")
        if score < min_score:
            print(f":warning: Skipping insertion — score below threshold ({min_score}).")
            return prompt.replace(placeholder, "")
        if placeholder not in prompt:
            print(f":warning: Placeholder '{placeholder}' not found. Appending snippet at end.")
            final_prompt = f"{prompt}\n\nReference Code Snippet:\n```python\n{code_snippet}\n```"
        else:
            final_prompt = prompt.replace(placeholder, code_snippet)
        print(":white_check_mark: Code snippet merged successfully.")
        return final_prompt
    except requests.RequestException as e:
        print(f":x: Qdrant API request failed: {e}")
        return prompt
    except Exception as e:
        print(f":x: Unexpected error: {e}")
        return prompt
# === Main Generator ===
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
            # Placeholder variable
            placeholder = "{catalog}"
            # === Build Prompt ===
            prompt = f"""
You are a specialist in producing high-quality educational animations using Manim v0.19.0 (Python).
Your goal is to turn a provided topic script into a visually clear, accurate, and fully executable Python animation that communicates concepts step-by-step.
Follow these CRITICAL INSTRUCTIONS exactly as described:
...
Now, based on the following structured input:
CATALOG: {placeholder}
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
            print(f"\n:brain: Generating Manim code for {script_seq}...")
            # :white_check_mark: Fetch and insert code from Qdrant
            final_prompt = merge_qdrant_snippet_into_prompt(
                prompt=prompt,
                query_text=" ".join(script_for_manim),
                collection="CATALOG",
                placeholder=placeholder,
                qdrant_api_url="http://127.0.0.1:8880/search",
                min_score=0.70
            )
            # :brain: Call Cohere once
            print(f":brain: Sending prompt to Cohere for topic: {script_for_manim}")
            print("final_prompt", final_prompt)
            response = self.client.chat(
                model="command-a-03-2025",
                messages=[{"role": "user", "content": final_prompt}]
            )
            # Extract model output
            manim_code = response.message.content[0].text.strip()
            # Clean Markdown fences if Cohere includes them
            if manim_code.startswith("```"):
                manim_code = (
                    manim_code.replace("```python", "")
                    .replace("```Python", "")
                    .replace("```", "")
                    .strip()
                )
            print(f":white_check_mark: Code generated for {script_seq}")
            result.append({f"script_seq{script_seq}": manim_code})
        return result


