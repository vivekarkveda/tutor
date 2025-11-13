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
    """Handles reading Manim-generated script data and inserting it into PostgreSQL."""

    def __init__(self, json_base, manim_base, db_config, unique_id):
        self.json_base = json_base
        self.manim_base = manim_base
        self.db_config = db_config
        self.unique_id = unique_id
        self.conn = None
        self.cursor = None
        self.batch_id = uuid.uuid4()
        self.current_time = datetime.now()

    # ---------------- Utility Methods ----------------
    def get_latest_folder(self, base_path: str) -> str:
        """Finds the most recently modified subfolder inside base_path."""
        print(f"🔍 Searching latest folder in: {base_path}")

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
        print(f"✅ Latest folder found: {latest_path}")
        return latest_path

    def find_all_script_folders(self, base_path: str):
        """Finds all folders starting with 'script_seq' under base_path."""
        print(f"🔍 Scanning for script_seq folders inside: {base_path}")
        script_folders = []
        for root, dirs, files in os.walk(base_path):
            for d in dirs:
                if d.startswith("script_seq"):
                    full_path = os.path.join(root, d)
                    script_folders.append(full_path)
        if not script_folders:
            raise FileNotFoundError(f"No script_seq folders found under {base_path}")
        print(f"✅ Found {len(script_folders)} script folders.")
        return script_folders

    # ---------------- File Handling ----------------
    def load_files(self):
        """Loads the latest JSON and corresponding .py/.txt scripts."""
        print("📂 Loading JSON and script files ...")

        json_folder = self.get_latest_folder(self.json_base)
        manim_folder = self.get_latest_folder(self.manim_base)

        # ✅ Find JSON file dynamically
        json_files = [f for f in os.listdir(json_folder) if f.endswith(".json")]
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {json_folder}")
        json_file = os.path.join(json_folder, json_files[0])
        print(f"✅ Found JSON file: {json_file}")

        # ✅ Find all script folders
        script_folders = self.find_all_script_folders(manim_folder)

        # ✅ Load JSON content
        with open(json_file, "r", encoding="utf-8") as f:
            scripts = json.load(f)

        code_data = {}
        narration_data = {}

        for folder in script_folders:
            seq_name = os.path.basename(folder)
            py_path = os.path.join(folder, f"{seq_name}.py")
            txt_path = os.path.join(folder, f"{seq_name}.txt")

            code_data[seq_name] = (
                open(py_path, "r", encoding="utf-8").read()
                if os.path.exists(py_path)
                else ""
            )
            narration_data[seq_name] = (
                open(txt_path, "r", encoding="utf-8").read()
                if os.path.exists(txt_path)
                else ""
            )

        folder_name = "input_data_" + os.path.basename(json_folder)

        print("✅ Files loaded successfully.")
        return {
            "scripts": scripts,
            "codes": code_data,
            "narrations": narration_data,
            "folder_name": folder_name,
        }

    # ---------------- Database Methods ----------------
    def connect_db(self):
        print("🔗 Connecting to PostgreSQL ...")
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        print("✅ Database connected successfully.")

    def create_table(self):
        print("🧱 Ensuring 'script_store' table exists ...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS script_store (
            id UUID NOT NULL,
            Transaction_id TEXT,
            time TIMESTAMP DEFAULT NOW(),
            folder_name TEXT,
            scripts JSONB,
            sequence TEXT,
            code TEXT,
            narration JSONB
        );
        """
        self.cursor.execute(create_table_query)
        self.conn.commit()
        print("✅ Table ready for inserts.")

    def insert_data(self, data):
        print("💾 Inserting data into PostgreSQL ...")

        scripts = data["scripts"]
        codes = data["codes"]
        narrations = data["narrations"]
        folder_name = data["folder_name"]

        for entry in scripts:
            seq_num = entry.get("script_seq")
            seq_label = f"script_seq{seq_num}"

            code_data = codes.get(seq_label, "")
            narration_data = narrations.get(seq_label, "")

            self.cursor.execute("""
                INSERT INTO script_store (id, Transaction_id, time, folder_name, scripts, sequence, code, narration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(self.batch_id),
                str(self.unique_id),
                self.current_time,
                folder_name,
                json.dumps(entry),
                seq_label,
                code_data,
                json.dumps(narration_data),
            ))

        self.conn.commit()
        print(f"✅ Data inserted successfully for batch ID = {self.batch_id}")

    def close_db(self):
        print("🔒 Closing database connection ...")
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Connection closed.")


# ---------------- Main Execution ----------------
def run_script_data_process(unique_id):
    """Main function to run the complete data extraction and DB insertion pipeline."""
    db_config = {
        "dbname": "airlines_flights_data",
        "user": "vivek",
        "password": "8811",
        "host": "localhost",
        "port": "5432"
    }

    try:
        print("\n🚀 Starting Script Data Pipeline...\n")

        handler = ScriptDataHandler(
            json_base=Settings.TEMP_GENERATED_FOLDER,
            manim_base=Settings.TEMP_GENERATED_FOLDER,
            db_config=db_config,
            unique_id=unique_id
        )

        handler.connect_db()
        handler.create_table()
        data = handler.load_files()
        handler.insert_data(data)
        handler.close_db()

        print("\n✅ Pipeline completed successfully.\n")

    except Exception as e:
        print("\n❌ ERROR OCCURRED:")
        print(str(e))
        traceback.print_exc()


# ---------------- Run Script ----------------
if __name__ == "__main__":
    run_script_data_process(unique_id=str(uuid.uuid4()))
