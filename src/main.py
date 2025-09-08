from inputHandler import get_files, get_json_files, get_naration_files
from processor.Manim.combined_runner import run_manim_on_files
from OutputHandler import save_final_video
from processor.Pyttsx.ttl import text_files_to_audio_bytes
from parsers.parsers import pyfile_generator
from mearger import merge_all_videos_with_audio


if __name__ == "__main__":


    files = get_files()
    print("Files found:", files)
    naration_files =get_naration_files()
    print("naration files found:", naration_files)

    video_bytes_list = run_manim_on_files(files)
    audio_bytes_list = text_files_to_audio_bytes(naration_files)

    final_video_path = merge_all_videos_with_audio(
        video_bytes_list,
        audio_bytes_list,
        r"C:\Vivek_Main\Manim_project\Manin_main\src\output\final_video.mp4"
    )

    print("Final MP4 video path:", final_video_path)


    

    

    

