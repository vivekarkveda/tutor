
from pathlib import Path

class Settings:
    RUN_FROM = "local" 
    GENERATE_NEW_FILES = False
    VIDEO_PROCESSOR = "manim"
    AUDIO_PROCESSOR = "kokoro"
    FILE_TYPES = ["py", "txt"]


    JSON_FILE_PATH = Path(r"C:\Vivek_Main\Manim_project\jsonfiles\script1.json")
    TEMP_GENERATED_FOLDER = Path(r"C:\Vivek_Main\Temp_Data")


    POSTGRES = {
        "host": "localhost",
        "port": 5432,
        "user": "vivek",
        "password": "8811",
        "dbname": "airlines_flights_data",
        "table": "videos",
    }

    SCRIPT_QUERY = "SELECT script_seq, script_for_manim, script_voice_over FROM scripts_table;"

    debugging = False
    COHERE_API_KEY = "ItjCVeX2H4je76T4Az0yQGnjISqZhD3IrKWj6ebq"
    BASE_INPUT_ROOT = "C:\Vivek_Main\Manim_project\inputbox"
    IP_ADDRESS= "http://127.0.0.1:8000"

    API_KEY="ItjCVeX2H4je76T4Az0yQGnjISqZhD3IrKWj6ebq"
