from fastapi import APIRouter, HTTPException
from typing import List, Dict
from video_pipeline.utils import save_temp_json
from logger import pipeline_logger
from config import Settings
from main import prepare_files

router = APIRouter(prefix="", tags=["File Generation"])

@router.post("/generate-files-api")
async def generate_files_endpoint(input_data: List[Dict]):
    """Accepts JSON list, saves to temp, generates base .py/.txt files."""
    try:
        json_path = save_temp_json(input_data)
        old_path = Settings.JSON_FILE_PATH
        Settings.JSON_FILE_PATH = str(json_path)

        try:
            generated = prepare_files(Settings.RUN_FROM, True, Settings.FILE_TYPES)
        finally:
            Settings.JSON_FILE_PATH = old_path

        return {
            "status": "success",
            "json_saved_in": str(json_path.parent),
            "generated_files": generated
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error generating files")
        raise HTTPException(status_code=500, detail=str(e))
