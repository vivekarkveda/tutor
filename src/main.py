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
from Artifacts.artifacts import run_script_data_process
from Transaction.transaction_handler import transaction
from Transaction.excepetion import exception
import traceback
from video_pipeline.drive_utils import upload_folder_to_drive
from shutil import copy2
from pathlib import Path
from video_pipeline.utils import async_post, latest_input_folder

async def run_in_executor(executor, func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


def prepare_files(run_from: str, generate_new_files: bool, file_types, unique_id:str ):
    """Either generate new files or fetch latest existing."""
    print("unique_id main",unique_id)
    if generate_new_files:
        handler = InputHandlerFactory.get_input_handler(run_from, unique_id)

        if run_from == "local":
            return handler.handle(Settings.JSON_FILE_PATH, file_types)

        elif run_from == "postgres":
            handler.set_credentials(Settings.POSTGRES)
            return handler.handle(Settings.SCRIPT_QUERY, file_types)

        else:
            raise ValueError("❌ Unsupported RUN_FROM type")

    return FileFetcherFactory.get_latest_files()


# --- Core pipeline ---
async def process_pipeline(generated_files, video: str, audio: str, run_from: str, unique_id: str):
    try:
        # === VIDEO / AUDIO PROCESSING IN THREADS ===
        with ThreadPoolExecutor() as executor:
            video_callable = ProcessFactory.get_processor(video, generated_files[0], unique_id)
            pipeline_logger.info(f"Video callable prepared for: {generated_files[1]}")

            audio_callable = ProcessFactory.get_processor(audio, generated_files[0], unique_id)

            # Run video/audio tasks concurrently
            video_task = asyncio.create_task(run_in_executor(executor, video_callable))
            audio_task = asyncio.create_task(run_in_executor(executor, audio_callable))

            video_bytes_list, audio_bytes_list = await asyncio.gather(video_task, audio_task)

        print("generated_files:", generated_files)

        # === SAVE PROCESSED MEDIA ===
        PathList = SaverFactory.save_all_script_media(
            video_bytes_list,
            audio_bytes_list,
            generated_files
        )
        print("PathList =>", PathList)

        # Generate table (metadata / manifest)
        Table_gen.table_generator(generated_files, PathList)

        # === MERGE VIDEO + AUDIO ===
        final_video_bytes = MergerFactory.merge_all_videos_with_audio(
            video_bytes_list,
            audio_bytes_list,
            unique_id
        )

        # Timestamp filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_video_{timestamp}.mp4"

        # === SAVE FINAL VIDEO ===
        output_path = SaverFactory.save_final_video(
            video_bytes=final_video_bytes,
            filename=filename,
            save_to=run_from,
            db_credentials=Settings.POSTGRES if run_from == "postgres" else None
        )

        # === COPY TO UNIQUE SESSION FOLDER ===
        folder_path = latest_input_folder(Settings.TEMP_GENERATED_FOLDER, unique_id)
        dest_path = folder_path / Path(output_path).name
        copy2(output_path, dest_path)

        # === UPLOAD TO GOOGLE DRIVE ===
        upload_folder_to_drive(
            folder_path=str(folder_path),
            auth_mode=Settings.DRIVE_AUTH_MODE
        )

        # === RUN DB PROCESS / FINAL LOGIC ===
        print("mainUid:", unique_id)
        run_script_data_process(unique_id)

        pipeline_logger.info(f"🎉 Final video saved at: {output_path}")

        return output_path

    except Exception as e:
        pipeline_logger.error(f"❌ Pipeline failed for UID {unique_id}: {e}")
        pipeline_logger.error(traceback.format_exc())

        # Record error in database transaction system
        # transaction(
        #     unique_id=unique_id,
        #     script_gen_status="pipeline failed",
        #     exception_message=str(e),
        #     trace=traceback.format_exc()
        # )

        raise   # rethrow to let caller know failure occurred


async def main():
    generated_files = prepare_files(Settings.RUN_FROM, Settings.GENERATE_NEW_FILES, Settings.FILE_TYPES,)

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