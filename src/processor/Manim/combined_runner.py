import os
import subprocess
import re
from pathlib import Path

def run_manim_on_files(files, output_folder=r"C:\Vivek_Main\Manim_project\Manin_main\src\output\video"):
    """
    Runs Manim on the provided Python script files.
    Returns a list of video bytes for each rendered Scene.
    Also saves each video to the output folder.
    """
    os.makedirs(output_folder, exist_ok=True)
    video_bytes_list = []

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    base_media_dir = os.path.join(project_root, "media", "videos")

    for file in files:
        print(f"Running Manim on {file} ...")
        result = subprocess.run([
            "poetry", "run", "manim", "-ql", file
        ])
        if result.returncode != 0:
            print(f"❌ Error running Manim on {file}")
            continue

        # Detect the Scene class name
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r"class\s+(\w+)\(Scene\)", content)
        if not match:
            print(f"⚠️ No Scene class found in {file}")
            continue
        scene_name = match.group(1)

        # Get script folder name
        script_folder = os.path.splitext(os.path.basename(file))[0]

        # Expected video path
        video_path = os.path.join(
            base_media_dir, script_folder, "480p15", f"{scene_name}.mp4"
        )

        # Check if video exists
        if not os.path.exists(video_path):
            found_files = list(Path(base_media_dir).rglob(f"{scene_name}.mp4"))
            if found_files:
                video_path = str(found_files[0])
                print(f"🔍 Found video at: {video_path}")
            else:
                print(f"⚠️ Could not locate video for {file}")
                continue

        # Read video as bytes
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        video_bytes_list.append(video_bytes)

        # Save a copy to the output folder
        output_file_path = os.path.join(output_folder, f"{script_folder}_{scene_name}.mp4")
        with open(output_file_path, "wb") as f:
            f.write(video_bytes)

        print(f"✅ Video loaded as bytes and saved to: {output_file_path}")

    if not video_bytes_list:
        print("⚠️ No videos were loaded.")

    return video_bytes_list
