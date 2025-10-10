# src/processor/Manim/video_factory.py
import os
import subprocess
import re
import shutil
from pathlib import Path
from logger import pipeline_logger, validation_logger


class VideoFactory:
    """Runs Manim scripts and saves videos in structured media folders."""

    @staticmethod
    def run_manim_on_files(generated_files):
        video_bytes_list = []

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        base_media_dir = os.path.join(project_root, "media", "videos")

        for file in generated_files["py_files"]:
            print("File_name:", file)
            pipeline_logger.info(f"🎬 Running Manim on {file} ...")

            # --- Extract session folder (e.g. sample_20251007_172414) ---
            parts = Path(file).parts
            try:
                session_folder = parts[-3]  # inputbox/<session>/<script_seqX>/file.py
            except IndexError:
                validation_logger.warning(f"⚠️ Could not detect session folder for {file}")
                session_folder = "unknown_session"

            # --- Set output directory for this script ---
            script_folder = os.path.splitext(os.path.basename(file))[0]
            custom_media_dir = os.path.join(base_media_dir, session_folder, script_folder)

            # --- If rerun, clean old outputs ---
            if os.path.exists(custom_media_dir):
                shutil.rmtree(custom_media_dir)
                pipeline_logger.info(f"🧹 Cleaned old media folder: {custom_media_dir}")

            os.makedirs(custom_media_dir, exist_ok=True)

            # --- Run Manim with custom media directory ---
            result = subprocess.run([
                "poetry", "run", "manim", "-ql", file,
                "--media_dir", custom_media_dir
            ])

            if result.returncode != 0:
                pipeline_logger.error(f"❌ Error running Manim on {file}")
                continue

            # --- Extract Scene class ---
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"class\s+(\w+)\(Scene\)", content)
            if not match:
                validation_logger.warning(f"⚠️ No Scene class found in {file}")
                continue
            scene_name = match.group(1)

            # --- Construct final video path ---
            video_path = os.path.join(custom_media_dir, "480p15", f"{scene_name}.mp4")

            # --- Verify and read ---
            if not os.path.exists(video_path):
                found_files = list(Path(custom_media_dir).rglob(f"{scene_name}.mp4"))
                if found_files:
                    video_path = str(found_files[0])
                    pipeline_logger.info(f"🔍 Found video at: {video_path}")
                else:
                    validation_logger.warning(f"⚠️ Could not locate video for {file}")
                    continue

            with open(video_path, "rb") as f:
                video_bytes_list.append(f.read())

        return video_bytes_list