import json
import pytest
from pathlib import Path
from parsers.base_handler import JsonHandler, PostgresHandler, InputHandlerFactory


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a temporary JSON file for JsonHandler testing."""
    data = [
        {"script_seq": 1, "script_for_manim": "Scene A", "script_voice_over": "Voice A"},
        {"script_seq": 2, "script_for_manim": "Scene B", "script_voice_over": "Voice B"},
    ]
    json_file = tmp_path / "input.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return json_file, data


def test_json_handler_handle(monkeypatch, sample_json_file):
    json_file, expected_data = sample_json_file
    handler = JsonHandler()

    # Fake _generate_files
    called_args = {}
    def fake_generate_files(data, base_name, file_types):
        called_args["data"] = data
        called_args["base_name"] = base_name
        called_args["file_types"] = file_types
        return {"mock": "result"}

    monkeypatch.setattr(handler, "_generate_files", fake_generate_files)

    result = handler.handle(str(json_file), file_types=["py", "txt"])
    assert result == {"mock": "result"}
    assert called_args["data"] == expected_data
    assert called_args["base_name"] == Path(json_file).stem
    assert called_args["file_types"] == ["py", "txt"]


def test_postgres_handler_handle(monkeypatch, tmp_path):
    handler = PostgresHandler()
    handler.set_credentials({
        "host": "localhost",
        "port": 5432,
        "user": "test",
        "password": "test",
        "dbname": "testdb"
    })

    # Mock psycopg2 connection + cursor
    class FakeCursor:
        description = [("script_seq",), ("script_for_manim",), ("script_voice_over",)]
        def execute(self, query): pass
        def fetchall(self):
            return [(1, "Scene X", "Voice X")]
        def close(self): pass

    class FakeConn:
        def cursor(self): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr("parsers.base_handler.psycopg2.connect", lambda **kwargs: FakeConn())

    # Fake _generate_files
    monkeypatch.setattr(handler, "_generate_files", lambda data, base, file_types: {"data": data})

    result = handler.handle("SELECT * FROM scripts;", file_types=["py"])
    assert "data" in result
    assert result["data"][0]["script_seq"] == 1
    assert result["data"][0]["script_for_manim"] == "Scene X"
    assert result["data"][0]["script_voice_over"] == "Voice X"


def test_factory_returns_correct_handler():
    local_handler = InputHandlerFactory.get_input_handler("local")
    postgres_handler = InputHandlerFactory.get_input_handler("postgres")
    assert isinstance(local_handler, JsonHandler)
    assert isinstance(postgres_handler, PostgresHandler)

    with pytest.raises(ValueError):
        InputHandlerFactory.get_input_handler("invalid")


def test_generate_files_creates_files(tmp_path, monkeypatch):
    handler = JsonHandler()
    handler.BASE_INPUT_PATH = tmp_path  # redirect output to tmp

    data = [
        {"script_seq": 1, "script_for_manim": "Code1", "script_voice_over": "Voice1"},
        {"script_seq": 2, "script_for_manim": "Code2", "script_voice_over": "Voice2"},
    ]

    result = handler._generate_files(data, "testcase", ["py", "txt"])
    # Verify structure
    assert "py_files" in result and "txt_files" in result
    assert len(result["py_files"]) == 2
    assert len(result["txt_files"]) == 2

    # Verify files actually created
    for file_list in result.values():
        for file_path in file_list:
            assert Path(file_path).exists()
            assert Path(file_path).read_text(encoding="utf-8")
