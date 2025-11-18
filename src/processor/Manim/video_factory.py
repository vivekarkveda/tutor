import os
import subprocess
import re
import shutil
import traceback
from pathlib import Path
from logger import pipeline_logger, validation_logger
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception


class VideoFactory:
    """Runs Manim scripts and saves videos in structured media folders."""

    @staticmethod
    def run_manim_on_files(generated_files, unique_id):
        video_bytes_list = []
        all_success = True   # Track overall success

        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            base_media_dir = os.path.join(project_root, "media", "videos")

            total_words = 0
            total_tokens = 0

            for file in generated_files.get("py_files", []):
                try:
                    print("\n====================================")
                    print(f"🧩 Processing File: {file}")
                    pipeline_logger.info(f"🎬 Running Manim on {file} ...")

                    # Count words/tokens
                    word_count, token_count = VideoFactory.count_words_in_file(file)
                    total_words += word_count
                    total_tokens += token_count

                    # Detect session folder
                    parts = Path(file).parts
                    try:
                        session_folder = parts[-3]
                    except IndexError:
                        validation_logger.warning(f"⚠️ Could not detect session folder for {file}")
                        session_folder = "unknown_session"

                    # Output folder
                    script_folder = os.path.splitext(os.path.basename(file))[0]
                    custom_media_dir = os.path.join(base_media_dir, session_folder, script_folder)

                    # Clean old media
                    if os.path.exists(custom_media_dir):
                        shutil.rmtree(custom_media_dir)
                    os.makedirs(custom_media_dir, exist_ok=True)

                    # Run Manim
                    result = subprocess.run(
                        ["poetry", "run", "manim", "-ql", file, "--media_dir", custom_media_dir],
                        capture_output=True,
                        text=True
                    )

                    # Manim failed for this file
                    if result.returncode != 0:
                        all_success = False    # <-- Mark overall failure
                        error_output = result.stderr.strip()
                        stdout_output = result.stdout.strip()

                        full_error_log = (
                            f"\n❌ Error running Manim on {file}\n"
                            f"──────────────────────────────────────────────\n"
                            f"STDERR:\n{error_output or '(no stderr)'}\n\n"
                            f"STDOUT:\n{stdout_output or '(no stdout)'}\n"
                            f"──────────────────────────────────────────────\n"
                        )

                        pipeline_logger.error(full_error_log)
                        print(full_error_log)
                        continue

                    # Detect scene name
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read()

                    match = re.search(r"class\s+(\w+)\([^)]*Scene[^)]*\)", content)
                    pattern = f"{match.group(1)}.mp4" if match else "*.mp4"

                    # Find generated video
                    found_files = list(Path(custom_media_dir).rglob(pattern))
                    if not found_files:
                        all_success = False    # <-- Missing video is failure
                        validation_logger.warning(f"⚠️ No video found for {file}")
                        continue

                    video_path = max(found_files, key=os.path.getmtime)

                    # Read video bytes
                    try:
                        with open(video_path, "rb") as f:
                            video_bytes_list.append(f.read())
                    except Exception as read_err:
                        all_success = False   # <-- Reading failed is failure
                        validation_logger.error(f"❌ Failed to read video: {read_err}")
                        continue

                except Exception as per_file_error:
                    all_success = False   # <-- Any exception means failure
                    validation_logger.error(
                        f"❌ Unexpected error while processing file {file}: {per_file_error}"
                    )
                    continue

            # Summary
            summary_msg = (
                f"Total words: {total_words} | Approx. GPT tokens: {total_tokens} | "
                f"Total videos collected: {len(video_bytes_list)}"
            )
            pipeline_logger.info(summary_msg)

            # Final Transaction Status
            if all_success:
                transaction(unique_id, manim_output_status="Successful video generation")
            else:
                transaction(unique_id, manim_output_status="Unsuccessful video generation")
                exception(unique_id, type="video" ,description="At least one video failed to generate", module="VideoFactory")

            return video_bytes_list

        except Exception as e:
            # Critical failure
            pipeline_logger.critical(f"🔥 CRITICAL ERROR in run_manim_on_files: {e}")
            transaction(unique_id, manim_output_status="Unsuccessful video generation")
            # exception(unique_id, manim_output_status="Critical failure in video generation")
            return []

    
    # :abacus: Helper: Count words and approximate tokens
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
            validation_logger.error(f":x: Failed to count words in {file_path}: {e}")
            return 0, 0
