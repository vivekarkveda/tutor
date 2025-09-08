
import os


def save_final_video(video_bytes: bytes, filename: str):
    """
    Save the final video bytes into the output directory.

    Args:
        video_bytes (bytes): Raw video data returned from run_manim_on_files.
        filename (str): Name for the saved file (without .mp4 extension allowed).
    """
    # Absolute output directory
    output_dir = os.path.join(
        os.path.dirname(__file__), "output"
    )
    os.makedirs(output_dir, exist_ok=True)

    # Ensure .mp4 extension
    if not filename.lower().endswith(".mp4"):
        filename = f"{filename}.mp4"

    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as f:
        f.write(video_bytes)

    print(f"✅ Final video saved at: {output_path}")
    return output_path
