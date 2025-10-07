# saver_factory.py
import os
import psycopg2
from pathlib import Path
from logger import pipeline_logger, validation_logger


class BaseSaver:
    """Abstract saver interface."""
    def save(self, video_bytes: bytes, filename: str, db_credentials=None):
        raise NotImplementedError("Subclasses must implement save()")


# --- Local Saver ---
class LocalSaver(BaseSaver):
    BASE_OUTPUT_DIR = Path(__file__).resolve().parent / "output"

    def save(self, video_bytes: bytes, filename: str, db_credentials=None):
        if not filename.lower().endswith(".mp4"):
            filename = f"{filename}.mp4"

        os.makedirs(self.BASE_OUTPUT_DIR, exist_ok=True)
        output_path = self.BASE_OUTPUT_DIR / filename

        with open(output_path, "wb") as f:
            f.write(video_bytes)

        pipeline_logger.info(f"✅ Final video saved locally at: {output_path}")
        return str(output_path)


# --- Postgres Saver ---
class PostgresSaver(BaseSaver):
    def save(self, video_bytes: bytes, filename: str, db_credentials=None):
        if not filename.lower().endswith(".mp4"):
            filename = f"{filename}.mp4"

        if not db_credentials:
            raise ValueError("❌ No DB credentials provided for Postgres saving")

        conn = psycopg2.connect(
            host=db_credentials["host"],
            port=db_credentials["port"],
            user=db_credentials["user"],
            password=db_credentials["password"],
            dbname=db_credentials["dbname"],
        )
        cursor = conn.cursor()

        table = db_credentials.get("table", "videos")

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                video BYTEA,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute(
            f"INSERT INTO {table} (filename, video) VALUES (%s, %s)",
            (filename, psycopg2.Binary(video_bytes))
        )
        conn.commit()

        cursor.close()
        conn.close()

        pipeline_logger.info(f"✅ Final video saved in PostgreSQL table '{table}' as {filename}")
        return f"postgres://{db_credentials['host']}:{db_credentials['port']}/{db_credentials['dbname']}/{table}/{filename}"


# --- Factory Handler ---
class SaverFactory:
    """Factory that decides with if/else which saver to use."""

    @staticmethod
    def save_final_video(video_bytes: bytes, filename: str, save_to: str, db_credentials=None):
        if save_to == "local":
            saver = LocalSaver()
        elif save_to == "postgres":
            saver = PostgresSaver()
        else:
            raise ValueError(f"❌ Unsupported save_to type: {save_to}")

        return saver.save(video_bytes, filename, db_credentials)
