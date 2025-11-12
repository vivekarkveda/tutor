import cohere
import json
import requests
from typing import List, Dict
from langchain_cohere import ChatCohere
from langchain_core.prompts import PromptTemplate
from config import Settings
# === Utility: Qdrant Integration ===
def merge_qdrant_snippet_into_prompt(
    prompt: str,
    query_text: str,
    collection: str = "CATALOG",
    placeholder: str = "{catalog}",
    qdrant_api_url: str = "http://127.0.0.1:8880/search",
    min_score: float = 0.30
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
# === Main Generator Class ===
class CodeGenerator:
    """
    Generates high-quality Manim animation Python code using LangChain + Cohere.
    - Injects relevant Qdrant snippets into prompt.
    - Keeps previous code as context for continuity.
    - Logs full prompt and output for debugging.
    """
    def __init__(self, api_key: str):
        self.client = cohere.ClientV2(api_key)
        self.llm = ChatCohere(model="command-r-plus-08-2024", cohere_api_key=api_key)
        self.prompt_template = PromptTemplate(
            input_variables=["final_prompt"],
            template="{final_prompt}"
        )
    def generate_code(self, input_data: List[Dict]) -> List[Dict]:
        result = []
        previous_code = ""  # :white_check_mark: carry forward between scenes
        for obj in input_data:
            script_seq = obj.get("script_seq", "Unknown_Seq")
            script_for_manim = obj.get("script_for_manim", [])
            script_voice_over = obj.get("script_voice_over", [])
            script_length = obj.get("script_length", 30)
            placeholder = "{catalog}"
            with open(Settings.MANIM_CODE_PROMPT_PATH , "r" , encoding="utf-8") as f:
                    prompt_template = f.read()
            # Replace placeholders in your prompt file
            prompt = (
                prompt_template
                .replace("{catalog}", "{catalog}")  # leave placeholder for Qdrant merge
                .replace("{script_seq}", str(script_seq))
                .replace("{script_for_manim}", json.dumps(script_for_manim, indent=2))
                .replace("{script_voice_over}", json.dumps(script_voice_over, indent=2))
                .replace("{script_length}", str(script_length))
                .replace("{previous_code}", previous_code)
            )
            print(f"\n:brain: Generating Manim code for {script_seq}...")
            # === Merge Qdrant snippet ===
            final_prompt = merge_qdrant_snippet_into_prompt(
                prompt=prompt,
                query_text=" ".join(script_for_manim),
                collection="CATALOG",
                placeholder=placeholder,
                qdrant_api_url="http://127.0.0.1:8880/search",
                min_score=0.30
            )
            # === LangChain Integration ===
            try:
                chain = self.prompt_template | self.llm
                output = chain.invoke({"final_prompt": final_prompt})
                manim_code = output.content.strip()
            except Exception as e:
                print(f":x: LangChain generation failed: {e}")
                manim_code = ""
            # === Log ===
            log_filename = f"debug_log_script_{script_seq}.txt"
            with open(log_filename, "w", encoding="utf-8") as log_file:
                log_file.write("=== FINAL PROMPT SENT ===\n\n")
                log_file.write(final_prompt)
                log_file.write("\n\n=== GENERATED CODE ===\n\n")
                log_file.write(manim_code if manim_code else "[No output generated]")
            print(f":receipt: Log saved: {log_filename}")
            # === Cleanup markdown formatting ===
            if manim_code.startswith("```"):
                manim_code = (
                    manim_code.replace("```python", "")
                    .replace("```Python", "")
                    .replace("```", "")
                    .strip()
                )
            # :white_check_mark: Update context for next iteration
            previous_code = manim_code.strip()
            print(f":white_check_mark: Code generated for {script_seq}")
            result.append({
                f"script_seq{script_seq}": manim_code
            })
        return result