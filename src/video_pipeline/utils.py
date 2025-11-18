import json
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
import httpx
from logger import pipeline_logger
from config import Settings
import uuid

async def async_post(url: str, payload: dict, timeout: int = 180):
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            pipeline_logger.error(f"❌ HTTP {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

def latest_input_folder(base_dir: Path, unique_id: str) -> Path:
    pattern = f"{unique_id}"
    folders = [d for d in base_dir.iterdir() if d.is_dir() and d.name.endswith(pattern)]
    if not folders:
        raise FileNotFoundError(f"No {pattern} found in {base_dir}")
    return max(folders, key=lambda d: d.stat().st_mtime)


def save_temp_json(data):
    print("data", data)
    unique_id = data.unique_id  # ✅ Works with Pydantic model
    print("unique_id test", unique_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a folder named with UUID
    temp_dir = Path(Settings.TEMP_GENERATED_FOLDER) / f"{timestamp}_{unique_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save the JSON file with UUID as filename
    json_path = temp_dir / f"{unique_id}.json"
    json_path.write_text(json.dumps(data.input_data, indent=2, ensure_ascii=False), encoding="utf-8")

    pipeline_logger.info(f"📄 JSON saved at {json_path}")
    print(json_path)
    return json_path

