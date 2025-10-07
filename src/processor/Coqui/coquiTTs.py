# src/processor/TTSX/audio_factory.py
from TTS.api import TTS
from pydub import AudioSegment
from pathlib import Path
import os
from logger import pipeline_logger, validation_logger


class AudioFactory:
    """Generates Hinglish audio (WAV bytes, memory-only) from TXT files using Coqui TTS."""

    @staticmethod
    def text_files_to_audio_bytes(generated_files):
        audio_bytes_list = []

        # Load TTS model (multilingual xtts_v2)
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        tts = TTS(model_name)

        pipeline_logger.info(f"🌍 Available Speakers: {tts.speakers}")
        pipeline_logger.info(f"🗣️ Available Languages: {tts.languages}")

        for txt_file in generated_files["txt_files"]:
            txt_path = Path(txt_file)

            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                validation_logger.warning(f"⚠️ Skipping empty file: {txt_file}")
                continue

            # Split into smaller segments if text is long (basic safeguard)
            segments = [s.strip() for s in text.split(".") if s.strip()]

            # Container for combined audio
            final_audio = AudioSegment.empty()

            # Generate audio per segment
            for i, seg in enumerate(segments):
                part_file = f"part_{i}.wav"
                tts.tts_to_file(
                    text=seg,
                    file_path=part_file,
                    language="en",                   # Hinglish handled via Hindi model
                    speaker="Kumar Dahl",        # Example: custom voice
                    speed=1.0,
                    temperature=0.7
                )
                final_audio += AudioSegment.from_wav(part_file) + AudioSegment.silent(duration=400)
                os.remove(part_file)

            # Export to memory (WAV bytes)
            from io import BytesIO
            audio_buffer = BytesIO()
            final_audio.export(audio_buffer, format="wav")
            audio_buffer.seek(0)

            audio_bytes_list.append(audio_buffer.read())
            pipeline_logger.info(f"✅ Generated Hinglish audio for: {txt_path.name} (in memory)")

        pipeline_logger.info(f"🎵 Total audio files generated: {len(audio_bytes_list)}")
        return audio_bytes_list
