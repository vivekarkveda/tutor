import os

class SaverFactory:
    """Factory for saving final video bytes."""

    BASE_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

    @staticmethod
    def save_final_video(video_bytes: bytes, filename: str):
        """
        Save the final video bytes into the output directory.

        Args:
            video_bytes (bytes): Raw video data returned from previous steps.
            filename (str): Name for the saved file (with or without .mp4 extension).
        """
        os.makedirs(SaverFactory.BASE_OUTPUT_DIR, exist_ok=True)

        if not filename.lower().endswith(".mp4"):
            filename = f"{filename}.mp4"

        output_path = os.path.join(SaverFactory.BASE_OUTPUT_DIR, filename)

        with open(output_path, "wb") as f:
            f.write(video_bytes)

        print(f"✅ Final video saved at: {output_path}")
        return output_path
