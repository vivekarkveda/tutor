import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess
from config import Settings
from logger import pipeline_logger, validation_logger

debugging = Settings.debugging


class MergerFactory:
    """Factory for merging video and audio files in-memory (returns bytes only)."""

    if debugging:
        @staticmethod
        def merge_video_with_audio(video_bytes, audio_bytes, idx=1):
            pipeline_logger.info("Entering merge_video_with_audio")
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
                    return None

                with open(out_temp_path, "rb") as f:
                    merged_bytes = f.read()

                pipeline_logger.info(f"✅ Merged video {idx} returned as bytes")
                return merged_bytes

            finally:
                for path in [v_temp_path, a_temp_path, out_temp_path]:
                    if path and os.path.exists(path):
                        os.remove(path)

    else:
        @staticmethod
        def merge_video_with_audio(video_bytes, audio_bytes, idx=1):
            pipeline_logger.info("🎞️ [MERGE] Entering merge_video_with_audio")
            """
            Merge one or multiple video/audio pairs.
            If multiple pairs are provided, merges each and concatenates the results.
            Returns final video as bytes.
            """
            try:
                if isinstance(video_bytes, (bytes, bytearray)):
                    video_bytes = [video_bytes]
                if isinstance(audio_bytes, (bytes, bytearray)):
                    audio_bytes = [audio_bytes]

                if len(video_bytes) != len(audio_bytes):
                    error_msg = (
                        f"❌ [MERGE] Pair count mismatch: {len(video_bytes)} video(s) vs "
                        f"{len(audio_bytes)} audio(s). Skipping extra items."
                    )
                    pipeline_logger.warning(error_msg)
                    pair_count = min(len(video_bytes), len(audio_bytes))
                else:
                    pair_count = len(video_bytes)

                pipeline_logger.info(f"📦 [MERGE] Starting merge for {pair_count} pair(s).")
                merged_videos_bytes = []

                for pair_idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes[:pair_count], audio_bytes[:pair_count]), 1):
                    v_temp_path = a_temp_path = out_temp_path = None
                    try:
                        pipeline_logger.info(
                            f"🎬 [PAIR {pair_idx}] Preparing temporary files for merge. "
                            f"Video size = {len(v_bytes):,} bytes, Audio size = {len(a_bytes):,} bytes."
                        )

                        with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp, \
                                NamedTemporaryFile(delete=False, suffix=".mp3") as a_temp, \
                                NamedTemporaryFile(delete=False, suffix=".mp4") as out_temp:
                            v_temp.write(v_bytes)
                            a_temp.write(a_bytes)
                            v_temp_path, a_temp_path, out_temp_path = v_temp.name, a_temp.name, out_temp.name

                        pipeline_logger.info(
                            f"🔧 [PAIR {pair_idx}] Running ffmpeg to merge video/audio:\n"
                            f"  → Video file: {v_temp_path}\n"
                            f"  → Audio file: {a_temp_path}\n"
                            f"  → Output file: {out_temp_path}"
                        )

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
                            error_output = result.stderr.decode(errors="ignore")
                            validation_logger.error(
                                f"💥 [PAIR {pair_idx}] ffmpeg merge failed (return code {result.returncode}).\n"
                                f"🧾 Command: {' '.join(ffmpeg_cmd)}\n"
                                f"📄 stderr:\n{error_output}"
                            )
                            continue

                        with open(out_temp_path, "rb") as f:
                            merged_bytes = f.read()
                            merged_videos_bytes.append(merged_bytes)
                            pipeline_logger.info(
                                f"✅ [PAIR {pair_idx}] Merge successful. Output size = {len(merged_bytes):,} bytes."
                            )

                    except Exception as e:
                        pipeline_logger.exception(f"💥 [PAIR {pair_idx}] Unexpected error during merge: {e}")
                        continue

                    finally:
                        for path in [v_temp_path, a_temp_path, out_temp_path]:
                            if path and os.path.exists(path):
                                try:
                                    os.remove(path)
                                    pipeline_logger.debug(f"🧹 [PAIR {pair_idx}] Deleted temp file: {path}")
                                except Exception as cleanup_err:
                                    pipeline_logger.warning(
                                        f"⚠️ [PAIR {pair_idx}] Failed to delete temp file {path}: {cleanup_err}"
                                    )

                if not merged_videos_bytes:
                    validation_logger.warning("⚠️ [MERGE] No merged videos to process.")
                    return None

                if len(merged_videos_bytes) == 1:
                    pipeline_logger.info("🎬 [MERGE] Only one merged video, returning directly.")
                    return merged_videos_bytes[0]

                pipeline_logger.info(
                    f"🎞️ [MERGE] Concatenating {len(merged_videos_bytes)} merged videos into one final output..."
                )

                temp_video_paths = []
                list_file_path = final_output_path = None
                try:
                    for idx, v_bytes in enumerate(merged_videos_bytes, 1):
                        with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp:
                            v_temp.write(v_bytes)
                            temp_video_paths.append(Path(v_temp.name))
                            pipeline_logger.debug(f"📝 [CONCAT] Temp file for video {idx}: {v_temp.name}")

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

                    pipeline_logger.info(
                        f"🔗 [MERGE] Running ffmpeg concatenation for {len(temp_video_paths)} videos.\n"
                        f"🧾 Command: {' '.join(ffmpeg_concat_cmd)}"
                    )

                    result = subprocess.run(ffmpeg_concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode != 0:
                        error_output = result.stderr.decode(errors="ignore")
                        validation_logger.error(
                            f"💥 [MERGE] ffmpeg concatenation failed (return code {result.returncode}).\n"
                            f"📄 stderr:\n{error_output}"
                        )
                        return None

                    with open(final_output_path, "rb") as f:
                        final_bytes = f.read()
                        pipeline_logger.info(
                            f"🎉 [MERGE] Final concatenated video generated successfully! Size = {len(final_bytes):,} bytes."
                        )

                    return final_bytes

                finally:
                    for path in temp_video_paths + [list_file_path, final_output_path]:
                        if path and os.path.exists(path):
                            try:
                                os.remove(path)
                                pipeline_logger.debug(f"🧹 [MERGE] Deleted temp file: {path}")
                            except Exception as cleanup_err:
                                pipeline_logger.warning(
                                    f"⚠️ [MERGE] Could not delete temp file {path}: {cleanup_err}"
                                )

            except Exception as e:
                pipeline_logger.exception(f"💥 [MERGE] merge_video_with_audio failed unexpectedly: {e}")
                raise

    # ✅ FIX: Made globally accessible (not inside if debugging)
    @staticmethod
    def concatenate_videos(video_bytes_list):
        pipeline_logger.info("Entering concatenate_videos")
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

        temp_video_paths = []
        try:
            for idx, v_bytes in enumerate(video_bytes_list, 1):
                with NamedTemporaryFile(delete=False, suffix=".mp4") as v_temp:
                    v_temp.write(v_bytes)
                    temp_video_paths.append(Path(v_temp.name))

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

    @staticmethod
    def merge_all_videos_with_audio(video_bytes_list, audio_bytes_list):
        """
        Merges all video/audio pairs and concatenates them.
        Returns final merged video as bytes.
        """
        try:
            pipeline_logger.info("🎞️ Starting merge_all_videos_with_audio")
            pipeline_logger.info(f"🎬 Total video segments: {len(video_bytes_list)}, Total audio segments: {len(audio_bytes_list)}")

            total_video_bytes = sum(len(v) for v in video_bytes_list if v)
            total_audio_bytes = sum(len(a) for a in audio_bytes_list if a)
            pipeline_logger.info(f"📏 Total video bytes: {total_video_bytes:,}, Total audio bytes: {total_audio_bytes:,}")

            if len(video_bytes_list) != len(audio_bytes_list):
                pipeline_logger.error(
                    "❌ Video and audio lists must have the same length",
                    extra={"part_name": "MergerFactory"}
                )
                raise ValueError("Video and audio lists must have the same length")

            merged_videos_bytes = []

            for idx, (v_bytes, a_bytes) in enumerate(zip(video_bytes_list, audio_bytes_list), 1):
                pipeline_logger.info(f"🎞️ Merging video/audio pair {idx}")
                pipeline_logger.info(f"📦 Pair {idx} -> Video bytes: {len(v_bytes):,}, Audio bytes: {len(a_bytes):,}")
                merged_bytes = MergerFactory.merge_video_with_audio(v_bytes, a_bytes, idx=idx)
                if not merged_bytes:
                    pipeline_logger.warning(f"⚠️ No merged bytes returned for pair {idx}")
                    continue
                merged_videos_bytes.append(merged_bytes)

            if not merged_videos_bytes:
                raise RuntimeError("❌ No video/audio pairs were successfully merged.")

            pipeline_logger.info(f"🎬 Concatenating {len(merged_videos_bytes)} merged videos...")
            return MergerFactory.concatenate_videos(merged_videos_bytes)

        except Exception as e:
            pipeline_logger.exception("💥 merge_all_videos_with_audio failed.")
            raise
