from fastapi import APIRouter, HTTPException
from typing import List, Dict
from video_pipeline.utils import save_temp_json
from logger import pipeline_logger
from config import Settings
from main import prepare_files
from pydantic import BaseModel
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception
import traceback
from Artifacts.artifacts import run_script_data_process

router = APIRouter(prefix="", tags=["File Generation"])


class GenerateFilesRequest(BaseModel):
    input_data: List[Dict]
    unique_id: str

@router.post("/generate-files-api")
async def generate_files_endpoint(request: GenerateFilesRequest):
    
    """Accepts JSON list, saves to temp, generates base .py/.txt files."""
    try:
        json_path = save_temp_json(request)
        unique_id = request.unique_id
        print("json_path",json_path)
        old_path = Settings.JSON_FILE_PATH
        Settings.JSON_FILE_PATH = str(json_path)

        try:
            generated = prepare_files(Settings.RUN_FROM, True, Settings.FILE_TYPES, request.unique_id)
        finally:
            Settings.JSON_FILE_PATH = old_path


        return {
            "status": "success",
            "json_saved_in": str(json_path.parent),
            "generated_files": generated
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error generating files",extra={"part_name": "FileRoutes"})
        raise HTTPException(status_code=500, detail=str(e))
