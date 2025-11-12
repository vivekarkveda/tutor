from fastapi import APIRouter, HTTPException
from typing import List, Dict
from video_pipeline.utils import save_temp_json
from logger import pipeline_logger
from config import Settings
from main import prepare_files
from datetime import datetime
import uuid, traceback
from pathlib import Path

router = APIRouter(prefix="", tags=["File Generation"])

@router.post("/generate-files-api")
async def generate_files_endpoint(input_data: List[Dict]):
    """
    Accepts JSON list, creates a timestamped transaction folder,
    saves JSON there, and triggers base file generation.
    Includes detailed debug logs for traceability.
    """
    try:
        pipeline_logger.info("🟢 [generate-files-api] New request received")
        pipeline_logger.debug(f"📦 Input data sample: {str(input_data)[:500]}")  # log first 500 chars

        # === Step 1️⃣: Create timestamped folder ===
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transaction_id = uuid.uuid4().hex[:8]
        root_folder = Settings.VIDEO_DATA_PATH / f"{timestamp}_{transaction_id}"
        

        try:
            root_folder.mkdir(parents=True, exist_ok=True)
            pipeline_logger.info(f"📁 Created folder: {root_folder}")

            # ✅ Save transaction folder path globally for downstream modules
            Settings.set_transaction_folder(root_folder)

            persist_path = Settings.TEMP_GENERATED_FOLDER / "current_transaction.txt"
            persist_path.write_text(str(root_folder), encoding="utf-8")

            pipeline_logger.debug(f"🌍 Set Settings.TRANSACTION_FOLDER → {Settings.TRANSACTION_FOLDER}")

        except Exception as e:
            pipeline_logger.error(f"❌ Failed to create folder: {root_folder}")
            pipeline_logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to create transaction folder: {e}")

        # === Step 2️⃣: Save input JSON ===
        json_path = root_folder / "input_data.json"
        try:
            pipeline_logger.debug(f"💾 Attempting to save JSON to {json_path}")
            saved_path = save_temp_json(input_data, json_path)
            pipeline_logger.info(f"✅ JSON saved successfully at {saved_path}")
        except Exception as e:
            pipeline_logger.error(f"❌ Failed to save JSON at {json_path}: {e}")
            pipeline_logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to save JSON file: {e}")

        # === Step 3️⃣: Prepare files ===
        old_path = Settings.JSON_FILE_PATH
        Settings.JSON_FILE_PATH = str(json_path)
        pipeline_logger.debug(f"⚙️ Updated Settings.JSON_FILE_PATH → {Settings.JSON_FILE_PATH}")

        try:
            pipeline_logger.info("🧩 Starting file preparation process via prepare_files()")
            generated = prepare_files(Settings.RUN_FROM, True, Settings.FILE_TYPES)
            pipeline_logger.info(f"✅ File preparation completed. Output: {generated}")
        except Exception as e:
            pipeline_logger.error(f"❌ Error during prepare_files(): {e}")
            pipeline_logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"prepare_files failed: {e}")
        finally:
            Settings.JSON_FILE_PATH = old_path
            pipeline_logger.debug("🔁 Restored original Settings.JSON_FILE_PATH")

            # 🚫 Do NOT clear TRANSACTION_FOLDER here — it's needed for Drive upload
            pipeline_logger.debug(f"🔒 Keeping TRANSACTION_FOLDER active for upload: {Settings.TRANSACTION_FOLDER}")



        # === Step 4️⃣: Return Success ===
        pipeline_logger.info(
            f"🎯 Transaction {transaction_id} completed successfully. Folder: {root_folder}"
        )

        return {
            "status": "success",
            "transaction_id": transaction_id,
            "timestamp": timestamp,
            "save_dir": str(root_folder),
            "json_file": str(json_path),
            "generated_files": generated,
            "transaction_folder": str(root_folder)
        }

    except HTTPException:
        raise  # re-raise cleanly for FastAPI
    except Exception as e:
        pipeline_logger.error("💥 Unexpected top-level error in /generate-files-api")
        pipeline_logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
