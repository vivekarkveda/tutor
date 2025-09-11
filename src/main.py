import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from merger_factory import MergerFactory

# --- Pipeline Factory ---
class PipelineFactory:
    """Factory for creating pipeline steps."""

    @staticmethod
    def get_pyfile_generator():
        from parsers.pyfile_factory import PyFileFactory
        return PyFileFactory.pyfile_generator

    @staticmethod
    def get_video_generator():
        from processor.Manim.video_factory import VideoFactory
        return VideoFactory.run_manim_on_files

    @staticmethod
    def get_audio_generator():
        from processor.Pyttsx.audio_factory import AudioFactory
        return AudioFactory.text_files_to_audio_bytes

    @staticmethod
    def get_merger():
        return MergerFactory.merge_all_videos_with_audio

    @staticmethod
    def get_saver():
        from saver_factory import SaverFactory
        return SaverFactory.save_final_video

# --- Async helper for sync functions ---
async def run_in_executor(executor, func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

# --- Main Async Pipeline ---
async def main():
    json_file_path = r"C:\Vivek_Main\Manim_project\jsonfiles\Pythagoras.json"

    RUN_PYFILE_FACTORY = False

    with ThreadPoolExecutor() as executor:
        if RUN_PYFILE_FACTORY:
            pyfile_generator = PipelineFactory.get_pyfile_generator()
            generated_files = await run_in_executor(executor, pyfile_generator, json_file_path)
            files = generated_files["py_files"]
            narration_files = generated_files["txt_files"]
        else:
            from file_fetcher_factory import FileFetcherFactory
            files = FileFetcherFactory.get_python_files()
            narration_files = FileFetcherFactory.get_narration_files()

        # Step 1: Generate video & audio in parallel
        run_manim = PipelineFactory.get_video_generator()
        run_tts = PipelineFactory.get_audio_generator()

        video_task = asyncio.create_task(run_in_executor(executor, run_manim, files))
        audio_task = asyncio.create_task(run_in_executor(executor, run_tts, narration_files))
        video_bytes_list, audio_bytes_list = await asyncio.gather(video_task, audio_task)

        # Step 2: Merge & Save
        merge = PipelineFactory.get_merger()
        save = PipelineFactory.get_saver()

        final_video_bytes = merge(video_bytes_list, audio_bytes_list)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(MergerFactory.BASE_OUTPUT_FOLDER) / f"final_video_{timestamp}.mp4"

        save(final_video_bytes, str(output_path))
        print(f"🎉 Pipeline completed! Final video saved at: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
