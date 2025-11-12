import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from config import Settings
from merger_factory import MergerFactory
from parsers.base_handler import InputHandlerFactory
from file_fetcher_factory import FileFetcherFactory
from processor.process_factory import ProcessFactory
from saver_factory import SaverFactory
from table_gen import Table_gen
from logger import pipeline_logger, validation_logger
from pathlib import Path


async def run_in_executor(executor, func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


def prepare_files(run_from: str, generate_new_files: bool, file_types):
    """Either generate new files or fetch latest existing."""
    if generate_new_files:
        handler = InputHandlerFactory.get_input_handler(run_from)

        if run_from == "local":
            return handler.handle(Settings.JSON_FILE_PATH, file_types)

        elif run_from == "postgres":
            handler.set_credentials(Settings.POSTGRES)
            return handler.handle(Settings.SCRIPT_QUERY, file_types)

        else:
            raise ValueError("❌ Unsupported RUN_FROM type")

    return FileFetcherFactory.get_latest_files()


# --- Core pipeline ---
async def process_pipeline(generated_files, video: str, audio: str, run_from: str, transaction_folder: str = None):
    with ThreadPoolExecutor() as executor:
        video_callable = ProcessFactory.get_processor(video, generated_files[0])
        pipeline_logger.info(f"🎬 Video callable prepared for: {generated_files[1]}")
        audio_callable = ProcessFactory.get_processor(audio, generated_files[0])

        video_task = asyncio.create_task(run_in_executor(executor, video_callable))
        audio_task = asyncio.create_task(run_in_executor(executor, audio_callable))
        video_bytes_list, audio_bytes_list = await asyncio.gather(video_task, audio_task)

    PathList = SaverFactory.save_all_script_media(video_bytes_list, audio_bytes_list, generated_files)

    try:
        Table_gen.table_generator(generated_files, PathList)
    except Exception as e:
        pipeline_logger.warning(f"[TABLE_GEN] ⚠️ Skipping table generation due to error: {e}")


    output_path = None

    try:
        pipeline_logger.info("🎞️ [MERGE] Starting final video/audio merge process...")

        # --- Pre-check ---
        if not video_bytes_list or not audio_bytes_list:
            pipeline_logger.warning("⚠️ [MERGE] Empty video or audio bytes list — merge may fail.")

        pipeline_logger.info(f"🎬 [MERGE] Video clips: {len(video_bytes_list)}, Audio clips: {len(audio_bytes_list)}")

        # --- Perform merge ---
        start_time = datetime.now()
        final_video_bytes = MergerFactory.merge_all_videos_with_audio(video_bytes_list, audio_bytes_list)
        elapsed = (datetime.now() - start_time).total_seconds()

        if not final_video_bytes:
            raise ValueError("❌ [MERGE] MergerFactory returned empty final video bytes!")

        pipeline_logger.info(f"✅ [MERGE] Merge completed successfully in {elapsed:.2f}s.")

        # --- Generate filename ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_video_{timestamp}.mp4"
        pipeline_logger.info(f"💾 [MERGE] Preparing to save final video as '{filename}' (mode: {run_from}).")

        # --- Save final video ---
        output_path = SaverFactory.save_final_video(
            video_bytes=final_video_bytes,
            filename=filename,
            save_to=run_from,
            db_credentials=Settings.POSTGRES if run_from == "postgres" else None
        )

        if output_path:
            pipeline_logger.info(f"🎉 [MERGE] Final video saved successfully → {output_path}")
        else:
            pipeline_logger.warning("⚠️ [MERGE] SaverFactory.save_final_video returned None!")

    except Exception as e:
        pipeline_logger.exception("💥 [MERGE] Final video merge failed due to unexpected error.")
        pipeline_logger.error(f"❌ [MERGE] Error details: {str(e)}", exc_info=True)


    except Exception as e:
        pipeline_logger.exception("⚠️ Final video merge failed — proceeding with Drive upload anyway.")

    finally:
        # ✅ Always trigger Drive upload, even if merge failed
        pipeline_logger.info("🚀 Starting Drive upload process")

        try:
            from video_pipeline.drive_utils import upload_folder_to_drive
            from pathlib import Path
            from shutil import copy2

            # --- Step 1️⃣: Determine transaction folder safely ---
            folder_path = None

            if transaction_folder:
                folder_path = Path(transaction_folder)
                pipeline_logger.info(f"📂 Using provided transaction_folder: {folder_path}")
            elif Settings.TRANSACTION_FOLDER:
                folder_path = Path(Settings.TRANSACTION_FOLDER)
                pipeline_logger.info(f"📂 Using Settings.TRANSACTION_FOLDER: {folder_path}")
            else:
                persist_path = Settings.TEMP_GENERATED_FOLDER / "current_transaction.txt"
                if persist_path.exists():
                    recovered = persist_path.read_text().strip()
                    folder_path = Path(recovered)
                    pipeline_logger.info(f"♻️ Recovered TRANSACTION_FOLDER from persist file: {folder_path}")
                else:
                    pipeline_logger.warning("⚠️ No valid TRANSACTION_FOLDER or persist file found.")

            # --- Step 2️⃣: Copy final video into transaction folder ---
            if output_path and folder_path and folder_path.exists():
                try:
                    dest_path = folder_path / Path(output_path).name
                    copy2(output_path, dest_path)
                    pipeline_logger.info(f"📦 Final video copied to transaction folder: {dest_path}")
                except Exception as e:
                    pipeline_logger.warning(f"⚠️ Could not copy final video to transaction folder: {e}")

            # --- Step 3️⃣: Upload folder to Drive ---
            if folder_path and folder_path.exists():
                upload_folder_to_drive(
                    folder_path=str(folder_path),
                    auth_mode=Settings.DRIVE_AUTH_MODE
                )
                pipeline_logger.info("✅ Folder (with final video) successfully uploaded to Google Drive.")
            else:
                pipeline_logger.warning("⚠️ TRANSACTION_FOLDER not set or does not exist — skipping Drive upload.")

        except Exception as e:
            pipeline_logger.exception(f"❌ Failed to upload folder to Google Drive: {e}")

    return output_path


async def main():
    generated_files = prepare_files(Settings.RUN_FROM, Settings.GENERATE_NEW_FILES, Settings.FILE_TYPES)

    output_path = await process_pipeline(
        generated_files,
        Settings.VIDEO_PROCESSOR,
        Settings.AUDIO_PROCESSOR,
        Settings.RUN_FROM,
    )

    pipeline_logger.info(f"🎉 Pipeline completed! Final video saved at: {output_path}")
    pipeline_logger.info(f"📝 Process history: {ProcessFactory.get_state()}")


if __name__ == "__main__":
    asyncio.run(main())

