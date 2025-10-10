import os
import psycopg2
import random
import string
from datetime import datetime
from psycopg2 import sql
from config import Settings
from logger import pipeline_logger, validation_logger
POSTGRES = Settings.POSTGRES
VIDEO_Type = Settings.VIDEO_PROCESSOR
AUDIO_Type = Settings.AUDIO_PROCESSOR

class Table_gen:
    @staticmethod
    def _generate_content_id(topic_name: str):
        """Generates unique content ID like Pythagoras_20251007_A1B2C3"""
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{topic_name}_{date_part}_{random_part}"

    @staticmethod
    def table_generator(generated_files, PathList):
        """
        Saves records to PostgreSQL using file paths instead of byte arrays.
        PathList: [{'video_paths': [...], 'audio_paths': [...]}]
        """
        base_path = generated_files[1]
        topic_name = os.path.basename(base_path)

        py_files = generated_files[0].get("py_files", [])
        txt_files = generated_files[0].get("txt_files", [])

        # Extract video/audio paths
        video_paths = PathList[0].get("video_paths", [])
        audio_paths = PathList[1].get("audio_paths", [])

        if len(video_paths) != len(py_files):
            validation_logger.warning("⚠ Warning: number of video paths and py files do not match!")
        if len(audio_paths) != len(txt_files):
            validation_logger.warning("⚠ Warning: number of audio paths and txt files do not match!")

        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=POSTGRES["host"],
                port=POSTGRES["port"],
                user=POSTGRES["user"],
                password=POSTGRES["password"],
                dbname=POSTGRES["dbname"],
            )
            cur = conn.cursor()

            # Create table if not exists
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        content_id TEXT PRIMARY KEY,
                        video_script TEXT,
                        video_path TEXT,
                        video_type TEXT,
                        tts_script TEXT,
                        tts_type TEXT,
                        tts_path TEXT,
                        creation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        flag TEXT,
                        exception TEXT
                    )
                    """
                ).format(table=sql.Identifier(POSTGRES["table"]))
            )

            # Insert rows
            for i, py_file in enumerate(py_files):
                script_name = os.path.splitext(os.path.basename(py_file))[0]
                video_path = video_paths[i] if i < len(video_paths) else None
                audio_path = audio_paths[i] if i < len(audio_paths) else None

                # Read TTS script
                tts_script = None
                if i < len(txt_files):
                    try:
                        with open(txt_files[i], "r", encoding="utf-8") as f:
                            tts_script = f.read()
                    except Exception as e:
                        validation_logger.error(f"⚠ Could not read TTS file for {script_name}: {e}")

                # Generate unique content_id
                content_id = Table_gen._generate_content_id(topic_name)

                # Insert record with file paths
                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO {table}
                        (content_id, video_script, video_path, video_type,
                         tts_script, tts_type, tts_path,
                         flag, exception)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                    ).format(table=sql.Identifier(POSTGRES["table"])),
                    (
                        content_id,
                        script_name,
                        video_path,
                        VIDEO_Type,
                        tts_script,
                        AUDIO_Type,
                        audio_path,
                        "save",
                        None,
                    ),
                )
                pipeline_logger.info(f"✅ Inserted record {content_id} with paths")

            conn.commit()

        except Exception as e:
            validation_logger.error(f"❌ Database error: {e}")

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()