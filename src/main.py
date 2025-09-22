import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from config import Settings
from merger_factory import MergerFactory
from parsers.base_handler import InputHandlerFactory
from file_fetcher_factory import FileFetcherFactory
from processor.process_factory import ProcessFactory
from saver_factory import SaverFactory


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
async def process_pipeline(generated_files, video: str, audio: str, run_from: str):
    with ThreadPoolExecutor() as executor:
        video_callable = ProcessFactory.get_processor(video, generated_files)
        audio_callable = ProcessFactory.get_processor(audio, generated_files)

        video_task = asyncio.create_task(run_in_executor(executor, video_callable))
        audio_task = asyncio.create_task(run_in_executor(executor, audio_callable))
        video_bytes_list, audio_bytes_list = await asyncio.gather(video_task, audio_task)

    final_video_bytes = MergerFactory.merge_all_videos_with_audio(video_bytes_list, audio_bytes_list)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"final_video_{timestamp}.mp4"

    output_path = SaverFactory.save_final_video(
        video_bytes=final_video_bytes,
        filename=filename,
        save_to=run_from,
        db_credentials=Settings.POSTGRES if run_from == "postgres" else None
    )


    print(f"🎉 Final video saved at: {output_path}")
    return output_path


async def main():
    generated_files = prepare_files(Settings.RUN_FROM, Settings.GENERATE_NEW_FILES, Settings.FILE_TYPES)


    output_path = await process_pipeline(
        generated_files,
        Settings.VIDEO_PROCESSOR,
        Settings.AUDIO_PROCESSOR,
        Settings.RUN_FROM,
    )

    print(f"🎉 Pipeline completed! Final video saved at: {output_path}")
    print(f"📝 Process history: {ProcessFactory.get_state()}")


if __name__ == "__main__":
    asyncio.run(main())
