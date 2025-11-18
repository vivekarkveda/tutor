from processor.Manim.video_factory import VideoFactory
from processor.Pyttsx.audio_factory import AudioFactory as PyttsxAudioFactory
from processor.Coqui.coquiTTs import AudioFactory as CoquiAudioFactory
from processor.IndicTTS.indicTTs import AudioFactory as IndicTTSAudioFactory
from processor.Kokoro.kokoro import AudioFactory as KokoroAudioFactory


class ProcessFactory:
    process_history = []
    history_length = 10

    @staticmethod
    def get_processor(processor_name: str, generated_files, unique_id):
        if processor_name == "manim":
            ProcessFactory.process_history.append("manim")
            return lambda: VideoFactory.run_manim_on_files(generated_files, unique_id)
        elif processor_name == "tts":
            ProcessFactory.process_history.append("tts")
            return lambda: PyttsxAudioFactory.text_files_to_audio_bytes(generated_files, unique_id)
        elif processor_name == "coqui":
            ProcessFactory.process_history.append("coqui")
            return lambda: CoquiAudioFactory.text_files_to_audio_bytes(generated_files, unique_id)
        elif processor_name == "indic":
            ProcessFactory.process_history.append("indic")
            return lambda: IndicTTSAudioFactory.text_files_to_audio_bytes(generated_files, unique_id)
        elif processor_name == "kokoro":
            ProcessFactory.process_history.append("kokoro")
            return lambda: KokoroAudioFactory.text_files_to_audio_bytes(generated_files, unique_id)
        else:
            raise Exception(f"❌ Processor {processor_name} not implemented")

    @staticmethod
    def get_state():
        return ProcessFactory.process_history
