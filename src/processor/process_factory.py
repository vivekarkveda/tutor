from processor.Manim.video_factory import VideoFactory
from processor.Pyttsx.audio_factory import AudioFactory


class ProcessFactory:
    process_history = []
    history_length = 10

    @staticmethod
    def get_processor(processor_name: str, generated_files):
        if processor_name == "manim":
            ProcessFactory.process_history.append("manim")
            return lambda: VideoFactory.run_manim_on_files(generated_files)
        elif processor_name == "tts":
            ProcessFactory.process_history.append("tts")
            return lambda: AudioFactory.text_files_to_audio_bytes(generated_files)
        else:
            raise Exception(f"❌ Processor {processor_name} not implemented")

    @staticmethod
    def get_state():
        return ProcessFactory.process_history
