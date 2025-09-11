import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess

class MergerFactory:
    """Factory for merging video and audio files."""

    BASE_OUTPUT_FOLDER = r"C:\Vivek_Main\Manim_project\Manin_main\src\output\mearge"

    @staticmethod
    def merge_video_with_audio(video_bytes, audio_bytes, output_folder=None, idx=1):
        """
        Merge a single video with its corresponding audio.
        Pads audio with silence if shorter than video.
        Returns the path of the merged video file.
        """
        if output_folder is None:
            output_folder = MergerFactory.BASE_OUTPUT_FOLDER
        os.makedirs(output_folder, exist_ok=True)

        v_temp_path = a_temp_path = None
        try:
            with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp, \
                 NamedTemporaryFile(delete=False, suffix=".mp3") as a_temp:
                v_temp.write(video_bytes)
                a_temp.write(audio_bytes)
                v_temp_path = v_temp.name
                a_temp_path = a_temp.name

            merged_file_path = Path(output_folder) / f"merged_{idx}.mp4"

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", v_temp_path,
                "-i", a_temp_path,
                "-c:v", "copy",        # keep video stream unchanged
                "-c:a", "aac",         # encode audio
                "-b:a", "192k",
                "-af", "apad",         # pad audio with silence
                "-shortest",           # stop when video ends
                str(merged_file_path)
            ]

            result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                print(f"❌ Error merging video {idx}:\n{result.stderr.decode()}")
                return None

            print(f"✅ Merged video {idx} saved: {merged_file_path}")
            return merged_file_path

        finally:
            if v_temp_path and os.path.exists(v_temp_path):
                os.remove(v_temp_path)
            if a_temp_path and os.path.exists(a_temp_path):
                os.remove(a_temp_path)

    @staticmethod
    def concatenate_videos(video_paths, output_folder=None):
        """
        Concatenate multiple video files into a single video.
        Returns the final video as bytes.
        """
        if output_folder is None:
            output_folder = MergerFactory.BASE_OUTPUT_FOLDER
        os.makedirs(output_folder, exist_ok=True)

        if not video_paths:
            print("⚠️ No videos to concatenate.")
            return None

        if len(video_paths) == 1:
            final_path = video_paths[0]
            with open(final_path, "rb") as f:
                final_bytes = f.read()
            os.remove(final_path)
            print("🎬 Single video returned as bytes (no concatenation needed)")
            return final_bytes

        list_file = Path(output_folder) / "concat_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for video_file in video_paths:
                f.write(f"file '{video_file.resolve()}'\n")

        with NamedTemporaryFile(delete=False, suffix=".mp4") as final_temp:
            final_output_path = final_temp.name

        ffmpeg_concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            final_output_path
        ]

        result = subprocess.run(ffmpeg_concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.remove(list_file)

        if result.returncode != 0:
            print(f"❌ Error concatenating videos:\n{result.stderr.decode()}")
            return None

        with open(final_output_path, "rb") as f:
            final_bytes = f.read()

        for video_file in video_paths:
            if video_file.exists():
                os.remove(video_file)
        os.remove(final_output_path)

        print("🎬 Final concatenated MP4 video returned as bytes")
        return final_bytes

    @staticmethod
    def merge_all_videos_with_audio(video_bytes_list, audio_bytes_list, output_folder=None):
        """
        Merges all video/audio pairs and concatenates them.
        Returns final merged video as bytes.
        """
        if len(video_bytes_list) != len(audio_bytes_list):
            raise ValueError("Video and audio lists must have the same length")

        merged_paths = []
        for idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), 1):
            merged_path = MergerFactory.merge_video_with_audio(
                v_bytes, a_bytes, output_folder=output_folder, idx=idx
            )
            if merged_path:
                merged_paths.append(merged_path)

        return MergerFactory.concatenate_videos(merged_paths, output_folder=output_folder)
