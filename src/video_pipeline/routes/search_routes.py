from fastapi import APIRouter, HTTPException, Query
from video_pipeline.utils import async_post
from LLM_Processor.script_factory import ScriptGeneratorFactory
from logger import pipeline_logger
import asyncio, json
from config import Settings

router = APIRouter(prefix="", tags=["Script Generation"])

API_KEY = Settings.API_KEY

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

        gen_url = Settings.IP_ADDRESS +"/generate-files-api"
        code_url = Settings.IP_ADDRESS +"/Generator"

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
