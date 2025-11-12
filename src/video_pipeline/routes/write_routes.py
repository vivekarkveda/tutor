from fastapi import APIRouter, HTTPException
from pydantic import RootModel
from typing import List, Dict
from pathlib import Path
from video_pipeline.utils import async_post, latest_input_folder
from logger import pipeline_logger
from config import Settings
import traceback
import asyncio


router = APIRouter(prefix="", tags=["Write Scripts"])
BASE_INPUT_PATH = Settings.BASE_INPUT_PATH

class ScriptData(RootModel[List[Dict[str, str]]]): 
    pass

@router.post("/write-scripts")
async def write_scripts(data: ScriptData):
    """
    Writes Manim .py scripts to the appropriate folder.
    If TRANSACTION_FOLDER is active, uses that.
    Otherwise, falls back to latest input folder (old flow).
    """
    try:
        transaction_folder = getattr(Settings, "TRANSACTION_FOLDER", None)
        pipeline_logger.info(f"🔍 TRANSACTION_FOLDER currently: {transaction_folder}")

        if transaction_folder and Path(transaction_folder).exists():
            folder = Path(transaction_folder) / "script_sequences"
            pipeline_logger.info(f"🟢 Using TRANSACTION_FOLDER for writing scripts: {folder}")
        else:
            folder_file = Settings.TEMP_GENERATED_FOLDER / "current_transaction.txt"
            if folder_file.exists():
                saved_path = Path(folder_file.read_text().strip())
                folder = saved_path / "script_sequences"
                pipeline_logger.info(f"🟢 Using persisted transaction folder: {folder}")
            else:
                folder = latest_input_folder(BASE_INPUT_PATH)
                pipeline_logger.warning(f"⚠️ No transaction folder found, using latest folder: {folder}")


        # ✍️ Write each script file
        for item in data.root:
            for name, content in item.items():
                target = folder / name
                target.mkdir(parents=True, exist_ok=True)
                file_path = target / f"{name}.py"

                try:
                    decoded_content = content.encode("utf-8").decode("unicode_escape")
                    file_path.write_text(decoded_content, encoding="utf-8")
                    pipeline_logger.info(f"✅ Manim script written: {file_path}")
                except Exception as write_err:
                    pipeline_logger.error(f"❌ Failed to write script {file_path}: {write_err}")
                    pipeline_logger.debug(traceback.format_exc())
                    raise

        # 🎬 Trigger video generation
        video_url = "http://127.0.0.1:8000/generate-videos-api"
        pipeline_logger.info(f"🎥 Triggering video generation for folder: {folder}")

        await asyncio.sleep(1)
        video_result = await async_post(video_url, {"path": str(folder)}, timeout=300)

        return {
            "status": "success",
            "message": "Scripts written & video generated.",
            "target_directory": str(folder),
            "video_result": video_result,
        }

    except Exception as e:
        pipeline_logger.error("💥 Error in /write-scripts endpoint")
        pipeline_logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
