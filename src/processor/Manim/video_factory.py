# src/processor/Manim/video_factory.py
import os
import subprocess
import re
from pathlib import Path


class VideoFactory:
    """Runs Manim scripts and loads video bytes in memory."""

    @staticmethod
    
    def run_manim_on_files(generated_files):
        video_bytes_list = []

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        base_media_dir = os.path.join(project_root, "media", "videos")

        for file in generated_files["py_files"]:
            print(f"🎬 Running Manim on {file} ...")
            result = subprocess.run(["poetry", "run", "manim", "-ql", file])
            if result.returncode != 0:
                print(f"❌ Error running Manim on {file}")
                continue

            # Extract Scene class
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"class\s+(\w+)\(Scene\)", content)
            if not match:
                print(f"⚠️ No Scene class found in {file}")
                continue
            scene_name = match.group(1)

            script_folder = os.path.splitext(os.path.basename(file))[0]
            video_path = os.path.join(base_media_dir, script_folder, "480p15", f"{scene_name}.mp4")

            # Fallback search
            if not os.path.exists(video_path):
                found_files = list(Path(base_media_dir).rglob(f"{scene_name}.mp4"))
                if found_files:
                    video_path = str(found_files[0])
                    print(f"🔍 Found video at: {video_path}")
                else:
                    print(f"⚠️ Could not locate video for {file}")
                    continue

            # Read video bytes
            with open(video_path, "rb") as f:
                video_bytes_list.append(f.read())

        return video_bytes_list
