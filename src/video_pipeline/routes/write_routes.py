from fastapi import APIRouter, HTTPException
from pydantic import RootModel
from typing import List, Dict
from pathlib import Path
from video_pipeline.utils import async_post, latest_input_folder
from logger import pipeline_logger

router = APIRouter(prefix="", tags=["Write Scripts"])
BASE_INPUT_ROOT = Path(r"C:\Vivek_Main\Manim_project\inputbox")

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

        # Trigger video generation
        video_url = "http://127.0.0.1:8000/generate-videos-api"
        video_result = await async_post(video_url, {"path": str(folder)}, timeout=300)

        return {
            "status": "success",
            "message": "Scripts written & video generated.",
            "target_directory": str(folder),
            "video_result": video_result,
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error writing scripts")
        raise HTTPException(status_code=500, detail=str(e))
