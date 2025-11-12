from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..drive_utils import upload_folder_to_drive
from config import Settings
from logger import pipeline_logger

router = APIRouter()

class DriveFolderUploadRequest(BaseModel):
    folder_path: str  # Local folder to upload


@router.post("/upload-folder-to-drive")
async def upload_folder_to_drive_route(request: DriveFolderUploadRequest):
    """Upload an entire local folder (and its contents) to Google Drive."""
    try:

        result = upload_folder_to_drive(
            folder_path=request.folder_path,
            drive_credentials=Settings.DRIVE_CREDENTIALS_PATH,
            token_path=Settings.TOKEN_PATH,
            auth_mode=Settings.DRIVE_AUTH_MODE,
            # parent_folder_id=Settings.DRIVE_FOLDER_ID
        )

        pipeline_logger.info(f"🚀 Folder uploaded successfully: {result}")
        return result

    except Exception as e:
        pipeline_logger.exception("❌ Google Drive folder upload API failed.")
        raise HTTPException(status_code=500, detail=str(e))
