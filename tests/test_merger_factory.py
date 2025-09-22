import subprocess
import pytest
from pathlib import Path
from merger_factory import MergerFactory


def generate_dummy_video(path: Path, duration=1):
    """Generate a small dummy silent MP4 video using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=red:s=160x120:d={duration}",
        "-pix_fmt", "yuv420p",
        str(path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def generate_dummy_audio(path: Path, duration=1):
    """Generate a small dummy silent MP3 audio using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono:d={duration}",
        str(path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


@pytest.fixture
def dummy_files(tmp_path):
    """Creates dummy video + audio files for testing."""
    video_file = tmp_path / "test.mp4"
    audio_file = tmp_path / "test.mp3"
    generate_dummy_video(video_file)
    generate_dummy_audio(audio_file)

    return {
        "video_bytes": video_file.read_bytes(),
        "audio_bytes": audio_file.read_bytes(),
    }


def test_merge_video_with_audio(dummy_files):
    merged = MergerFactory.merge_video_with_audio(
        dummy_files["video_bytes"], dummy_files["audio_bytes"]
    )
    assert merged is not None
    assert isinstance(merged, bytes)
    assert len(merged) > 100  # ensure non-empty output


def test_concatenate_single_video(dummy_files):
    single = MergerFactory.concatenate_videos([dummy_files["video_bytes"]])
    assert single == dummy_files["video_bytes"]


def test_concatenate_multiple_videos(dummy_files, tmp_path):
    # Generate a second dummy video
    second_video = tmp_path / "test2.mp4"
    generate_dummy_video(second_video, duration=2)

    final = MergerFactory.concatenate_videos(
        [dummy_files["video_bytes"], second_video.read_bytes()]
    )
    assert final is not None
    assert isinstance(final, bytes)
    assert len(final) > len(dummy_files["video_bytes"])  # concatenated should be longer


def test_merge_all_videos_with_audio(dummy_files, tmp_path):
    # Create another pair
    second_video = tmp_path / "test2.mp4"
    second_audio = tmp_path / "test2.mp3"
    generate_dummy_video(second_video, duration=1)
    generate_dummy_audio(second_audio, duration=1)

    final = MergerFactory.merge_all_videos_with_audio(
        [dummy_files["video_bytes"], second_video.read_bytes()],
        [dummy_files["audio_bytes"], second_audio.read_bytes()]
    )
    assert final is not None
    assert isinstance(final, bytes)


def test_concatenate_empty_list():
    result = MergerFactory.concatenate_videos([])
    assert result is None


def test_merge_all_videos_with_audio_mismatched_lists(dummy_files):
    with pytest.raises(ValueError):
        MergerFactory.merge_all_videos_with_audio(
            [dummy_files["video_bytes"]],
            [dummy_files["audio_bytes"], dummy_files["audio_bytes"]]
        )
