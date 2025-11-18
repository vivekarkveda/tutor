from fastapi import APIRouter, HTTPException
from pydantic import RootModel, BaseModel
from typing import List, Dict
from pathlib import Path
from video_pipeline.utils import async_post, latest_input_folder
from logger import pipeline_logger, validation_logger
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception
import traceback
from config import Settings
from Artifacts.artifacts import run_script_data_process


router = APIRouter(prefix="", tags=["Write Scripts"])
BASE_INPUT_ROOT = Path(Settings.TEMP_GENERATED_FOLDER)


class GenerateFilesRequest(BaseModel):
    result_data: List[Dict]
    unique_id: str


class ScriptData(RootModel[List[Dict[str, str]]]): 
    pass


@router.post("/write-scripts")
async def write_scripts(data: GenerateFilesRequest):
    """
    Writes scripts from JSON payload to structured folders,
    then triggers video generation. Handles all errors gracefully
    with proper DB logging (transaction + exception tables).
    """
    unique_id = data.unique_id
    folder = None

    try:
        # -------------------------------
        # 1️⃣  Create Target Folder
        # -------------------------------
        try:
            folder = latest_input_folder(BASE_INPUT_ROOT, unique_id)
            pipeline_logger.info(f"📂 Located folder for unique_id {unique_id}: {folder}")
        except Exception as e:
            err_msg = f"❌ Failed to locate input folder for {unique_id}: {e}"
            pipeline_logger.error(err_msg)
            exception(
                unique_id,
                script_written="Script writing failed",
                exception_message=str(e),
                trace=traceback.format_exc()
            )
            raise HTTPException(status_code=500, detail=err_msg)

        # -------------------------------
        # 2️⃣  Write Script Files
        # -------------------------------
        try:
            for item in data.result_data:
                for name, content in item.items():
                    target = folder / name
                    target.mkdir(parents=True, exist_ok=True)
                    file_path = target / f"{name}.py"

                    try:
                        file_path.write_text(
                            content.encode("utf-8").decode("unicode_escape"),
                            encoding="utf-8"
                        )
                        pipeline_logger.info(f"✅ Script written: {file_path}")
                    except Exception as fe:
                        validation_logger.error(f"❌ File write failed: {file_path} | {fe}")
                        exception(
                            unique_id,
                            script_written="Script file write failed",
                            exception_message=str(fe),
                            trace=traceback.format_exc()
                        )
                        continue  # continue to next file safely

            transaction(unique_id, script_written="Script written successfully")
            pipeline_logger.info("✅ All scripts written successfully")

        except Exception as e:
            err_msg = f"❌ Error while writing scripts: {e}"
            pipeline_logger.error(err_msg)
            exception(
                unique_id,
                script_written="Script writing failed",
                exception_message=str(e),
                trace=traceback.format_exc()
            )
            raise HTTPException(status_code=500, detail=err_msg)

        # -------------------------------
        # 3️⃣  Trigger Video Generation
        # -------------------------------

        run_script_data_process(unique_id)
        try:
            video_url = "http://127.0.0.1:8000/generate-videos-api"
            pipeline_logger.info(f"🎬 Triggering video generation for {unique_id}")

            video_result = await async_post(
                video_url,
                {"path": str(folder), "unique_id": data.unique_id},
                timeout=300
            )

            transaction(unique_id, video_status="Video generation successful")
            pipeline_logger.info(f"🎉 Video generated successfully for {unique_id}")

            return {
                "status": "success",
                "message": "Scripts written & video generated.",
                "target_directory": str(folder),
                "video_result": video_result,
            }

        except Exception as e:
            err_msg = f"❌ Video generation failed for {unique_id}: {e}"
            pipeline_logger.error(err_msg)
            raise HTTPException(status_code=500, detail=err_msg)

    # -------------------------------
    # 4️⃣  Global Exception Handling
    # -------------------------------
    except Exception as e:
        pipeline_logger.exception("❌ Unhandled error in write_scripts endpoint")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pipeline_logger.info(f"🔚 write_scripts completed for {unique_id}")
