import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess

def get_duration_from_file(file_path):
    """Returns the duration of a media file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    try:
        return float(result.stdout)
    except ValueError:
        return 0.0

def merge_all_videos_with_audio(video_bytes_list, audio_bytes_list, final_output_path,
                                merge_output_folder=r"C:\Vivek_Main\Manim_project\Manin_main\src\output\mearge"):
    """
    Merge each video with its corresponding audio, save each individually,
    then concatenate all into one final MP4.
    Re-encodes final video to ensure audio is preserved.
    """
    if len(video_bytes_list) != len(audio_bytes_list):
        raise ValueError("Video and audio lists must have the same length")
    
    os.makedirs(merge_output_folder, exist_ok=True)
    temp_merged_files = []

    # Step 1: Merge each video with its corresponding audio
    for idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), 1):
        print(f"\n📌 Processing video {idx}")
        print(f"Video bytes length: {len(v_bytes)}")
        print(f"Audio bytes length: {len(a_bytes)}")

        with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp, \
             NamedTemporaryFile(delete=False, suffix=".mp3") as a_temp:
            
            v_temp.write(v_bytes)
            a_temp.write(a_bytes)
            v_temp_path = v_temp.name
            a_temp_path = a_temp.name

        merged_file_name = f"merged_{idx}.mp4"
        merged_temp_file = Path(merge_output_folder) / merged_file_name

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", v_temp_path,
            "-i", a_temp_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(merged_temp_file)
        ]

        result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"❌ Error merging video {idx} with audio:\n{result.stderr.decode()}")
            os.remove(v_temp_path)
            os.remove(a_temp_path)
            continue

        temp_merged_files.append(merged_temp_file)

        # Print duration info
        duration = get_duration_from_file(merged_temp_file)
        print(f"✅ Video {idx} merged with audio: {merged_temp_file} (Duration: {duration:.2f} sec)")

        # Cleanup temp files
        os.remove(v_temp_path)
        os.remove(a_temp_path)

    if not temp_merged_files:
        print("⚠️ No merged videos to concatenate.")
        return None

    # Step 2: Concatenate all merged segments into final output
    list_file = Path(merge_output_folder) / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for temp_file in temp_merged_files:
            f.write(f"file '{temp_file.resolve()}'\n")

    ffmpeg_concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(final_output_path)
    ]

    result = subprocess.run(ffmpeg_concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        print(f"🎬 Final merged MP4 video saved: {final_output_path}")
    else:
        print(f"❌ Error concatenating videos:\n{result.stderr.decode()}")
        final_output_path = None

    # Cleanup concat list
    os.remove(list_file)

    return final_output_path
