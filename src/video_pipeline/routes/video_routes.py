from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from video_pipeline.utils import latest_input_folder
from config import Settings
from main import process_pipeline
from logger import pipeline_logger

router = APIRouter(prefix="", tags=["Video Generation"])
BASE_INPUT_PATH = Settings.BASE_INPUT_PATH


class VideoRequest(BaseModel):
    path: Optional[str] = None


@router.post("/generate-videos-api")
async def generate_videos_endpoint(request: VideoRequest):
    """Generate final video from latest or specified folder."""
    try:
        pipeline_logger.info("🚀 Received video generation request.")

        # --- Resolve input path ---
        if request.path:
            input_path = Path(request.path)
            pipeline_logger.info(f"📂 Using provided input path: {input_path}")
        else:
            input_path = latest_input_folder(BASE_INPUT_PATH)
            pipeline_logger.info(f"📂 Using latest input folder: {input_path}")

        if not input_path.exists():
            pipeline_logger.error(f"❌ Input path not found: {input_path}")
            raise HTTPException(status_code=404, detail=f"Path not found: {input_path}")

        # --- Collect .py and .txt files ---
        py_files = [f.as_posix() for f in input_path.rglob("*.py")]
        txt_files = [f.as_posix() for f in input_path.rglob("*.txt")]

        pipeline_logger.info(f"🧩 Found {len(py_files)} .py files and {len(txt_files)} .txt files under {input_path}")

        if not py_files or not txt_files:
            pipeline_logger.warning(f"⚠️ Missing .py or .txt files in {input_path}")
            raise HTTPException(status_code=400, detail=f"No .py/.txt files in {input_path}")

        # --- Run the pipeline ---
        pipeline_logger.info("🎬 Starting video + audio processing pipeline...")

        root_folder = input_path.parent if input_path.name == "script_sequences" else input_path

        output_path = await process_pipeline(
            [{"py_files": py_files, "txt_files": txt_files}, str(root_folder)],
            Settings.VIDEO_PROCESSOR,
            Settings.AUDIO_PROCESSOR,
            Settings.RUN_FROM,
        )

        if output_path:
            pipeline_logger.info(f"✅ Pipeline completed successfully. Final video saved at: {output_path}")
        else:
            pipeline_logger.warning("⚠️ Pipeline finished without generating a final video output (merge may have failed).")

        # --- Response ---
        return {
            "status": "success",
            "final_video": output_path,
            "processed_from": str(input_path),
        }

    except HTTPException as http_err:
        pipeline_logger.warning(f"⚠️ HTTP error during video generation: {http_err.detail}")
        raise http_err

    except Exception as e:
        pipeline_logger.exception("💥 Unexpected error in video generation endpoint.")
        raise HTTPException(status_code=500, detail=str(e))
