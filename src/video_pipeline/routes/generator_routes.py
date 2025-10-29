from fastapi import APIRouter, HTTPException
from typing import List, Dict
from LLM_Processor.codeGen_factory import CodeGenerator
from video_pipeline.utils import async_post
from logger import pipeline_logger

router = APIRouter(prefix="", tags=["Code Generation"])
API_KEY = "ItjCVeX2H4je76T4Az0yQGnjISqZhD3IrKWj6ebq"

@router.post("/Generator")
async def generate_code_endpoint(input_data: List[Dict]):
    """Generate Manim Python code & forward to /write-scripts."""
    try:
        generator = CodeGenerator(API_KEY)
        result = generator.generate_code(input_data)
        pipeline_logger.info("🎬 Generated Manim Code Successfully")

        write_url = "http://127.0.0.1:8000/write-scripts"
        write_result = await async_post(write_url, result, timeout=120)

        return {
            "status": "success",
            "generated_scripts": result,
            "write_result": write_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
