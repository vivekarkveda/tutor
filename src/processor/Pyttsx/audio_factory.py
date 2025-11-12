# src/processor/Pyttsx/audio_factory.py
from gtts import gTTS
from io import BytesIO
from pathlib import Path
from logger import pipeline_logger, validation_logger


class AudioFactory:
    """Generates audio bytes from TXT files (memory-only)."""

    @staticmethod
    def text_files_to_audio_bytes(generated_files):
        audio_bytes_list = []

        for txt_file in generated_files["txt_files"]:
            txt_path = Path(txt_file)
            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if not text:
                validation_logger.warning(f"⚠️ Skipping empty file: {txt_file}")
                continue

            tts = gTTS(text=text, lang="en")
            mp3_fp = BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            audio_bytes_list.append(mp3_fp.read())

            pipeline_logger.info(f"✅ Generated audio for: {txt_path.name} (in memory)")

        pipeline_logger.info(f"🎵 Total audio files generated: {len(audio_bytes_list)}")
        return audio_bytes_list
