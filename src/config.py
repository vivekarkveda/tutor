
from pathlib import Path

class Settings:
    RUN_FROM = "local" 
    GENERATE_NEW_FILES = False
    VIDEO_PROCESSOR = "manim"
    AUDIO_PROCESSOR = "kokoro"
    FILE_TYPES = ["py", "txt"]


    JSON_FILE_PATH = Path(r"D:\tests\script.json")


    POSTGRES = {
        "host": "localhost",
        "port": 5432,
        "user": "Mayank",
        "password": "yourpassword",
        "dbname": "my_database",
        "table": "videos",
    }

    SCRIPT_QUERY = "SELECT script_seq, script_for_manim, script_voice_over FROM scripts_table;"

    debugging = False
