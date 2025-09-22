tutter/
│── src/
│   ├── main.py                 # Main pipeline entry
│   ├── config.py               # Configuration settings
│   ├── file_fetcher_factory.py # File fetching logic
│   ├── saver_factory.py        # Save output locally or in Postgres
│   ├── merger_factory.py       # Merge video + audio
│   └── parsers/
│       └── base_handler.py     # Input handlers (JSON, Postgres)
│
│── tests/
    |-- test_base_handle.py
    |-- test_file_fetcher_factory.py 
    |-- test_merger_factory.py
    |-- test_saver_factory.py                   # Unit tests
│── pyproject.toml              # Poetry project file
│── README.md                   # This file


install the poetry   
commnad  poetry install --no-root

in the config file i have the lots of the varible jse tile 
    RUN_FROM = set the flow with local and postgres
    GENERATE_NEW_FILES = this is for to fetch the json aor false to use the exixting file
    VIDEO_PROCESSOR = "manim" (if usin the othe libray for video generation)
    AUDIO_PROCESSOR = "tts"(this is use to genrate the audio)
    FILE_TYPES = ["py", "txt"] (here i can se the file type to buid by usin the json file)


    JSON_FILE_PATH = Path(r"C:\Vivek_Main\Manim_project\jsonfiles\Pythagoras.json")  (this is the path where json file is store if we are sung local)

   this is the postgres credintials
    POSTGRES = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "your_password",
        "dbname": "your_db",
        "table": "videos",
    }

    its the script of the postgres query to select the json file

    SCRIPT_QUERY = "SELECT script_seq, script_for_manim, script_voice_over FROM scripts_table;"


in the base handler i have this fution which handles the if else statement 
get_input_handler
for local and the postgres

this also have the two more fution for 
JsonHandler and the _generate_files
this two file genrerate the folder using the json file

file fetcher this is ues to fetch the folder develop by json this folder have the py and txt file rightnow
get_latest_files






    




set the path of the  BASE_INPUT_PATH in the base_handler to get the folder builfd by using the json file
----------------------------------------------------------------------------------------------------------------------


📂 Project Structure – tutter
tutter/
│── src/
│   ├── main.py                 # Main pipeline entry point
│   ├── config.py               # Centralized configuration settings
│   ├── file_fetcher_factory.py # Fetch latest generated files (py/txt)
│   ├── saver_factory.py        # Save outputs (local or Postgres)
│   ├── merger_factory.py       # Merge video & audio into final output
|   |--processor/
|   |  |--Manim/
|   |  |  |--video_factory.py
|   |  |--Pyttsx
|   |     |----audio_factory.py
│   └── parsers/
│       └── base_handler.py     # Input handlers (Local JSON / Postgres)
│
│── tests/
│   ├── test_base_handler.py
│   ├── test_file_fetcher_factory.py
│   ├── test_merger_factory.py
│   ├── test_saver_factory.py   # Unit tests
│
│── pyproject.toml              # Poetry project file
│── README.md                   # Documentation

⚙️ Setup

Install dependencies using Poetry:

poetry install --no-root


Run tests:

poetry run pytest


--------------------------------------------------------

🔧 Configuration (src/config.py)

All runtime behavior is controlled via environment-like variables inside config.py.

Core Settings

RUN_FROM – Select input source:

"local" → Use local JSON file

"postgres" → Use database scripts

GENERATE_NEW_FILES – Control file generation:

True → Fetch/generate new files from JSON

False → Use existing files

VIDEO_PROCESSOR – Video generation engine

"manim" (default) or custom video processor

AUDIO_PROCESSOR – Audio generation engine

"tts" (default, text-to-speech)

FILE_TYPES – File types to generate from JSON

FILE_TYPES = ["py", "txt"]

Input Sources

Local JSON File

JSON_FILE_PATH = Path(
    r"C:\Vivek_Main\Manim_project\jsonfiles\Pythagoras.json"
)


Postgres Credentials

POSTGRES = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "your_password",
    "dbname": "your_db",
    "table": "videos",
}


Postgres Script Query

SELECT script_seq, script_for_manim, script_voice_over
FROM scripts_table;

-----------------------------------------------------------------------


🧩 Parsers (src/parsers/base_handler.py)

get_input_handler() – Chooses the input source (local JSON or Postgres).

JsonHandler – Loads JSON and prepares file generation.

_generate_files() – Builds project folders and files (.py, .txt) based on JSON contents.


-----------------------------------------------------------------------------------------


📂 File Fetcher (src/file_fetcher_factory.py)

Responsible for retrieving the latest generated folder built from JSON.

get_latest_files() → Returns .py and .txt files inside the generated folder.

Uses BASE_INPUT_PATH (set in base_handler.py) to locate generated folders.

-----------------------------------------------------------------------------------------------


🎬 Pipeline Flow (src/main.py)

Input Handler → Choose source (local JSON / Postgres)

File Generator → Build .py + .txt files

File Fetcher → Get the latest generated files

Video Processor → Generate video (manim by default)

Audio Processor → Generate audio (tts by default)

Merger → Merge video + audio

Saver → Save output (local or Postgres)+5

------------------------------------------------------------------------------------------------
