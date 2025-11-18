from cohere.finetuning.finetuning.types import settings
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from video_pipeline.utils import async_post
from LLM_Processor.script_factory import ScriptGeneratorFactory
from logger import pipeline_logger
import asyncio, json
from config import Settings
from typing import Optional
import uuid
from Transaction.transaction_handler import transaction
from Artifacts.artifacts import run_script_data_process

router = APIRouter(prefix="", tags=["Script Generation"])

API_KEY = "dZfHrqzrU2lw32MX2RPRiG8ARSKqavpiqpLsU2b0"


# 🧩 Request Model (no mock flag)
class SearchRequest(BaseModel):
    topic: str = Field(..., description="The topic to generate a storytelling script for")
    class_: str = Field(..., alias="class", description="The educational class or grade level")
    language: Optional[str] = Field("English", description="Language for the script (default: English)")

    class Config:
        allow_population_by_field_name = True


@router.post("/search")
async def search(request: SearchRequest):
    """
    Generate storytelling JSON for a given topic and class using Cohere,
    then trigger internal APIs to generate files and Manim code.
    """
    try:
        topic = request.topic
        class_level = request.class_
        language = request.language
        unique_id = str(uuid.uuid4())
        pipeline_logger.info(f"Transaction ID {unique_id}")
        

        pipeline_logger.info(f"🧠 Generating script for topic='{topic}', class='{class_level}'")
        

        # === Step 1️⃣: Initialize Cohere generator
        generator = ScriptGeneratorFactory.get_generator("cohere", api_key=API_KEY )

        # === Step 2️⃣: Generate the storytelling JSON
        full_prompt = f"{topic} for class {class_level} in {language} language"

        raw_script = generator.generate_script(full_prompt,unique_id )

        # === Step 3️⃣: Clean up and parse JSON safely
        cleaned_script = (
            raw_script.strip()
            .removeprefix("```json").removeprefix("```JSON")
            .removeprefix("```").removesuffix("```").strip()
        )

        transaction(unique_id, topic=topic, meta_prompt=full_prompt, cleaned_script=cleaned_script)

        try:
            input_data = []
            parsed_json = {
                        "input_data": json.loads(cleaned_script),
                        "unique_id": unique_id
                    }
        except json.JSONDecodeError as je:
            pipeline_logger.error(f"⚠️ Invalid JSON output from Cohere: {je}")
            raise HTTPException(status_code=400, detail="Generated script is not valid JSON")
        
        run_script_data_process(unique_id)
        

        # === Step 4️⃣: Send data to internal APIs
        gen_url = f"{Settings.IP_ADDRESS}/generate-files-api"
        code_url = f"{Settings.IP_ADDRESS}/Generator"

        pipeline_logger.info("🚀 Sending generated script to /generate-files-api and /Generator ...")

        gen_task = async_post(gen_url, parsed_json)
        code_task = async_post(code_url, parsed_json)
        file_resp, code_resp = await asyncio.gather(gen_task, code_task)

        # === Step 5️⃣: Final response
        pipeline_logger.info(f"✅ Script pipeline completed successfully for topic='{topic}'")
        

        result = {
            "status": "success",
            "topic": topic,
            "class": class_level,
            "script": parsed_json,
            "file_generation": file_resp,
            "manim_code_generation": code_resp,
        }




        return result

    except HTTPException:
        raise
    except Exception as e:
        pipeline_logger.info(f"❌ Script pipeline completed unsuccessfully for topic='{topic}'")
        pipeline_logger.exception("❌ Unexpected error in /search endpoint",extra={"part_name": "SearchRoutes"})
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")
