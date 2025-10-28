import soundfile as sf
import torch
import numpy as np
from io import BytesIO
from pathlib import Path
from kokoro import KPipeline
from logger import pipeline_logger, validation_logger


class AudioFactory:
    """Generates audio bytes from TXT files using Kokoro TTS (in memory)."""

    @staticmethod
    def text_files_to_audio_bytes(generated_files):
        audio_bytes_list = []
        pipeline = KPipeline(lang_code='a')

        for txt_file in generated_files.get("txt_files", []):
            txt_path = Path(txt_file)

            # Read text
            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                validation_logger.warning(f"⚠️ Skipping empty file: {txt_file}")
                continue

            try:
                generator = pipeline(text, voice="af_aoede")
                all_audio_chunks = []

                # ✅ Collect *all* generated audio chunks
                for _, _, audio in generator:
                    if isinstance(audio, torch.Tensor):
                        audio = audio.detach().cpu().numpy()
                    all_audio_chunks.append(audio)

                # ✅ Concatenate all chunks together
                if all_audio_chunks:
                    full_audio = np.concatenate(all_audio_chunks)

                    # Write to memory as WAV bytes
                    buffer = BytesIO()
                    sf.write(buffer, full_audio, samplerate=24000, format="WAV")
                    buffer.seek(0)
                    audio_bytes_list.append(buffer.read())

                pipeline_logger.debug(f"✅ Generated full audio for: {txt_path.name} (in memory)")

            except Exception as e:
                validation_logger.error(f"❌ Error generating audio for {txt_path.name}: {e}")

        pipeline_logger.debug(f"Audio bytes count: {len(audio_bytes_list)}")
        print("audio_bytes_list", len(audio_bytes_list))
        return audio_bytes_list