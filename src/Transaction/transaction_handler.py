import json
import psycopg2
import psycopg2.extras
from datetime import datetime
import traceback
from config import Settings  # ✅ shared config for DB connection

psycopg2.extras.register_uuid()


class TransactionHandler:
    """Handles database operations for the transaction table with UPSERT (insert/update) support."""

    def __init__(self):
        self.db_config = Settings.POSTGRES
        self.conn = None
        self.cursor = None

    # ---------------- Connection Methods ----------------
    def connect_db(self):
        """Establish connection to PostgreSQL using config."""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                dbname=self.db_config["dbname"],
            )
            self.cursor = self.conn.cursor()
        except Exception as e:
            print("❌ Database connection failed:", str(e))
            traceback.print_exc()
            raise

    def close_db(self):
        """Safely close DB connection."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception as e:
            print("⚠️ Error closing DB connection:", e)

    # ---------------- Table Creation & Schema Healing ----------------
    def create_table_if_not_exists(self):
        """Ensure the transaction table exists and has all expected columns."""
        try:
            base_table_query = """
            CREATE TABLE IF NOT EXISTS transaction (
                transaction_id UUID PRIMARY KEY,
                topic TEXT,
                meta_prompt TEXT,
                cleaned_script JSON,
                script_gen_status TEXT,
                filegenration TEXT,
                code_gen TEXT,
                manim_output_status TEXT,
                script_written TEXT,
                merge_status TEXT,
                video_status TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP
            );
            """
            self.cursor.execute(base_table_query)
            self.conn.commit()

            # ✅ Auto-heal (for schema evolution)
            alter_queries = [
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS topic TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS meta_prompt TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS cleaned_script JSON;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS script_gen_status TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS filegenration TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS code_gen TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS manim_output_status TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS script_written TEXT;",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS merge_status TEXT;"
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS video_status TEXT;"
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",
                "ALTER TABLE transaction ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;"
            ]

            for q in alter_queries:
                self.cursor.execute(q)
            self.conn.commit()

        except Exception as e:
            print("❌ Error creating/updating transaction table:", str(e))
            traceback.print_exc()
            self.conn.rollback()
            raise

    # ---------------- UPSERT Logic ----------------
    def upsert_transaction(
        self,
        transaction_id: str,
        topic: str = None,
        meta_prompt: str = None,
        cleaned_script=None,
        script_gen_status=None,
        filegenration: str = None,
        code_gen: str = None,
        manim_output_status: str = None,
        script_written: str = None,
        merge_status: str =None,
        video_status: str = None,
    ):
        """Insert or update a transaction record safely (UPSERT)."""
        try:
            now = datetime.now()

            # Safely convert cleaned_script to JSON string
            json_data = (
                json.dumps(cleaned_script)
                if cleaned_script is not None and not isinstance(cleaned_script, str)
                else cleaned_script
            )

            # ✅ Correct UPSERT query
            query = """
                INSERT INTO transaction (
                    transaction_id, topic, meta_prompt, cleaned_script,script_gen_status,
                    filegenration, code_gen, manim_output_status, script_written,merge_status,video_status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s, %s)
                ON CONFLICT (transaction_id)
                DO UPDATE SET
                    topic = COALESCE(EXCLUDED.topic, transaction.topic),
                    meta_prompt = COALESCE(EXCLUDED.meta_prompt, transaction.meta_prompt),
                    cleaned_script = COALESCE(EXCLUDED.cleaned_script, transaction.cleaned_script),
                    script_gen_status = COALESCE(EXCLUDED.script_gen_status, transaction.script_gen_status),
                    filegenration = COALESCE(EXCLUDED.filegenration, transaction.filegenration),
                    code_gen = COALESCE(EXCLUDED.code_gen, transaction.code_gen),
                    manim_output_status = COALESCE(EXCLUDED.manim_output_status, transaction.manim_output_status),
                    script_written = COALESCE(EXCLUDED.script_written, transaction.script_written),
                    merge_status = COALESCE(EXCLUDED.merge_status, transaction.merge_status),
                    video_status = COALESCE(EXCLUDED.video_status, transaction.video_status),
                    updated_at = EXCLUDED.updated_at;
            """

            self.cursor.execute(
                query,
                (
                    transaction_id,
                    topic,
                    meta_prompt,
                    json_data,
                    script_gen_status,
                    filegenration,
                    code_gen,
                    manim_output_status,
                    script_written,
                    merge_status,
                    video_status,
                    now,
                    now,
                ),
            )
            self.conn.commit()
            print(f"✅ Transaction upserted successfully: {transaction_id}")

        except Exception as e:
            print(f"❌ Error upserting transaction {transaction_id}: {e}")
            traceback.print_exc()
            self.conn.rollback()
            raise


# ---------------- Helper Wrapper ----------------
def transaction(
    transaction_id: str,
    topic: str = None,
    meta_prompt: str = None,
    cleaned_script=None,
    script_gen_status = None,
    filegenration: str = None,
    code_gen: str = None,
    manim_output_status: str = None,
    script_written: str = None,
    merge_status :str = None,
    video_status :str =None,
):
    """
    Flexible one-line transaction logger:
      - Inserts if not exists, updates if already present.
      - Automatically heals missing columns if schema changes.

    Examples:
      transaction(unique_id, topic="Math", meta_prompt="Algebra lesson for class 8")
      transaction(unique_id, cleaned_script=cleaned_json)
      transaction(unique_id, filegenration="Files generated successfully")
      transaction(unique_id, code_gen="Code created successfully")
      transaction(unique_id, script_written="Scripts written successfully")
    """
    handler = TransactionHandler()
    try:
        handler.connect_db()
        handler.create_table_if_not_exists()
        handler.upsert_transaction(
            transaction_id, topic, meta_prompt, cleaned_script,script_gen_status, filegenration, code_gen, manim_output_status, script_written,merge_status,video_status
        )
    except Exception as e:
        print(f"❌ Failed to log transaction {transaction_id}: {e}")
        traceback.print_exc()
    finally:
        handler.close_db()