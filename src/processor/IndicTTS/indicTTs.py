# src/processor/TTSX/audio_factory.py
from TTS.api import TTS
from pydub import AudioSegment
from pathlib import Path
from io import BytesIO
import os
from logger import pipeline_logger, validation_logger


class AudioFactory:
    """Generates Hindi audio (WAV bytes in memory) using your FastPitch + HiFi-GAN model."""

    @staticmethod
    def text_files_to_audio_bytes(generated_files):
        audio_bytes_list = []

        # Load your local Hindi model (not multilingual)
        tts = TTS(
            model_path="C:/Vivek_Main/Datasets/indictts/en+hi/fastpitch/best_model.pth",
            config_path="C:/Vivek_Main/Datasets/indictts/en+hi/fastpitch/config.json",
            vocoder_path="C:/Vivek_Main/Datasets/indictts/en+hi/hifigan/best_model.pth",
            vocoder_config_path="C:/Vivek_Main/Datasets/indictts/en+hi/hifigan/config.json"
        )

        # Try to print speaker info
        try:
            pipeline_logger.info(f"🎙️ Available Speakers: {tts.speakers}")
        except Exception:
            pipeline_logger.info("ℹ️ Speaker info not available for this model.")

        for txt_file in generated_files["txt_files"]:
            txt_path = Path(txt_file)

            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                validation_logger.warning(f"⚠️ Skipping empty file: {txt_file}")
                continue

            # Split into smaller sentences
            segments = [s.strip() for s in text.split("।") if s.strip()]

            final_audio = AudioSegment.empty()

            # Choose speaker dynamically (use 'male' or 'female')
            chosen_speaker = "female"

            for i, seg in enumerate(segments):
                if not seg:
                    continue

                temp_wav = f"part_{i}.wav"
                tts.tts_to_file(
                    text=seg,
                    speaker=chosen_speaker,
                    file_path=temp_wav
                )

                # Add to final combined audio
                final_audio += AudioSegment.from_wav(temp_wav) + AudioSegment.silent(duration=400)
                os.remove(temp_wav)

            # Export to in-memory WAV
            buffer = BytesIO()
            final_audio.export(buffer, format="wav")
            buffer.seek(0)

            audio_bytes_list.append(buffer.read())
            pipeline_logger.info(f"✅ Generated Hindi audio for: {txt_path.name}")

        pipeline_logger.info(f"🎵 Total audio files generated: {len(audio_bytes_list)}")
        return audio_bytes_list
