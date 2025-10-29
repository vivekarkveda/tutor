from fastapi import APIRouter, HTTPException, Query
from video_pipeline.utils import async_post
from LLM_Processor.script_factory import ScriptGeneratorFactory
from logger import pipeline_logger
import asyncio, json

router = APIRouter(prefix="", tags=["Script Generation"])

API_KEY = "ItjCVeX2H4je76T4Az0yQGnjISqZhD3IrKWj6ebq"

@router.post("/search")
async def search(topic: str = Query(..., description="Topic for script generation")):
    """Generate storytelling JSON, trigger file & code generation."""
    try:
        pipeline_logger.info(f"🧠 Generating script for topic: {topic}")
        generator = ScriptGeneratorFactory.get_generator("cohere", api_key=API_KEY)
        raw_script = generator.generate_script(topic)

        cleaned = (
            raw_script.strip()
            .removeprefix("```json").removeprefix("```JSON")
            .removeprefix("```").removesuffix("```").strip()
        )

        parsed_json = json.loads(cleaned)

        gen_url = "http://127.0.0.1:8000/generate-files-api"
        code_url = "http://127.0.0.1:8000/Generator"

        gen_task = async_post(gen_url, parsed_json)
        code_task = async_post(code_url, parsed_json)
        file_resp, code_resp = await asyncio.gather(gen_task, code_task)

        return {
            "status": "success",
            "topic": topic,
            "script": parsed_json,
            "file_generation": file_resp,
            "manim_code_generation": code_resp,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
