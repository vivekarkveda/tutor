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

        # Determine base path for Manim output
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        base_media_dir = os.path.join(project_root, "media", "videos")

        total_words = 0
        total_tokens = 0

        for file in generated_files["py_files"]:
            print("\n====================================")
            print(f"🧩 Processing File: {file}")
            pipeline_logger.info(f"🎬 Running Manim on {file} ...")

            # --- Count words + estimated tokens (for logging)
            word_count, token_count = VideoFactory.count_words_in_file(file)
            total_words += word_count
            total_tokens += token_count

            debug_msg = (
                f"🧮 File: {os.path.basename(file)} | "
                f"video_factory Words: {word_count} | Approx. GPT Tokens: {token_count}"
            )
            print(debug_msg)
            pipeline_logger.debug(debug_msg)

            # --- Extract session folder (e.g. script1_20251015_170540)
            parts = Path(file).parts
            try:
                session_folder = parts[-3]  # inputbox/<session>/<script_seqX>/file.py
            except IndexError:
                validation_logger.warning(f"⚠️ Could not detect session folder for {file}")
                session_folder = "unknown_session"

            # --- Set custom Manim output directory
            script_folder = os.path.splitext(os.path.basename(file))[0]
            custom_media_dir = os.path.join(base_media_dir, session_folder, script_folder)

            # --- Clean old outputs (fresh render)
            if os.path.exists(custom_media_dir):
                shutil.rmtree(custom_media_dir)
                pipeline_logger.info(f"🧹 Cleaned old media folder: {custom_media_dir}")
            os.makedirs(custom_media_dir, exist_ok=True)

            # --- Run Manim with this custom output path
            # --- Run Manim with this custom output path and capture all output
            result = subprocess.run(
                [
                    "poetry", "run", "manim", "-ql", file,
                    "--media_dir", custom_media_dir
                ],
                capture_output=True,  # capture stdout + stderr
                text=True  # decode output as text
            )

            # --- Handle Manim failure
            if result.returncode != 0:
                error_output = result.stderr.strip()
                stdout_output = result.stdout.strip()

                # Combine both for context
                full_error_log = (
                    f"\n❌ Error running Manim on {file}\n"
                    f"──────────────────────────────────────────────\n"
                    f"STDERR:\n{error_output or '(no stderr)'}\n\n"
                    f"STDOUT:\n{stdout_output or '(no stdout)'}\n"
                    f"──────────────────────────────────────────────\n"
                )

                # Log the full captured output
                pipeline_logger.error(full_error_log, extra={"part_name": "ManimRenderer"})
                print(full_error_log)  # optional: still see it in terminal
                continue

            # --- Try to extract Scene class name (supporting Scene, ThreeDScene, etc.)
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()

            match = re.search(r"class\s+(\w+)\([^)]*Scene[^)]*\)", content)
            if match:
                scene_name = match.group(1)
                pipeline_logger.info(f"🎞️ Detected Scene class: {scene_name}")
                pattern = f"{scene_name}.mp4"
            else:
                validation_logger.warning(f"⚠️ No Scene class found in {file}, using fallback search.")
                pattern = "*.mp4"  # fallback to any video

            # --- Find video files robustly
            found_files = list(Path(custom_media_dir).rglob(pattern))
            if not found_files:
                validation_logger.warning(f"⚠️ Could not locate video for {file}")
                continue

            # Pick the most recently modified video file
            video_path = max(found_files, key=os.path.getmtime)
            pipeline_logger.info(f"✅ Found video: {video_path}")

            # --- Read video into bytes
            try:
                with open(video_path, "rb") as f:
                    video_bytes_list.append(f.read())
            except Exception as e:
                validation_logger.error(f"❌ Failed to read video file {video_path}: {e}")
                continue

        # --- Summary log
        summary_msg = (
            f"✅ Total words: {total_words} | Approx. GPT tokens: {total_tokens} | "
            f"Total videos collected: {len(video_bytes_list)}"
        )
        print("\n" + summary_msg)
        pipeline_logger.info(summary_msg)
        print("video_bytes_list", len(video_bytes_list))

        return video_bytes_list

    # 🧮 Helper: Count words and approximate tokens
    @staticmethod
    def count_words_in_file(file_path):
        """Counts number of words and approximates GPT tokens in a given .py file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            words = content.split()
            word_count = len(words)
            approx_tokens = int(word_count / 0.75)  # simple token estimation
            return word_count, approx_tokens

        except Exception as e:
            validation_logger.error(f"❌ Failed to count words in {file_path}: {e}")
            return 0, 0
