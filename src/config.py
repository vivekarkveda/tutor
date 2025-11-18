
from pathlib import Path

class Settings:
    RUN_FROM = "local" 
    GENERATE_NEW_FILES = False
    VIDEO_PROCESSOR = "manim"
    AUDIO_PROCESSOR = "kokoro"
    FILE_TYPES = ["py", "txt"]


    JSON_FILE_PATH = Path(r"C:\Vivek_Main\Manim_project\jsonfiles\script1.json")
    TEMP_GENERATED_FOLDER = Path(r"C:\Vivek_Main\Temp_Data")
    TEST_JSON_PROMPT_PATH = Path(r"C:\Vivek_Main\feature_vivek\tutor\src\Prompt\test_json.txt")
    TEST_JSON_PROMPT_PATH_2 = Path(r"C:\Vivek_Main\feature_vivek\tutor\src\Prompt\test_json_2.txt")
    TEST_MANIM_PROMPT_PATH = Path(r"C:\Vivek_Main\feature_vivek\tutor\src\Prompt\test_manim.txt")
    TEST_MANIM_PROMPT_PATH_2 = Path(r"C:\Vivek_Main\feature_vivek\tutor\src\Prompt\test_manim_2.txt")
    JSON_PROMPT_PATH = Path(r"C:\Vivek_Main\Malay\tutor\src\Prompt\Prompt_Template1.txt")
    MANIM_CODE_PROMPT_PATH = Path(r"C:\Vivek_Main\Malay\tutor\src\Prompt\Prompt_Template2.txt")



    # === New default timing parameters ===
    DEFAULT_SCENE_DURATION_RANGE = " 30 seconds"
    DEFAULT_TOTAL_VIDEO_LENGTH_TARGET = "1 minutes"


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
    COHERE_API_KEY = "dZfHrqzrU2lw32MX2RPRiG8ARSKqavpiqpLsU2b0"
    BASE_INPUT_ROOT = "C:\Vivek_Main\Manim_project\inputbox"
    IP_ADDRESS= "http://127.0.0.1:8000"

    API_KEY="dZfHrqzrU2lw32MX2RPRiG8ARSKqavpiqpLsU2b0"

    # 🧠 Google Drive Configuration
    DRIVE_AUTH_MODE = "service"  # "token" for OAuth, "service" for service account
    DRIVE_CREDENTIALS_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\credentials\client_secret_584093952937-sfvfijr3u9n9r4rnqi88utngpm77q739.apps.googleusercontent.com.json")
    SERVICE_ACCOUNT_PATH = Path(r"C:\Vivek_Main\feature_vivek\tutor\src\credentials\gv4ex001-f1a212036ab2.json")
    TOKEN_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\credentials\token.json")  # auto-generated & reused
    DRIVE_FOLDER_ID = "1fSIa3LHaUZ6ElWywNuyHRnyj1ohr_gjj"
