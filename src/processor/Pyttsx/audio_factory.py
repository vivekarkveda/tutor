import os
from gtts import gTTS
from io import BytesIO
from pathlib import Path

class AudioFactory:
    """Factory for generating audio from narration text files."""

    BASE_OUTPUT_PATH = r"C:\Vivek_Main\Manim_project\Manin_main\src\output\audiofile"

    @staticmethod
    def text_files_to_audio_bytes(txt_file_list, output_folder=None, skip_existing=True):
        """
        Convert each narration TXT file to audio (MP3) using gTTS.
        Audio filenames are based on the TXT filename to avoid duplicates.

        Args:
            txt_file_list (list[str]): List of narration TXT file paths.
            output_folder (str, optional): Where to save MP3 files.
            skip_existing (bool): If True, skip files that already exist.

        Returns:
            list[bytes]: List of audio bytes corresponding to each TXT file.
        """
        if output_folder is None:
            output_folder = AudioFactory.BASE_OUTPUT_PATH

        os.makedirs(output_folder, exist_ok=True)
        audio_bytes_list = []

        for txt_file in txt_file_list:
            txt_path = Path(txt_file)
            audio_filename = f"{txt_path.stem}.mp3"
            file_path = Path(output_folder) / audio_filename

            # Skip if file already exists
            if skip_existing and file_path.exists():
                print(f"⏭ Skipping existing audio: {file_path}")
                with open(file_path, "rb") as f:
                    audio_bytes_list.append(f.read())
                continue

            # Read text
            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                print(f"⚠️ Skipping empty file: {txt_file}")
                continue

            # Generate audio
            tts = gTTS(text=text, lang="en")
            mp3_fp = BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            audio_bytes = mp3_fp.read()
            audio_bytes_list.append(audio_bytes)

            # Save MP3
            with open(file_path, "wb") as f:
                f.write(audio_bytes)

            print(f"✅ Generated audio: {file_path}")

        print(f"🎵 Total audio files generated/loaded: {len(audio_bytes_list)}")
        return audio_bytes_list
