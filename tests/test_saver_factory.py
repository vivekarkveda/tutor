import os
import pytest
from pathlib import Path
from saver_factory import SaverFactory


def test_save_final_video_local(tmp_path, monkeypatch):
    # Redirect BASE_OUTPUT_DIR to temp folder
    monkeypatch.setattr(SaverFactory, "BASE_OUTPUT_DIR", tmp_path)

    video_bytes = b"fake_video_data"
    filename = "test_video"

    output_path = SaverFactory.save_final_video(video_bytes, filename, save_to="local", db_credentials=None)

    # Ensure file exists and content matches
    saved_file = Path(output_path)
    assert saved_file.exists()
    assert saved_file.read_bytes() == video_bytes
    assert saved_file.suffix == ".mp4"


def test_save_final_video_local_with_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(SaverFactory, "BASE_OUTPUT_DIR", tmp_path)

    video_bytes = b"another_fake_video"
    filename = "video.mp4"

    output_path = SaverFactory.save_final_video(video_bytes, filename, save_to="local", db_credentials=None)
    saved_file = Path(output_path)

    assert saved_file.exists()
    assert saved_file.read_bytes() == video_bytes


def test_save_final_video_invalid_save_to(dummy_video_bytes=b"video"):
    with pytest.raises(ValueError, match="Unsupported save_to type"):
        SaverFactory.save_final_video(dummy_video_bytes, "file", save_to="cloud", db_credentials=None)


def test_save_final_video_postgres_missing_credentials():
    with pytest.raises(ValueError, match="No DB credentials provided"):
        SaverFactory.save_final_video(b"video", "file", save_to="postgres", db_credentials=None)


def test_save_final_video_postgres_mock(monkeypatch):
    """Mock psycopg2 connection to simulate DB insert."""

    class FakeCursor:
        def execute(self, *args, **kwargs):
            self.executed = True
        def close(self): pass

    class FakeConnection:
        def cursor(self): return FakeCursor()
        def commit(self): pass
        def close(self): pass

    def fake_connect(**kwargs):
        return FakeConnection()

    monkeypatch.setattr("saver_factory.psycopg2.connect", fake_connect)

    video_bytes = b"postgres_video_data"
    db_credentials = {
        "host": "localhost",
        "port": 5432,
        "user": "test_user",
        "password": "test_pass",
        "dbname": "test_db",
        "table": "videos_test"
    }

    result = SaverFactory.save_final_video(video_bytes, "test_pg", save_to="postgres", db_credentials=db_credentials)

    assert "postgres://" in result
    assert "videos_test/test_pg.mp4" in result
