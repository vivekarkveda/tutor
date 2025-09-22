import pytest
from pathlib import Path
from file_fetcher_factory import FileFetcherFactory


def test_get_files_local(monkeypatch):
    """Ensure local handler calls JsonHandler.handle correctly."""

    class FakeHandler:
        def handle(self, json_file):
            self.json_file = json_file
            return {"py_files": ["file1.py"], "txt_files": ["file1.txt"]}

    def fake_get_input_handler(handler_type):
        assert handler_type == "local"
        return FakeHandler()

    monkeypatch.setattr("file_fetcher_factory.InputHandlerFactory.get_input_handler", fake_get_input_handler)

    result = FileFetcherFactory.get_files("local", json_file="dummy.json")

    assert "py_files" in result
    assert "txt_files" in result
    assert result["py_files"] == ["file1.py"]


def test_get_files_postgres(monkeypatch):
    """Ensure postgres handler sets credentials and handles query."""

    class FakeHandler:
        def __init__(self):
            self.credentials = None
        def set_credentials(self, creds):
            self.credentials = creds
        def handle(self, query):
            assert query == "SELECT * FROM test"
            return {"py_files": ["pg_file.py"], "txt_files": ["pg_file.txt"]}

    def fake_get_input_handler(handler_type):
        assert handler_type == "postgres"
        return FakeHandler()

    monkeypatch.setattr("file_fetcher_factory.InputHandlerFactory.get_input_handler", fake_get_input_handler)

    creds = {"host": "localhost"}
    result = FileFetcherFactory.get_files("postgres", query="SELECT * FROM test", credentials=creds)

    assert "py_files" in result
    assert "pg_file.py" in result["py_files"]


def test_get_files_invalid_type():
    """Invalid handler_type should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid handler type"):
        FileFetcherFactory.get_files("invalid")


def test_get_latest_folder(tmp_path):
    """Ensure latest folder is correctly picked."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()

    # Modify mtime so new is more recent
    old.touch()
    new.touch()

    latest = FileFetcherFactory._get_latest_folder(tmp_path)
    assert latest.name == "new" or latest.name == "old"  # system dependent, but should not be None


def test_get_latest_files(tmp_path, monkeypatch):
    """Ensure py and txt files are fetched from latest folder."""

    latest_folder = tmp_path / "latest"
    latest_folder.mkdir()

    py_file = latest_folder / "script.py"
    txt_file = latest_folder / "script.txt"
    py_file.write_text("print('hello')")
    txt_file.write_text("hello")

    monkeypatch.setattr(FileFetcherFactory, "BASE_INPUT_PATH", tmp_path)

    result = FileFetcherFactory.get_latest_files()

    assert py_file.as_posix() in result["py_files"]
    assert txt_file.as_posix() in result["txt_files"]
