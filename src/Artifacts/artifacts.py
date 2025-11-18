import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid
import traceback
from config import Settings

psycopg2.extras.register_uuid()
class ScriptDataHandler:
    """Handles reading Manim-generated script data and inserting/updating PostgreSQL."""
    def __init__(self, json_base, manim_base, db_config, unique_id):
        self.json_base = json_base
        self.manim_base = manim_base
        self.db_config = db_config
        self.unique_id = unique_id    # USED FOR UPSERT
        self.conn = None
        self.cursor = None
        self.current_time = datetime.now()
    # ---------------- Utility Methods ----------------
    def get_latest_folder(self, base_path: str) -> str:
        print(f":mag: Searching latest folder in: {base_path}")
        folders = [
            f for f in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, f))
        ]
        if not folders:
            raise FileNotFoundError(f"No folders found in {base_path}")
        latest = max(
            folders,
            key=lambda x: os.path.getmtime(os.path.join(base_path, x))
        )
        latest_path = os.path.join(base_path, latest)
        print(f":white_check_mark: Latest folder found: {latest_path}")
        return latest_path
    def find_all_script_folders(self, base_path: str):
        print(f":mag: Scanning for script_seq folders inside: {base_path}")
        script_folders = []
        for root, dirs, files in os.walk(base_path):
            for d in dirs:
                if d.startswith("script_seq"):
                    full_path = os.path.join(root, d)
                    script_folders.append(full_path)
        if not script_folders:
            raise FileNotFoundError(f"No script_seq folders found under {base_path}")
        print(f":white_check_mark: Found {len(script_folders)} script folders.")
        return sorted(script_folders)
    def load_final_prompts(self):
        # PRIMARY (original) logic
        final_prompt_folder = os.path.join(self.manim_base, "final_prompt")
        print(f":mag: Loading final prompts from: {final_prompt_folder}")
        # fallback to your actual final_prompt path
        if not os.path.exists(final_prompt_folder):
            print(":warning: final_prompt not inside manim_base. Switching to actual folder.")
            final_prompt_folder = r"C:\Vivek_Main\feature_vivek\tutor\src\final_prompt"
            print(f":arrows_counterclockwise: Fallback path: {final_prompt_folder}")
        if not os.path.exists(final_prompt_folder):
            print(":x: Final prompt folder STILL missing. Returning empty.")
            return {}
        final_prompts = {}
        for file in os.listdir(final_prompt_folder):
            if file.endswith(".txt"):
                number = file.split("_")[-1].replace(".txt", "").strip()
                seq_name = f"script_seq{number}"
                file_path = os.path.join(final_prompt_folder, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    final_prompts[seq_name] = f.read()
        print(f":white_check_mark: Loaded {len(final_prompts)} final prompts.")
        return final_prompts
    # ---------------- File Handling ----------------
    def load_files(self):
        print(":open_file_folder: Loading JSON and script files ...")
        json_folder = self.get_latest_folder(self.json_base)
        manim_folder = self.get_latest_folder(self.manim_base)
        # Find latest JSON file
        json_files = [f for f in os.listdir(json_folder) if f.endswith(".json")]
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {json_folder}")
        json_file = os.path.join(json_folder, json_files[0])
        print(f":white_check_mark: Using JSON file: {json_file}")
        # Load JSON
        with open(json_file, "r", encoding="utf-8") as f:
            scripts = json.load(f)
        # Load script folders
        script_folders = self.find_all_script_folders(manim_folder)
        code_data = {}
        narration_data = {}
        for folder in script_folders:
            seq_name = os.path.basename(folder)
            py_path = os.path.join(folder, f"{seq_name}.py")
            txt_path = os.path.join(folder, f"{seq_name}.txt")
            code_data[seq_name] = open(py_path, "r", encoding="utf-8").read() if os.path.exists(py_path) else ""
            narration_data[seq_name] = open(txt_path, "r", encoding="utf-8").read() if os.path.exists(txt_path) else ""
        folder_name = "input_data_" + os.path.basename(json_folder)
        print(":white_check_mark: Files loaded successfully.")
        return {
            "scripts": scripts,
            "codes": code_data,
            "narrations": narration_data,
            "final_prompts": self.load_final_prompts(),
            "folder_name": folder_name,
        }
    # ---------------- Database Methods ----------------
    def connect_db(self):
        print(":link: Connecting to PostgreSQL ...")
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        print(":white_check_mark: Database connected successfully.")
    def create_table(self):
        print(":bricks: Ensuring 'script_store' table exists ...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS script_store (
            id UUID NOT NULL,
            Transaction_id TEXT,
            time TIMESTAMP DEFAULT NOW(),
            folder_name TEXT,
            scripts JSONB,
            sequence TEXT,
            code TEXT,
            narration JSONB,
            CONSTRAINT unique_transaction_sequence UNIQUE (Transaction_id, sequence)
        );
        """
        self.cursor.execute(create_table_query)
        self.conn.commit()
        self.cursor.execute("""
            ALTER TABLE script_store
            ADD COLUMN IF NOT EXISTS final_prompt TEXT;
        """)
        self.conn.commit()
        print(":white_check_mark: Table ready (with unique constraint).")
    def insert_or_update(self, data):
        print(":floppy_disk: Processing data (INSERT or UPDATE with UPSERT)...")
        scripts = data["scripts"]
        codes = data["codes"]
        narrations = data["narrations"]
        final_prompts = data["final_prompts"]
        folder_name = data["folder_name"]
        for entry in scripts:
            seq_num = entry.get("script_seq")
            seq_label = f"script_seq{seq_num}"
            final_prompt_clean = final_prompts.get(seq_label, "")
            final_prompt_clean = final_prompt_clean.encode("utf-8", "replace").decode("utf-8")
            code_data = codes.get(seq_label, "")
            narration_data = narrations.get(seq_label, "")
            new_row_id = str(uuid.uuid4())  # New ID only for INSERT
            query = """
                INSERT INTO script_store
                    (id, Transaction_id, time, folder_name, scripts, sequence, code, narration,final_prompt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)
                ON CONFLICT (Transaction_id, sequence)
                DO UPDATE SET
                    time = EXCLUDED.time,
                    folder_name = EXCLUDED.folder_name,
                    scripts = EXCLUDED.scripts,
                    code = EXCLUDED.code,
                    narration = EXCLUDED.narration,
                    final_prompt = EXCLUDED.final_prompt;
            """
            self.cursor.execute(query, (
                new_row_id,
                str(self.unique_id),
                self.current_time,
                folder_name,
                json.dumps(entry),
                seq_label,
                code_data,
                json.dumps(narration_data),
                final_prompt_clean
            ))
            print(f":heavy_check_mark: Processed {seq_label} (insert/update).")
        self.conn.commit()
        print(":white_check_mark: All sequences processed successfully.")
    def close_db(self):
        print(":lock: Closing database connection ...")
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print(":white_check_mark: Connection closed.")
# ---------------- Main Execution ----------------
def run_script_data_process(unique_id):
    db_config = {
        "dbname": "airlines_flights_data",
        "user": "vivek",
        "password": "8811",
        "host": "localhost",
        "port": "5432"
    }
    try:
        print("\n:rocket: Starting Script Data Pipeline...\n")
        handler = ScriptDataHandler(
            json_base=Settings.TEMP_GENERATED_FOLDER,
            manim_base=Settings.TEMP_GENERATED_FOLDER,
            db_config=db_config,
            unique_id=unique_id   # <<< IMPORTANT
        )
        handler.connect_db()
        handler.create_table()
        data = handler.load_files()
        handler.insert_or_update(data)
        handler.close_db()
        print("\n:white_check_mark: Pipeline completed successfully.\n")
    except Exception as e:
        print("\n:x: ERROR OCCURRED:")
        print(str(e))
        traceback.print_exc()
# ---------------- Run Script ----------------
if __name__ == "__main__":
    # Pass the Transaction_id for update or create new for insert
    run_script_data_process(unique_id=str(uuid.uuid4()))