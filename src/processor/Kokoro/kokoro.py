import soundfile as sf
import torch
import numpy as np
from io import BytesIO
from pathlib import Path
from kokoro import KPipeline
from logger import pipeline_logger, validation_logger
from Transaction.excepetion import exception


class AudioFactory:
    """Generates audio bytes from TXT files using Kokoro TTS (in memory)."""

    @staticmethod
    def text_files_to_audio_bytes(generated_files, unique_id):
        audio_bytes_list = []
        pipeline = KPipeline(lang_code='a')

        module_name = "AudioFactory"

        for txt_file in generated_files.get("txt_files", []):
            txt_path = Path(txt_file)

            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    text = f.read().strip()

                if not text:
                    validation_logger.warning(f"⚠️ Skipping empty file: {txt_file}")

                    # ⬇️ NEW: Log skipped/empty content
                    exception(
                        unique_id,
                        type="audio",
                        description=f"Empty text file skipped: {txt_path.name}",
                        module=module_name
                    )
                    continue

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()

                exception(
                    unique_id,
                    type="audio",
                    description=f"Error reading text file: {txt_path.name} | {e}",
                    module=module_name
                )

                validation_logger.error(
                    f"❌ Failed reading text file {txt_path.name}: {e}\n{error_trace}"
                )
                continue

            try:
                generator = pipeline(text, voice="af_aoede")
                all_audio_chunks = []

                # ----------------------------------------------------
                # Process Kokoro generator chunks
                # ----------------------------------------------------
                for _, _, audio in generator:
                    try:
                        if isinstance(audio, torch.Tensor):
                            audio = audio.detach().cpu().numpy()

                        all_audio_chunks.append(audio)

                    except Exception as e:
                        import traceback
                        error_trace = traceback.format_exc()

                        # ⬇️ NEW: Exception placeholder for chunk-level error
                        exception(
                            unique_id,
                            type="audio",
                            description=f"Error processing audio chunk: {e}",
                            module=module_name
                        )

                        pipeline_logger.error(
                            f"\n❌ Error in audio chunk loop for {txt_path.name}:\n"
                            f"──────────────────────────────────────────\n"
                            f"{e}\n{error_trace}\n"
                            f"──────────────────────────────────────────"
                        )
                        continue

                # ----------------------------------------------------
                # Concatenate chunks into final audio
                # ----------------------------------------------------
                if all_audio_chunks:
                    try:
                        full_audio = np.concatenate(all_audio_chunks)
                        buffer = BytesIO()
                        sf.write(buffer, full_audio, samplerate=24000, format="WAV")
                        buffer.seek(0)
                        audio_bytes_list.append(buffer.read())

                        pipeline_logger.debug(
                            f"✅ Generated full audio for: {txt_path.name} (in memory)"
                        )

                    except Exception as e:
                        exception(
                            unique_id,
                            type="audio",
                            description=f"Failed concatenating final audio for {txt_path.name}: {e}",
                            module=module_name
                        )
                        validation_logger.error(
                            f"❌ Audio concatenation error for {txt_path.name}: {e}"
                        )

            except Exception as e:
                # General fallback for generator-level errors
                exception(
                    unique_id,
                    type="audio",
                    description=f"Kokoro TTS failed for {txt_path.name}: {e}",
                    module=module_name
                )

                validation_logger.error(
                    f"❌ Error generating audio for {txt_path.name}: {e}",
                    extra={"part_name": "KokoroAudioFactory"}
                )

        pipeline_logger.debug(f"Audio bytes count: {len(audio_bytes_list)}")
        print("audio_bytes_list", len(audio_bytes_list))
        return audio_bytes_list