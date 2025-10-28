import os
import psycopg2
from pathlib import Path
from logger import pipeline_logger


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
    """Factory that decides which saver to use and handles custom saves."""

    @staticmethod
    def save_final_video(video_bytes: bytes, filename: str, save_to: str, db_credentials=None):
        if save_to == "local":
            saver = LocalSaver()
        elif save_to == "postgres":
            saver = PostgresSaver()
        else:
            raise ValueError(f"❌ Unsupported save_to type: {save_to}")

        return saver.save(video_bytes, filename, db_credentials)

        # --- New method: save all script step media ---
    @staticmethod
    def save_all_script_media(video_bytes_list, audio_bytes_list, generated_files):
        """
        Saves each script step video/audio into fixed output paths:
        Videos -> C:\Vivek_Main\tutter\src\output\Video
        Audios -> C:\Vivek_Main\tutter\src\output\Audio
        Naming: <parent_folder_name>_script_seq<seq>.mp4/.mp3
        Returns: (list_of_video_paths, list_of_audio_paths)
        """

        videos_dir = Path(r"C:\Vivek_Main\tutter\src\output\Video")
        audios_dir = Path(r"C:\Vivek_Main\tutter\src\output\Audio")
        videos_dir.mkdir(parents=True, exist_ok=True)
        audios_dir.mkdir(parents=True, exist_ok=True)

        # ✅ Safely detect parent folder name
        try:
            # If dict format → use first py_file path to infer parent folder
            if isinstance(generated_files, dict):
                first_py = generated_files["py_files"][0]
                parent_folder_path = Path(first_py).parent.parent  # e.g. .../input_data_20251010_121145
                parent_folder_name = parent_folder_path.name
            else:
                # If list format → old behavior
                parent_folder_path = Path(generated_files[1])
                parent_folder_name = parent_folder_path.name
        except Exception as e:
            parent_folder_name = f"unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            pipeline_logger.warning(f"⚠ Could not detect parent folder name, defaulting to {parent_folder_name}. Error: {e}")

        video_paths = []
        audio_paths = []

        for idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), start=1):
            video_filename = f"{parent_folder_name}_script_seq{idx}.mp4"
            audio_filename = f"{parent_folder_name}_script_seq{idx}.mp3"

            video_path = videos_dir / video_filename
            audio_path = audios_dir / audio_filename

            if v_bytes:
                with open(video_path, "wb") as f:
                    f.write(v_bytes)
                pipeline_logger.info(f"🎬 Video saved at: {video_path}")
                video_paths.append(str(video_path))
            else:
                pipeline_logger.warning(f"⚠ Video bytes for step {idx} are empty, file not saved.")

            if a_bytes:
                with open(audio_path, "wb") as f:
                    f.write(a_bytes)
                pipeline_logger.info(f"🎵 Audio saved at: {audio_path}")
                audio_paths.append(str(audio_path))
            else:
                pipeline_logger.warning(f"⚠ Audio bytes for step {idx} are empty, file not saved.")

        print("📁 Videos saved to:", video_paths)
        print("📁 Audios saved to:", audio_paths)

        return [{"video_paths": video_paths}, {"audio_paths": audio_paths}]
