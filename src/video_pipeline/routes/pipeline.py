from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, RootModel
from typing import List, Dict, Optional
from pathlib import Path
import asyncio, json
from logger import pipeline_logger
from config import Settings
from main import prepare_files, process_pipeline
from LLM_Processor.script_factory import ScriptGeneratorFactory
from LLM_Processor.codeGen_factory import CodeGenerator
from video_pipeline.utils import async_post, latest_input_folder, save_temp_json


router = APIRouter()
API_KEY = "ItjCVeX2H4je76T4Az0yQGnjISqZhD3IrKWj6ebq"
BASE_INPUT_ROOT = Path(r"C:\Vivek_Main\Manim_project\inputbox")

# ================================================================
# 1️⃣ /search — Generate Script + Trigger Rest
# ================================================================
@router.post("/search")
async def search(topic: str = Query(..., description="Topic for script generation")):
    try:
        pipeline_logger.info(f"🧠 Generating script for topic: {topic}")
        generator = ScriptGeneratorFactory.get_generator("cohere", api_key=API_KEY)
        script_raw = generator.generate_script(topic)

        cleaned = (
            script_raw.strip()
            .removeprefix("```json").removeprefix("```JSON")
            .removeprefix("```").removesuffix("```").strip()
        )

        parsed_json = json.loads(cleaned)
        gen_url, code_url = "http://127.0.0.1:8000/generate-files-api", "http://127.0.0.1:8000/Generator"

        gen_task = async_post(gen_url, parsed_json)
        code_task = async_post(code_url, parsed_json)
        file_resp, code_resp = await asyncio.gather(gen_task, code_task)

        return {
            "status": "success",
            "topic": topic,
            "script": parsed_json,
            "file_generation": file_resp,
            "manim_code_generation": code_resp,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# 2️⃣ /generate-files-api — Save JSON & Generate .py/.txt
# ================================================================
@router.post("/generate-files-api")
async def generate_files_endpoint(input_data: List[Dict]):
    try:
        json_path = save_temp_json(input_data)
        old_path = Settings.JSON_FILE_PATH
        Settings.JSON_FILE_PATH = str(json_path)

        try:
            generated = prepare_files(Settings.RUN_FROM, True, Settings.FILE_TYPES)
        finally:
            Settings.JSON_FILE_PATH = old_path

        return {"status": "success", "json_saved_in": str(json_path.parent), "generated_files": generated}
    except Exception as e:
        pipeline_logger.exception("❌ Error generating files")
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# 3️⃣ /Generator — Generate Manim Code & Write to Disk
# ================================================================
@router.post("/Generator")
async def generate_code_endpoint(input_data: List[Dict]):
    try:
        generator = CodeGenerator(API_KEY)
        result = generator.generate_code(input_data)
        pipeline_logger.info("🎬 Generated Manim Code Successfully")

        write_url = "http://127.0.0.1:8000/write-scripts"
        write_result = await async_post(write_url, result, timeout=120)

        return {"status": "success", "generated_scripts": result, "write_result": write_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# 4️⃣ /write-scripts — Save scripts & trigger video generation
# ================================================================
class ScriptData(RootModel[List[Dict[str, str]]]): pass

@router.post("/write-scripts")
async def write_scripts(data: ScriptData):
    try:
        folder = latest_input_folder(BASE_INPUT_ROOT)
        for item in data.root:
            for name, content in item.items():
                target = folder / name
                target.mkdir(parents=True, exist_ok=True)
                file_path = target / f"{name}.py"
                file_path.write_text(content.encode("utf-8").decode("unicode_escape"), encoding="utf-8")
                pipeline_logger.info(f"✅ Script written: {file_path}")

        video_url = "http://127.0.0.1:8000/generate-videos-api"
        video_result = await async_post(video_url, {"path": str(folder)}, timeout=300)

        return {"status": "success", "message": "Scripts written & video generated.", "target_directory": str(folder), "video_result": video_result}

    except Exception as e:
        pipeline_logger.exception("❌ Error writing scripts")
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# 5️⃣ /generate-videos-api — Render Final Video
# ================================================================
class VideoRequest(BaseModel):
    path: Optional[str] = None

@router.post("/generate-videos-api")
async def generate_videos_endpoint(request: VideoRequest):
    try:
        input_path = Path(request.path) if request.path else latest_input_folder(BASE_INPUT_ROOT)
        if not input_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {input_path}")

        py_files = [f.as_posix() for f in input_path.rglob("*.py")]
        txt_files = [f.as_posix() for f in input_path.rglob("*.txt")]
        if not py_files or not txt_files:
            raise HTTPException(status_code=400, detail=f"No .py/.txt in {input_path}")

        output_path = await process_pipeline(
            [{"py_files": py_files, "txt_files": txt_files}, str(input_path)],
            Settings.VIDEO_PROCESSOR,
            Settings.AUDIO_PROCESSOR,
            Settings.RUN_FROM,
        )

        return {"status": "success", "final_video": output_path, "processed_from": str(input_path)}
    except Exception as e:
        pipeline_logger.exception("❌ Video generation error")
        raise HTTPException(status_code=500, detail=str(e))
