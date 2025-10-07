import os
import psycopg2
from psycopg2 import sql
from config import Settings
from logger import pipeline_logger, validation_logger


POSTGRES = Settings.POSTGRES 


class Table_gen:
    @staticmethod
    def table_generator(generated_files, video_bytes_list, audio_bytes_list=None):
        base_path = generated_files[1]
        topic_name = os.path.basename(base_path)

        py_files = generated_files[0].get("py_files", [])

        if len(video_bytes_list) != len(py_files):
            validation_logger.warning("⚠️ Warning: number of video bytes and py files do not match!")

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
                        id SERIAL PRIMARY KEY,
                        topic TEXT,
                        script TEXT,
                        video BYTEA,
                        remark TEXT
                    )
                    """
                ).format(table=sql.Identifier(POSTGRES["table"]))
            )

            # Insert rows
            for i, py_file in enumerate(py_files):
                script_name = os.path.splitext(os.path.basename(py_file))[0]

                video_bytes = video_bytes_list[i] if i < len(video_bytes_list) else None
                if video_bytes is None:
                    validation_logger.warning(f"Skipping {script_name}, no video bytes available")
                    continue

                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO {table} (topic, script, video, remark)
                        VALUES (%s, %s, %s, %s)
                        """
                    ).format(table=sql.Identifier(POSTGRES["table"])),
                    (topic_name, script_name, psycopg2.Binary(video_bytes), ""),
                )

                pipeline_logger.info(f"✅ Inserted {script_name} for topic {topic_name}")

            conn.commit()

        except Exception as e:
            validation_logger.error(f"❌ Database error: {e}")

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
