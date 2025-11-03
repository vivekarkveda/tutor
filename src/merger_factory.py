import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess
from config import Settings
from logger import pipeline_logger, validation_logger

debugging=Settings.debugging


class MergerFactory:
    """Factory for merging video and audio files in-memory (returns bytes only)."""

    if debugging:
        @staticmethod
        def merge_video_with_audio(video_bytes, audio_bytes, idx=1):
            """
            Merge a single video with its corresponding audio.
            Pads audio with silence if shorter than video.
            Returns merged video as bytes (no file saved).
            """
            pipeline_logger.debug("merge_video_with_audio called in debugging mode")
            v_temp_path = a_temp_path = out_temp_path = None
            try:
                with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp, \
                    NamedTemporaryFile(delete=False, suffix=".mp3") as a_temp, \
                    NamedTemporaryFile(delete=False, suffix=".mp4") as out_temp:
                    v_temp.write(video_bytes)
                    a_temp.write(audio_bytes)
                    v_temp_path = v_temp.name
                    a_temp_path = a_temp.name
                    out_temp_path = out_temp.name

                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", v_temp_path,
                    "-i", a_temp_path,
                    "-c:v", "copy",        # keep video stream unchanged
                    "-c:a", "aac",         # encode audio
                    "-b:a", "192k",
                    "-af", "apad",         # pad audio with silence
                    "-shortest",           # stop when video ends
                    out_temp_path
                ]

                result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    validation_logger.error(f"❌ Error merging video {idx}:\n{result.stderr.decode()}")
                    return None

                with open(out_temp_path, "rb") as f:
                    merged_bytes = f.read()

                pipeline_logger.info(f"✅ Merged video {idx} returned as bytes")
                return merged_bytes

            finally:
                for path in [v_temp_path, a_temp_path, out_temp_path]:
                    if path and os.path.exists(path):
                        os.remove(path)

        @staticmethod
        def concatenate_videos(video_bytes_list):
            """
            Concatenate multiple videos (provided as bytes).
            Returns the final concatenated video as bytes.
            """
            if not video_bytes_list:
                validation_logger.warning("⚠️ No videos to concatenate.")
                return None

            if len(video_bytes_list) == 1:
                pipeline_logger.info("🎬 Single video returned as bytes (no concatenation needed)")
                return video_bytes_list[0]

            # Write all input videos to temporary files
            temp_video_paths = []
            try:
                for idx, v_bytes in enumerate(video_bytes_list, 1):
                    with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp:
                        v_temp.write(v_bytes)
                        temp_video_paths.append(Path(v_temp.name))

                # Create concat list file
                with NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as list_file:
                    for video_file in temp_video_paths:
                        list_file.write(f"file '{video_file.resolve()}'\n")
                    list_file_path = list_file.name

                with NamedTemporaryFile(delete=False, suffix=".mp4") as final_temp:
                    final_output_path = final_temp.name

                ffmpeg_concat_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    final_output_path
                ]

                result = subprocess.run(ffmpeg_concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    validation_logger.error(f"❌ Error concatenating videos:\n{result.stderr.decode()}")
                    return None

                with open(final_output_path, "rb") as f:
                    final_bytes = f.read()

                pipeline_logger.info("🎬 Final concatenated MP4 video returned as bytes")
                return final_bytes

            finally:
                for path in temp_video_paths + [list_file_path, final_output_path]:
                    if path and os.path.exists(path):
                        os.remove(path)

    else:
        @staticmethod
        def merge_video_with_audio(video_bytes_list, audio_bytes_list, idx=1):
            """
            Merge one or multiple video/audio pairs.
            If multiple pairs are provided, merges each and concatenates the results.
            Returns final video as bytes.
            """
            if len(video_bytes_list) != len(audio_bytes_list):
                # Log to PostgreSQL and console
                pipeline_logger.error(
                    "❌ Video and audio lists must have the same length",
                    extra={"part_name": "MergerFactory"}
                )
                # Also raise an explicit error for control flow
                raise ValueError("Video and audio lists must have the same length")

            merged_videos_bytes = []

            for pair_idx, (video_bytes, audio_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), 1):
                v_temp_path = a_temp_path = out_temp_path = None
                try:
                    with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp, \
                        NamedTemporaryFile(delete=False, suffix=".mp3") as a_temp, \
                        NamedTemporaryFile(delete=False, suffix=".mp4") as out_temp:
                        v_temp.write(video_bytes)
                        a_temp.write(audio_bytes)
                        v_temp_path = v_temp.name
                        a_temp_path = a_temp.name
                        out_temp_path = out_temp.name

                    ffmpeg_cmd = [
                        "ffmpeg", "-y",
                        "-i", v_temp_path,
                        "-i", a_temp_path,
                        "-c:v", "copy",        # keep video stream unchanged
                        "-c:a", "aac",         # encode audio
                        "-b:a", "192k",
                        "-af", "apad",         # pad audio with silence
                        "-shortest",           
                        out_temp_path
                    ]

                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode != 0:
                        validation_logger.error(f"❌ Error merging video {pair_idx}:\n{result.stderr.decode()}")
                        continue

                    with open(out_temp_path, "rb") as f:
                        merged_videos_bytes.append(f.read())

                    pipeline_logger.info(f"✅ Merged video {pair_idx} returned as bytes")

                finally:
                    for path in [v_temp_path, a_temp_path, out_temp_path]:
                        if path and os.path.exists(path):
                            os.remove(path)

            # ---- Concat step (if more than one) ----
            if not merged_videos_bytes:
                validation_logger.warning("⚠️ No merged videos to process.")
                return None

            if len(merged_videos_bytes) == 1:
                pipeline_logger.info("🎬 Only one merged video, returning directly.")
                return merged_videos_bytes[0]

            temp_video_paths = []
            list_file_path = final_output_path = None
            try:
                # Write merged videos to temp files
                for v_bytes in merged_videos_bytes:
                    with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp:
                        v_temp.write(v_bytes)
                        temp_video_paths.append(Path(v_temp.name))

                # Create concat list file
                with NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as list_file:
                    for video_file in temp_video_paths:
                        list_file.write(f"file '{video_file.resolve()}'\n")
                    list_file_path = list_file.name

                with NamedTemporaryFile(delete=False, suffix=".mp4") as final_temp:
                    final_output_path = final_temp.name

                ffmpeg_concat_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    final_output_path
                ]

                result = subprocess.run(ffmpeg_concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    validation_logger.error(f"❌ Error concatenating merged videos:\n{result.stderr.decode()}")
                    return None

                with open(final_output_path, "rb") as f:
                    final_bytes = f.read()

                pipeline_logger.info("🎬 Final merged+concatenated MP4 returned as bytes")
                return final_bytes

            finally:
                for path in temp_video_paths + [list_file_path, final_output_path]:
                    if path and os.path.exists(path):
                        os.remove(path)


    @staticmethod
    def merge_all_videos_with_audio(video_bytes_list, audio_bytes_list):
        """
        Merges all video/audio pairs and concatenates them.
        Returns final merged video as bytes.
        """

        if debugging:

            if len(video_bytes_list) != len(audio_bytes_list):
                pipeline_logger.error(
                    "❌ Video and audio lists must have the same length",
                    extra={"part_name": "MergerFactory"}
                )

                raise ValueError("Video and audio lists must have the same length")

            merged_videos_bytes = []
            for idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), 1):
                merged_bytes = MergerFactory.merge_video_with_audio(v_bytes, a_bytes, idx=idx)
                if merged_bytes:
                    merged_videos_bytes.append(merged_bytes)

            return MergerFactory.concatenate_videos(merged_videos_bytes)

        else:
            return MergerFactory.merge_video_with_audio(video_bytes_list, audio_bytes_list)
