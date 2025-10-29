import json
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
import httpx
from logger import pipeline_logger
from config import Settings

async def async_post(url: str, payload: dict, timeout: int = 180):
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            pipeline_logger.error(f"❌ HTTP {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

def latest_input_folder(base_dir: Path) -> Path:
    folders = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("input_data_")]
    if not folders:
        raise FileNotFoundError(f"No input_data_* found in {base_dir}")
    return max(folders, key=lambda d: d.stat().st_mtime)

def save_temp_json(data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(Settings.TEMP_GENERATED_FOLDER) / f"batch_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    json_path = temp_dir / "input_data.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    pipeline_logger.info(f"📄 JSON saved at {json_path}")
    return json_path
