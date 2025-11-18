import cohere
import json
import requests
from typing import List, Dict, Optional
from langchain_cohere import ChatCohere
from langchain_core.prompts import PromptTemplate
from config import Settings
import os
# === Utility: Qdrant Integration ===
def merge_qdrant_snippets_into_prompt(
    prompt: str,
    query_text: str,
    catalog_collection: str = "CATALOG",
    Bug_fix_collection: str = "BUGFIX",
    catalog_placeholder: str = "{catalog}",
    Bug_fix_placeholder: str = "{Bug_fix}",
    qdrant_api_url: str = "http://127.0.0.1:8880/search",
    min_score: float = 0.20
) -> str:
    """
    Fetch the most relevant code snippet and Bug_fix hint from Qdrant,
    and merge them into the given prompt at their respective placeholders.
    """
    def fetch_best_match(collection: str) -> Optional[Dict]:
        try:
            payload = {"collection": collection, "query": query_text, "top_k": 1}
            response = requests.post(qdrant_api_url, json=payload)
            response.raise_for_status()
            results = response.json()
            print(f":mag: Fetched results from {collection}: {results}")
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
        # === Fetch Bug_fix Snippet ===
        Bug_fix_match = fetch_best_match(Bug_fix_collection)
        Bug_fix_snippet = ""
        if Bug_fix_match:
            score = float(Bug_fix_match.get("score", 0))
            if score >= min_score:
                bug_snip = Bug_fix_match.get("BUG SNIPPET", "").strip()
                fixed_snip = Bug_fix_match.get("FIXED BUG SNIPPET", "").strip()
                # Combine both properly in Markdown format
                Bug_fix_snippet = (
                    f"# Original Bug Snippet:\n```python\n{bug_snip}\n```\n\n"
                    f"# Fixed Bug Snippet:\n```python\n{fixed_snip}\n```"
                )
                print(f":white_check_mark: Bug_fix match accepted (score {score:.2f})")
                print(f" Bug Snippet: {bug_snip[:80]}...")  # for preview
                print(f" Fixed Snippet: {fixed_snip[:80]}...")
            else:
                print(f":warning: Bug_fix snippet skipped (score {score:.2f} < {min_score})")
    # === Merge Snippets ===
    final_prompt = prompt
    if catalog_placeholder in prompt:
        final_prompt = final_prompt.replace(catalog_placeholder, catalog_snippet or "")
    else:
        final_prompt += f"\n\n# Reference Catalog Snippet:\n```python\n{catalog_snippet}\n```"
    if Bug_fix_placeholder in prompt:
        final_prompt = final_prompt.replace(Bug_fix_placeholder, Bug_fix_snippet or "")
    else:
        final_prompt += f"\n\n# Bug_fix Hint:\n```python\n{Bug_fix_snippet}\n```"
    print(":white_check_mark: Qdrant snippets merged successfully.")
    return final_prompt
# === Main Generator Class ===
class CodeGenerator:
    """
    Generates high-quality Manim animation Python code using LangChain + Cohere.
    - Injects relevant Qdrant snippets into prompt.
    - Keeps previous code as context for continuity.
    - Logs full prompt and output for Bug_fixging.
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
            catalog_placeholder = "{catalog}"
            Bug_fix_placeholder = "{Bug_fix}"
            # === Load prompt template file safely ===
            try:
                with open(Settings.TEST_MANIM_PROMPT_PATH, "r", encoding="utf-8") as f:
                    prompt_template = f.read() or ""
            except Exception as e:
                print(f":x: Failed to read prompt file: {e}")
                prompt_template = ""
            # === Defensive conversion to strings ===
            script_seq_str = str(script_seq or "")
            script_for_manim_str = json.dumps(script_for_manim or [], indent=2)
            script_voice_over_str = json.dumps(script_voice_over or [], indent=2)
            script_length_str = str(script_length or "")
            previous_code_str = str(previous_code or "")
            # === Build prompt with safe replacements ===
            prompt = (
                prompt_template
                .replace("{catalog}", "{catalog}")  # keep placeholder for Qdrant merge
                .replace("{Bug_fix}", "{Bug_fix}")  # keep placeholder for Qdrant merge
                .replace("{script_seq}", script_seq_str)
                .replace("{script_for_manim}", script_for_manim_str)
                .replace("{script_voice_over}", script_voice_over_str)
                .replace("{script_length}", script_length_str)
                .replace("{previous_code}", previous_code_str)
            )
            print(f"\n:brain: Generating Manim code for {script_seq}...")
            # === Fetch and merge snippets ===
            final_prompt = merge_qdrant_snippets_into_prompt(
                prompt=prompt,
                query_text=" ".join(script_for_manim or []),
                catalog_collection="CATALOG",
                Bug_fix_collection="BUGFIX",
                catalog_placeholder=catalog_placeholder,
                Bug_fix_placeholder=Bug_fix_placeholder,
                qdrant_api_url="http://127.0.0.1:8880/search",
                min_score=0.20
            )
            # === LangChain Integration ===
            try:
                chain = self.prompt_template | self.llm
                output = chain.invoke({"final_prompt": final_prompt})
                manim_code = output.content.strip() if output and hasattr(output, "content") else ""
            except Exception as e:
                print(f":x: LangChain generation failed: {e}")
                manim_code = ""
            # === Log the prompt and result ===
            log_dir = "final_prompt"
            os.makedirs(log_dir, exist_ok=True)
            log_filename = f"Final_prompt_{script_seq}.txt"
            log_path = os.path.join(log_dir, log_filename)
            try:
                with open(log_path, "w", encoding="utf-8") as log_file:
                    log_file.write("=== FINAL PROMPT SENT ===\n\n")
                    log_file.write(final_prompt)
                    log_file.write("\n\n=== GENERATED CODE ===\n\n")
                    log_file.write(manim_code if manim_code else "[No output generated]")
                print(f":receipt: Log saved: {log_path}")
            except Exception as e:
                print(f":warning: Failed to save log file for {script_seq}: {e}")
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

