from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
import cohere
import json
import requests
from logger import pipeline_logger


# === Utility: Qdrant Integration ===
def merge_qdrant_snippets_into_prompt(
    prompt: str,
    query_text: str,
    catalog_collection: str = "CATALOG",
    debug_collection: str = "Bugs_fixes",
    catalog_placeholder: str = "{catalog}",
    debug_placeholder: str = "{debug}",
    qdrant_api_url: str = "http://127.0.0.1:8880/search",
    min_score: float = 0.70
) -> str:
    """
    Fetch the most relevant code snippet and debug hint from Qdrant,
    and merge them into the given prompt at their respective placeholders.
    """

    def fetch_best_match(collection: str) -> Optional[Dict]:
        try:
            payload = {"collection": collection, "query": query_text, "top_k": 1}
            response = requests.post(qdrant_api_url, json=payload)
            response.raise_for_status()
            results = response.json()
            if not results or not isinstance(results, list):
                print(f":warning: No valid results from {collection}.")
                return None
            return results[0]
        except requests.RequestException as e:
            print(f":x: Qdrant request failed for {collection}: {e}")
            return None
        except Exception as e:
            print(f":x: Unexpected error during {collection} fetch: {e}")
            return None

    # === Fetch Catalog Snippet ===
    catalog_match = fetch_best_match(catalog_collection)
    catalog_snippet = ""
    if catalog_match:
        score = float(catalog_match.get("score", 0))
        if score >= min_score:
            catalog_snippet = catalog_match.get("Sample Snippet", "")
            print(f":white_check_mark: Catalog match accepted (score {score:.2f})")
        else:
            print(f":warning: Catalog snippet skipped (score {score:.2f} < {min_score})")

    # === Fetch Debug Snippet ===
    debug_match = fetch_best_match(debug_collection)
    debug_snippet = ""
    if debug_match:
        score = float(debug_match.get("score", 0))
        if score >= min_score:
            debug_snippet = debug_match.get("Sample Snippet", "")
            print(f":white_check_mark: Debug match accepted (score {score:.2f})")
        else:
            print(f":warning: Debug snippet skipped (score {score:.2f} < {min_score})")

    # === Merge Snippets ===
    final_prompt = prompt
    if catalog_placeholder in prompt:
        final_prompt = final_prompt.replace(catalog_placeholder, catalog_snippet)
    else:
        final_prompt += f"\n\n# Reference Catalog Snippet:\n```python\n{catalog_snippet}\n```"

    if debug_placeholder in prompt:
        final_prompt = final_prompt.replace(debug_placeholder, debug_snippet)
    else:
        final_prompt += f"\n\n# Debug Hint:\n```python\n{debug_snippet}\n```"

    print(":white_check_mark: Qdrant snippets merged successfully.")
    return final_prompt


# === Main Generator ===
class CodeGenerator:
    def __init__(self, api_key: str):
        self.client = cohere.ClientV2(api_key)

    def generate_code(self, input_data: List[Dict]) -> List[Dict]:
        """
        For each script object, generate high-quality Manim animation Python code
        following strict spatial and mathematical rules.
        """
        results = []
        prompt_data = []

        for obj in input_data:
            script_seq = obj.get("script_seq", "Unknown_Seq")
            script_for_manim = obj.get("script_for_manim", [])
            script_voice_over = obj.get("script_voice_over", [])
            script_length = obj.get("script_length", 30)

            catalog_placeholder = "{catalog}"
            debug_placeholder = "{debug}"

            prompt = f"""
You are a specialist in producing high-quality educational animations using Manim v0.19.0 (Python).
Your goal is to turn a provided topic script into a visually clear, accurate, and fully executable Python animation.

Follow these CRITICAL INSTRUCTIONS exactly as described:
- Maintain precise spatial geometry and proportions.
- Use legible, non-overlapping text.
- Include accurate math-based animation sequences.
- Avoid redundant or commented-out code.

Now, based on the following structured input:

DEBUG: {debug_placeholder}
CATALOG: {catalog_placeholder}
SCRIPT_SEQ: {script_seq}
SCRIPT_FOR_MANIM: {json.dumps(script_for_manim, indent=2)}
SCRIPT_VOICE_OVER: {json.dumps(script_voice_over, indent=2)}
SCRIPT_LENGTH: {script_length}

Generate the FULL Manim Python code that:
- Follows all layout and animation rules.
- Is executable and error-free.
- Returns ONLY valid Python code (no Markdown or explanations).
"""

            print(f"\n:brain: Generating Manim code for {script_seq}...")

            # Fetch and merge snippets
            final_prompt = merge_qdrant_snippets_into_prompt(
                prompt=prompt,
                query_text=" ".join(script_for_manim),
                catalog_collection="CATALOG",
                debug_collection="Bugs_fixes",
                catalog_placeholder=catalog_placeholder,
                debug_placeholder=debug_placeholder,
                qdrant_api_url="http://127.0.0.1:8880/search",
                min_score=0.70
            )

            

            print(f":brain: Sending prompt to Cohere for topic: {script_for_manim}")
            response = self.client.chat(
                model="command-a-03-2025",
                messages=[{"role": "user", "content": final_prompt}]
            )

            manim_code = response.message.content[0].text.strip()
            if manim_code.startswith("```"):
                manim_code = (
                    manim_code.replace("```python", "")
                    .replace("```Python", "")
                    .replace("```", "")
                    .strip()
                )


            prompt_data.append(f"{script_seq}.{final_prompt}")



            

            print(f":white_check_mark: Code generated for {script_seq}")
            results.append({f"script_seq{script_seq}": manim_code})

        pipeline_logger.info(f"prompt_data  {prompt_data}")
        pipeline_logger.info(f"results {results}")

        return results
