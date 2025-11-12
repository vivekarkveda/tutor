from pathlib import Path

class Settings:
    RUN_FROM = "local" 
    GENERATE_NEW_FILES = False
    VIDEO_PROCESSOR = "manim"
    AUDIO_PROCESSOR = "kokoro"
    FILE_TYPES = ["py", "txt"]


    JSON_FILE_PATH = Path(r"C:\ArkMalay\Framework\json_file")
    TEMP_GENERATED_FOLDER = Path(r"C:\ArkMalay\Framework\Temp")

    LOCAL_VIDEO_DIR = Path(r"C:\ArkMalay\Framework\tutor\output\Videos")
    LOCAL_AUDIO_DIR = Path(r"C:\ArkMalay\Framework\tutor\output\Audios")

    VIDEO_DATA_PATH = Path(r"C:\ArkMalay\Framework\Video_data")

    BASE_INPUT_PATH = Path(r"C:\ArkMalay\Framework\Video_data")  # adjust as needed
    TRANSACTION_FOLDER = None  # initialize globally


    #Test prompt Paths
    TEST_JSON_PROMPT_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\Prompt\test_json.txt")
    TEST_MANIM_PROMPT_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\Prompt\test_manim.txt")


    # === New default timing parameters ===
    DEFAULT_SCENE_DURATION_RANGE = " 30 seconds"
    DEFAULT_TOTAL_VIDEO_LENGTH_TARGET = "1 minutes"

    @classmethod
    def set_transaction_folder(cls, path: Path):
        cls.TRANSACTION_FOLDER = str(path)
        print(f"[Settings] TRANSACTION_FOLDER set to → {cls.TRANSACTION_FOLDER}")

    @classmethod
    def clear_transaction_folder(cls):
        print(f"[Settings] TRANSACTION_FOLDER cleared (was {cls.TRANSACTION_FOLDER})")
        cls.TRANSACTION_FOLDER = None





    POSTGRES = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "malayraj11",
        "dbname": "a_v_data",
        "table": "videos",
    }

    SCRIPT_QUERY = "SELECT script_seq, script_for_manim, script_voice_over FROM scripts_table;"

    debugging = False
    
    IP_ADDRESS= "http://127.0.0.1:8000"


    COHERE_API_KEY = "ClKSBvEQCHw9PJF6RezdGEasYMMwjZuv2U96GSO1"
    API_KEY="ClKSBvEQCHw9PJF6RezdGEasYMMwjZuv2U96GSO1"
    JSON_PROMPT_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\Prompt\test_json.txt")
    MANIM_CODE_PROMPT_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\Prompt\test_manim.txt")

# 🧠 Google Drive Configuration
    DRIVE_AUTH_MODE = "service"  # "token" for OAuth, "service" for service account
    DRIVE_CREDENTIALS_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\credentials\client_secret_584093952937-sfvfijr3u9n9r4rnqi88utngpm77q739.apps.googleusercontent.com.json")
    SERVICE_ACCOUNT_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\credentials\gv4ex001-f1a212036ab2.json")
    TOKEN_PATH = Path(r"C:\ArkMalay\Framework\tutor\src\credentials\token.json")  # auto-generated & reused
    DRIVE_FOLDER_ID = "1fSIa3LHaUZ6ElWywNuyHRnyj1ohr_gjj"