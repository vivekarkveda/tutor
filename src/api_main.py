from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel, RootModel
from datetime import datetime
from pathlib import Path
import json
import os
import httpx
import asyncio

from config import Settings
from logger import pipeline_logger
from main import prepare_files, process_pipeline
from LLM_Processor.script_factory import ScriptGeneratorFactory


# ================================================================
#  🚀 FastAPI Setup
# ================================================================
app = FastAPI(title="🎬 Video Processing Pipeline API")
API_KEY = "ItjCVeX2H4je76T4Az0yQGnjISqZhD3IrKWj6ebq"
BASE_INPUT_ROOT = Path(r"C:\Vivek_Main\Manim_project\inputbox")


# ================================================================
#  🧰 Helper Functions
# ================================================================
def get_latest_input_folder(base_dir: Path) -> Path:
    """Find the most recent input_data_* folder."""
    input_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("input_data_")]
    if not input_dirs:
        raise FileNotFoundError(f"No input_data_* folders found in {base_dir}")
    return max(input_dirs, key=lambda d: d.stat().st_mtime)


def save_json_to_temp(data: List[Dict]) -> Path:
    """Save JSON data into a timestamped folder under TEMP_GENERATED_FOLDER."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(Settings.TEMP_GENERATED_FOLDER) / f"batch_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    json_path = temp_dir / "input_data.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    pipeline_logger.info(f"📄 JSON saved: {json_path}")
    return json_path


async def send_to_internal_api(url: str, json_data: str) -> Dict:
    """Send JSON to another FastAPI route asynchronously using httpx."""
    async with httpx.AsyncClient() as client:
        headers = {"Content-Type": "application/json"}
        response = await client.post(url, data=json_data, headers=headers)
        if response.status_code != 200:
            pipeline_logger.error(f"⚠️ Internal API error {response.status_code}: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


# ================================================================
#  1️⃣ /search — Generate Script + Trigger /generate-files-api
# ================================================================
@app.post("/search")
async def search(topic: str = Query(..., description="The topic to generate script for")):
    """
    Generate storytelling + animation script for a given topic,
    then automatically hit /generate-files-api with the generated JSON body.
    Example: POST http://127.0.0.1:8000/search?topic=pythagoras
    """
    try:
        # Step 1: Create generator via factory
        generator = ScriptGeneratorFactory.get_generator(
            generator_type="cohere",
            api_key=API_KEY
        )

        # Step 2: Generate JSON script
        script_json = generator.generate_script(topic)
        print("\n📝 Raw Script From Cohere:\n")
        print(script_json)

        # 🧹 Step 3: Clean markdown fences and stray characters
        cleaned_json = (
            script_json.strip()
            .removeprefix("```json").removeprefix("```JSON")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        # Step 4: Try parsing into a real JSON object
        try:
            parsed_json = json.loads(cleaned_json)
        except json.JSONDecodeError as je:
            raise HTTPException(
                status_code=400,
                detail=f"Generated script is not valid JSON. Error: {je}"
            )

        # Step 5: Automatically send to /generate-files-api
        api_url = "http://127.0.0.1:8000/generate-files-api"
        headers = {"Content-Type": "application/json"}

        print("\n🚀 Sending cleaned script to /generate-files-api ...\n")

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, json=parsed_json)

        if response.status_code == 200:
            print("🎬 Successfully sent to /generate-files-api!")
            file_response = response.json()
        else:
            print(f"⚠️ Failed to send script: {response.status_code}")
            file_response = {"error": response.text}

        # Step 6: Return combined result
        return {
            "status": "success",
            "topic": topic,
            "script": parsed_json,
            "file_generation": file_response
        }

    except Exception as e:
        print(f"❌ Error in /search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ================================================================
#  2️⃣ /generate-files-api — Save JSON + Generate Scripts
# ================================================================
@app.post("/generate-files-api")
async def generate_files_endpoint(input_data: List[Dict]):
    """Accepts JSON list, saves to temp, generates .py/.txt files."""
    try:
        json_path = save_json_to_temp(input_data)

        old_json_path = Settings.JSON_FILE_PATH
        Settings.JSON_FILE_PATH = str(json_path)

        try:
            generated_files = prepare_files(
                run_from=Settings.RUN_FROM,
                generate_new_files=True,
                file_types=Settings.FILE_TYPES,
            )
        finally:
            Settings.JSON_FILE_PATH = old_json_path

        return {
            "status": "success",
            "json_saved_in": str(json_path.parent),
            "generated_files": generated_files,
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error generating files")
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
#  3️⃣ /write-scripts — Write Python Scripts
# ================================================================
class ScriptData(RootModel[List[Dict[str, str]]]):
    pass


@app.post("/write-scripts")
def write_scripts(data: ScriptData):
    """Writes each script file into its respective folder."""
    try:
        latest_folder = get_latest_input_folder(BASE_INPUT_ROOT)

        for item in data.root:
            for folder_name, content in item.items():
                folder = latest_folder / folder_name
                folder.mkdir(parents=True, exist_ok=True)

                file_path = folder / f"{folder_name}.py"
                decoded_script = bytes(content, "utf-8").decode("unicode_escape")
                file_path.write_text(decoded_script, encoding="utf-8")

                pipeline_logger.info(f"✅ Script written: {file_path}")

        return {
            "status": "success",
            "message": "Scripts written successfully.",
            "target_directory": str(latest_folder),
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error writing scripts")
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
#  4️⃣ /generate-videos-api — Create Final Video
# ================================================================
class VideoRequest(BaseModel):
    path: Optional[str] = None


@app.post("/generate-videos-api")
async def generate_videos_endpoint(request: VideoRequest):
    """Generates final videos from latest or given input_data folder."""
    try:
        input_path = Path(request.path) if request.path else get_latest_input_folder(BASE_INPUT_ROOT)
        if not input_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {input_path}")

        py_files = [f.as_posix() for f in input_path.rglob("*.py")]
        txt_files = [f.as_posix() for f in input_path.rglob("*.txt")]
        if not py_files or not txt_files:
            raise HTTPException(status_code=400, detail=f"No .py or .txt files in {input_path}")

        pipeline_logger.info(f"🎞️ Processing: {len(py_files)} py + {len(txt_files)} txt")
        generated_files = [{"py_files": py_files, "txt_files": txt_files}, str(input_path)]

        # Run video pipeline asynchronously
        output_path = await process_pipeline(
            generated_files,
            Settings.VIDEO_PROCESSOR,
            Settings.AUDIO_PROCESSOR,
            Settings.RUN_FROM,
        )

        pipeline_logger.info(f"🎬 Final video saved: {output_path}")
        return {
            "status": "success",
            "final_video": output_path,
            "processed_from": str(input_path),
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error during video generation")
        raise HTTPException(status_code=500, detail=str(e))
