import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess
from config import Settings
from logger import pipeline_logger, validation_logger
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception
debugging = Settings.debugging 


class MergerFactory:
    """Factory for merging video and audio files, with database logging."""

    # ---------------- Debugging Mode ----------------
    @staticmethod
    def merge_video_with_audio_debug(video_bytes, audio_bytes, idx=1, unique_id=None):
        """Debug version — merges a single video/audio pair and returns bytes."""
        pipeline_logger.debug("🧩 merge_video_with_audio called in debugging mode")
        v_temp_path = a_temp_path = out_temp_path = None
        try:
            with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp, \
                 NamedTemporaryFile(delete=False, suffix=".mp3") as a_temp, \
                 NamedTemporaryFile(delete=False, suffix=".mp4") as out_temp:
                v_temp.write(video_bytes)
                a_temp.write(audio_bytes)
                v_temp_path, a_temp_path, out_temp_path = v_temp.name, a_temp.name, out_temp.name

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", v_temp_path,
                "-i", a_temp_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-af", "apad",
                "-shortest",
                out_temp_path
            ]

            result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                validation_logger.error(f"❌ Error merging video {idx}:\n{result.stderr.decode()}")
                if unique_id:
                    print("uidHello1")
                    transaction(unique_id, merge_status="Merge failed during debugging")
                return None

            with open(out_temp_path, "rb") as f:
                merged_bytes = f.read()

            pipeline_logger.info(f"✅ Merged video {idx} returned as bytes (debug mode)")
            if unique_id:
                print("uidHello2")
                transaction(unique_id, merge_status="Merge completed successfully (debug mode)")

            return merged_bytes

        finally:
            for path in [v_temp_path, a_temp_path, out_temp_path]:
                if path and os.path.exists(path):
                    os.remove(path)

    @staticmethod
    def concatenate_videos(video_bytes_list):
        """Concatenate multiple videos (as bytes) and return the final combined video bytes."""
        if not video_bytes_list:
            validation_logger.warning("⚠️ No videos to concatenate.")
            return None

        if len(video_bytes_list) == 1:
            pipeline_logger.info("🎬 Single video returned as bytes (no concatenation needed)")
            return video_bytes_list[0]

        temp_video_paths, list_file_path, final_output_path = [], None, None
        try:
            for idx, v_bytes in enumerate(video_bytes_list, 1):
                with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp:
                    v_temp.write(v_bytes)
                    temp_video_paths.append(Path(v_temp.name))

            # Write concat list
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
                if path and path is not None and os.path.exists(path):
                    os.remove(path)

    # ---------------- Production Mode ----------------
    @staticmethod
    def merge_video_with_audio(video_bytes_list, audio_bytes_list, unique_id, idx=1):
        """
        Merge one or multiple video/audio pairs and return final merged video as bytes.
        Updates `merge_status` in transaction table.
        """
        if len(video_bytes_list) != len(audio_bytes_list):
            pipeline_logger.error("❌ Video and audio list length mismatch", extra={"part_name": "MergerFactory"})
            print("uidHello3")
            print("unique_id_merge",unique_id)
            exception(unique_id, type="Merge", description="Video and audio list length mismatch",module="MergerFactory")
            transaction(unique_id, merge_status="Final video merge failed (list mismatch)")
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
                    v_temp_path, a_temp_path, out_temp_path = v_temp.name, a_temp.name, out_temp.name

                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", v_temp_path,
                    "-i", a_temp_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-af", "apad",
                    "-shortest",
                    out_temp_path
                ]

                result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    validation_logger.error(f"❌ Error merging video {pair_idx}:\n{result.stderr.decode()}")
                    continue

                with open(out_temp_path, "rb") as f:
                    merged_videos_bytes.append(f.read())

                pipeline_logger.info(f"✅ Merged video {pair_idx} successfully")

            finally:
                for path in [v_temp_path, a_temp_path, out_temp_path]:
                    if path and os.path.exists(path):
                        os.remove(path)

        if not merged_videos_bytes:
            print("uidHello4")
            transaction(unique_id, merge_status="Final video merge failed (no output)")
            return None

        # Concatenate all merged videos
        final_bytes = MergerFactory.concatenate_videos(merged_videos_bytes)
        if final_bytes:
            print("uidHello5")
            transaction(unique_id, merge_status="Final video merged successfully")
        else:
            print("uidHello6")
            transaction(unique_id, merge_status="Final video merge failed during concatenation")

        return final_bytes

    # ---------------- Unified Entry Point ----------------
    @staticmethod
    def merge_all_videos_with_audio(video_bytes_list, audio_bytes_list, unique_id):
        print("unique_id",unique_id)
        """Merge and concatenate all video/audio pairs based on debugging flag."""
        if debugging:
            merged_videos = []
            if len(video_bytes_list) != len(audio_bytes_list):
                pipeline_logger.error("❌ Video and audio list length mismatch (debug mode)")
                print("unique_id_7",unique_id)
                transaction(unique_id, merge_status="Final video merge failed (debug mode list mismatch)")
                raise ValueError("Video and audio lists must have the same length")

            for idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), 1):
                merged_bytes = MergerFactory.merge_video_with_audio_debug(v_bytes, a_bytes, idx, unique_id)
                if merged_bytes:
                    merged_videos.append(merged_bytes)

            return MergerFactory.concatenate_videos(merged_videos)
        else:
            return MergerFactory.merge_video_with_audio(video_bytes_list, audio_bytes_list, unique_id)
