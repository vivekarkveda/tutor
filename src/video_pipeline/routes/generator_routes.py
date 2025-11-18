from fastapi import APIRouter, HTTPException
from typing import List, Dict
from LLM_Processor.codeGen_factory import CodeGenerator
from video_pipeline.utils import async_post
from logger import pipeline_logger
from config import Settings
from pydantic import BaseModel


router = APIRouter(prefix="", tags=["Code Generation"])
API_KEY = Settings.API_KEY

class GenerateFilesRequest(BaseModel):
    input_data: List[Dict]
    unique_id: str

@router.post("/Generator")
async def generate_code_endpoint(request: GenerateFilesRequest):
    """Generate Manim Python code & forward to /write-scripts."""
    try:
        generator = CodeGenerator(API_KEY)
        result = generator.generate_code(request.input_data, request.unique_id)
        pipeline_logger.info("🎬 Generated Manim Code Successfully")
        write_url = f"{Settings.IP_ADDRESS }/write-scripts"
        payload = {
            "result_data": result,
            "unique_id": request.unique_id
        }
        write_result = await async_post(write_url, payload)


        return {
            "status": "success",
            "generated_scripts": result,
            "write_result": write_result
        }

    except Exception as e:
        pipeline_logger.exception("❌ Error generating code")
        raise HTTPException(status_code=500, detail=str(e))
