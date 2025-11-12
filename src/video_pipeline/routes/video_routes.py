from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from video_pipeline.utils import latest_input_folder
from config import Settings
from main import process_pipeline
from logger import pipeline_logger
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception
import traceback

router = APIRouter(prefix="", tags=["Video Generation"])
BASE_INPUT_ROOT = Path(r"C:\Vivek_Main\Manim_project\inputbox")

class VideoRequest(BaseModel):
    path: Optional[str] = None
    unique_id: str


@router.post("/generate-videos-api")
async def generate_videos_endpoint(request: VideoRequest):
    unique_id = request.unique_id
    """Generate final video from latest or specified folder."""
    try:
        input_path = Path(request.path) if request.path else latest_input_folder(BASE_INPUT_ROOT , request.unique_id)
        print("request.unique_id",request.unique_id)
        if not input_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {input_path}")

        py_files = [f.as_posix() for f in input_path.rglob("*.py")]
        txt_files = [f.as_posix() for f in input_path.rglob("*.txt")]
        if not py_files or not txt_files:
            raise HTTPException(status_code=400, detail=f"No .py/.txt files in {input_path}")

        output_path = await process_pipeline(
            [{"py_files": py_files, "txt_files": txt_files}, str(input_path)],
            Settings.VIDEO_PROCESSOR,
            Settings.AUDIO_PROCESSOR,
            Settings.RUN_FROM,
            request.unique_id
        )

        transaction(unique_id, video_status="success")

        return {
            "status": "success",
            "final_video": output_path,
            "processed_from": str(input_path)
        }

    except Exception as e:
        transaction(unique_id, video_status="fail")
        pipeline_logger.exception("❌ Video generation error")
        raise HTTPException(status_code=500, detail=str(e))
