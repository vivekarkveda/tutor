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
from LLM_Processor.codeGen_factory import CodeGenerator

topicName = ""


# ================================================================
#  🚀 FastAPI Setup
# ================================================================
app = FastAPI(title="🎬 Video Processing Pipeline API")
API_KEY = "dZfHrqzrU2lw32MX2RPRiG8ARSKqavpiqpLsU2b0"
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
    # pipeline_logger.info(f"📄 JSON saved: {json_path}")
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
    1️⃣ Generate storytelling JSON script from Cohere.
    2️⃣ Send to /generate-files-api to create base files.
    3️⃣ Send to /Generator to create Manim Python scripts.
    4️⃣ Return combined structured response.
    """
    try:
        print(f"\n🧠 Generating script for topic: {topic}")
        generator = ScriptGeneratorFactory.get_generator(
            generator_type="cohere",
            api_key=API_KEY
        )

        script_json = generator.generate_script(topic)
        print("\n📝 Raw Script From Cohere:\n", script_json)


        cleaned_json = (
            script_json.strip()
            .removeprefix("```json")
            .removeprefix("```JSON")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )


        try:
            parsed_json = json.loads(cleaned_json)
        except json.JSONDecodeError as je:
            raise HTTPException(
                status_code=400,
                detail=f"Generated script is not valid JSON. Error: {je}"
            )

        api_generate = "http://127.0.0.1:8000/generate-files-api"
        api_generator = "http://127.0.0.1:8000/Generator"
        headers = {"Content-Type": "application/json"}

        print("\n🚀 Sending script to /generate-files-api and /Generator...\n")

        async with httpx.AsyncClient(timeout=180) as client:

            gen_task = client.post(api_generate, headers=headers, json=parsed_json)
            code_task = client.post(api_generator, headers=headers, json=parsed_json)
            responses = await asyncio.gather(gen_task, code_task, return_exceptions=True)


        gen_resp, code_resp = responses


        if isinstance(gen_resp, Exception):
            raise HTTPException(status_code=500, detail=f"/generate-files-api failed: {str(gen_resp)}")
        if isinstance(code_resp, Exception):
            raise HTTPException(status_code=500, detail=f"/Generator failed: {str(code_resp)}")

        if gen_resp.status_code != 200:
            raise HTTPException(status_code=gen_resp.status_code, detail=f"/generate-files-api: {gen_resp.text}")
        if code_resp.status_code != 200:
            raise HTTPException(status_code=code_resp.status_code, detail=f"/Generator: {code_resp.text}")

        file_response = gen_resp.json()
        code_response = code_resp.json()

        print("\n✅ Pipeline completed successfully!\n")

        return {
            "status": "success",
            "topic": topic,
            "script": parsed_json,
            "file_generation": file_response,
            "manim_code_generation": code_response
        }

    except HTTPException as e:
        print(f"⚠️ HTTPException in /search: {e.detail}")
        raise e

    except Exception as e:
        print(f"❌ Unexpected Error in /search: {str(e)}")
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

@app.post("/Generator")
async def generate_code_endpoint(input_data: List[Dict]):
    """
    Accepts a list of script objects (output from /search),
    generates Manim Python code for each script sequence,
    and automatically writes them to disk using /write-scripts.
    """
    try:
        print("\n🧠 Starting Manim Code Generation...\n")

        generator = CodeGenerator(API_KEY)
        result = generator.generate_code(input_data)

        print("\n🎬 Generated Manim Code Results:\n")
        for item in result:
            for k, v in item.items():
                print(f"\n{k}:\n{v}\n{'-'*80}")

        # Step 2 — Send the generated scripts to /write-scripts
        write_api = "http://127.0.0.1:8000/write-scripts"
        headers = {"Content-Type": "application/json"}

        print("\n📝 Sending generated scripts to /write-scripts ...\n")

        async with httpx.AsyncClient(timeout=120) as client:
            write_response = await client.post(write_api, headers=headers, json=result)

        if write_response.status_code != 200:
            print(f"⚠️ /write-scripts failed: {write_response.status_code}")
            raise HTTPException(
                status_code=write_response.status_code,
                detail=f"/write-scripts failed: {write_response.text}",
            )

        print("✅ Successfully wrote all scripts to disk.\n")

        # Step 3 — Combine all results and return
        write_result = write_response.json()

        return {
            "status": "success",
            "generated_scripts": result,
            "write_result": write_result,
        }

    except HTTPException as e:
        print(f"⚠️ HTTPException in /Generator: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Error in /Generator endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))



    
    

@app.post("/write-scripts")
async def write_scripts(data: ScriptData):
    """
    Writes each script file into its respective folder,
    then automatically triggers /generate-videos-api to render the final video.
    """
    try:
        latest_folder = get_latest_input_folder(BASE_INPUT_ROOT)
        print(f"\n📁 Writing scripts to latest input folder: {latest_folder}\n")

        # Step 1️⃣ — Write all scripts to files
        for item in data.root:
            for folder_name, content in item.items():
                folder = latest_folder / folder_name
                folder.mkdir(parents=True, exist_ok=True)

                file_path = folder / f"{folder_name}.py"
                decoded_script = bytes(content, "utf-8").decode("unicode_escape")
                file_path.write_text(decoded_script, encoding="utf-8")

                pipeline_logger.info(f"✅ Script written: {file_path}")
                print(f"✅ Saved: {file_path}")

        # Step 2️⃣ — Automatically call /generate-videos-api
        generate_api = "http://127.0.0.1:8000/generate-videos-api"
        headers = {"Content-Type": "application/json"}
        payload = {"path": str(latest_folder)}

        print(f"\n🎬 Triggering video generation for: {latest_folder}\n")

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(generate_api, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"⚠️ /generate-videos-api failed: {response.status_code}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"/generate-videos-api failed: {response.text}",
            )

        video_result = response.json()
        print(f"✅ Video generated successfully: {video_result.get('final_video', 'unknown')}")

        # Step 3️⃣ — Return combined result
        return {
            "status": "success",
            "message": "Scripts written successfully and video generated.",
            "target_directory": str(latest_folder),
            "video_result": video_result,
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error writing scripts or generating video")
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

        pipeline_logger.info(f"🎬 Final video saved: {output_path}",)
        return {
            "status": "success",
            "final_video": output_path,
            "processed_from": str(input_path),
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error during video generation")
        raise HTTPException(status_code=500, detail=str(e))
