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
        pipeline_logger.info("🚀 [TABLE_GEN] Starting table generation and DB insertion process...")

        base_path = generated_files[1]
        topic_name = os.path.basename(base_path)
        pipeline_logger.info(f"📂 [TABLE_GEN] Topic: {topic_name}")

        py_files = generated_files[0].get("py_files", [])
        txt_files = generated_files[0].get("txt_files", [])
        video_paths = PathList[0].get("video_paths", [])
        audio_paths = PathList[1].get("audio_paths", [])

        pipeline_logger.info(f"📁 [TABLE_GEN] Found {len(py_files)} scripts, {len(txt_files)} txts, "
                             f"{len(video_paths)} videos, {len(audio_paths)} audios")

        if len(video_paths) != len(py_files):
            validation_logger.warning("⚠ [TABLE_GEN] Warning: number of video paths and py files do not match!")
        if len(audio_paths) != len(txt_files):
            validation_logger.warning("⚠ [TABLE_GEN] Warning: number of audio paths and txt files do not match!")

        conn, cur = None, None

        try:
            # Connect to PostgreSQL
            pipeline_logger.info(f"🧩 [TABLE_GEN] Connecting to PostgreSQL database '{POSTGRES['dbname']}'...")
            conn = psycopg2.connect(
                host=POSTGRES["host"],
                port=POSTGRES["port"],
                user=POSTGRES["user"],
                password=POSTGRES["password"],
                dbname=POSTGRES["dbname"],
            )
            cur = conn.cursor()
            pipeline_logger.info("✅ [TABLE_GEN] PostgreSQL connection established successfully.")

            # Create table if not exists
            pipeline_logger.info(f"🛠 [TABLE_GEN] Ensuring table '{POSTGRES['table']}' exists...")
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
            pipeline_logger.info("✅ [TABLE_GEN] Table check/creation complete.")

            # Insert rows
            for i, py_file in enumerate(py_files):
                script_name = os.path.splitext(os.path.basename(py_file))[0]
                video_path = video_paths[i] if i < len(video_paths) else None
                audio_path = audio_paths[i] if i < len(audio_paths) else None

                # ✅ Convert any Path objects to strings (important!)
                if video_path is not None:
                    video_path = str(video_path)
                if audio_path is not None:
                    audio_path = str(audio_path)

                pipeline_logger.info(f"📝 [TABLE_GEN] Preparing record {i + 1}/{len(py_files)}: {script_name}")

                # Read TTS script
                tts_script = None
                if i < len(txt_files):
                    try:
                        with open(txt_files[i], "r", encoding="utf-8") as f:
                            tts_script = f.read()
                            pipeline_logger.debug(f"📄 [TABLE_GEN] Loaded TTS script for {script_name}")
                    except Exception as e:
                        validation_logger.error(f"⚠ [TABLE_GEN] Could not read TTS file for {script_name}: {e}")

                # Generate unique content_id
                content_id = Table_gen._generate_content_id(topic_name)
                pipeline_logger.debug(f"🆔 [TABLE_GEN] Generated content_id: {content_id}")

                try:
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
                    pipeline_logger.info(f"✅ [TABLE_GEN] Inserted record into DB: {content_id}")

                except Exception as insert_error:
                    validation_logger.error(f"❌ [TABLE_GEN] Failed to insert {script_name}: {insert_error}")

            conn.commit()
            pipeline_logger.info("💾 [TABLE_GEN] All records committed successfully to PostgreSQL.")

        except Exception as e:
            validation_logger.error(f"❌ [TABLE_GEN] Database connection or execution error: {e}", exc_info=True)

        finally:
            if cur:
                cur.close()
                pipeline_logger.debug("🔒 [TABLE_GEN] Cursor closed.")
            if conn:
                conn.close()
                pipeline_logger.debug("🔌 [TABLE_GEN] Database connection closed.")

        pipeline_logger.info("🏁 [TABLE_GEN] Table generation process completed.")
