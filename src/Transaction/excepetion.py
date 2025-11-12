import json
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid
import traceback
from config import Settings  # ✅ shared config for DB connection

psycopg2.extras.register_uuid()


class ExceptionHandler:
    """Handles database operations for the exception_store table with UPSERT (insert/update) support."""

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

    # ---------------- Table Creation ----------------
    def create_table_if_not_exists(self):
        """Ensure the exception_store table exists and has all expected columns."""
        try:
            base_table_query = """
            CREATE TABLE IF NOT EXISTS exception_store (
                exception_id UUID PRIMARY KEY,
                transaction_id TEXT,
                script_gen_status TEXT,
                filegenration TEXT,
                code_gen TEXT,
                script_written TEXT,
                merge_status TEXT,
                video_status TEXT,
                exception_message TEXT,
                traceback TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP
            );
            """
            self.cursor.execute(base_table_query)
            self.conn.commit()

            # ✅ Auto-heal (schema evolution)
            alter_queries = [
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS transaction_id TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS script_gen_status TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS filegenration TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS code_gen TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS script_written TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS merge_status TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS video_status TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS exception_message TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS traceback TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;"
            ]

            for q in alter_queries:
                self.cursor.execute(q)
            self.conn.commit()

        except Exception as e:
            print("❌ Error creating/updating exception_store table:", str(e))
            traceback.print_exc()
            self.conn.rollback()
            raise

    # ---------------- UPSERT Logic ----------------
    def upsert_exception(
        self,
        transaction_id: str,
        script_gen_status: str = None,
        filegenration: str = None,
        code_gen: str = None,
        script_written: str = None,
        merge_status: str = None,
        video_status: str = None,
        exception_message: str = None,
        trace: str = None,
    ):
        """Insert or update an exception record safely (UPSERT)."""
        try:
            exception_id = uuid.uuid4()
            now = datetime.now()

            query = """
                INSERT INTO exception_store (
                    exception_id, transaction_id, script_gen_status,
                    filegenration, code_gen, script_written, merge_status, video_status,
                    exception_message, traceback, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exception_id)
                DO UPDATE SET
                    script_gen_status = COALESCE(EXCLUDED.script_gen_status, exception_store.script_gen_status),
                    filegenration = COALESCE(EXCLUDED.filegenration, exception_store.filegenration),
                    code_gen = COALESCE(EXCLUDED.code_gen, exception_store.code_gen),
                    script_written = COALESCE(EXCLUDED.script_written, exception_store.script_written),
                    merge_status = COALESCE(EXCLUDED.merge_status, exception_store.merge_status),
                    video_status = COALESCE(EXCLUDED.video_status, exception_store.video_status),
                    exception_message = COALESCE(EXCLUDED.exception_message, exception_store.exception_message),
                    traceback = COALESCE(EXCLUDED.traceback, exception_store.traceback),
                    updated_at = EXCLUDED.updated_at;
            """

            self.cursor.execute(
                query,
                (
                    exception_id,
                    transaction_id,
                    script_gen_status,
                    filegenration,
                    code_gen,
                    script_written,
                    merge_status,
                    video_status,
                    exception_message,
                    trace,
                    now,
                    now,
                ),
            )
            self.conn.commit()
            print(f"⚠️ Exception logged for transaction {transaction_id} (Exception ID: {exception_id})")

        except Exception as e:
            print(f"❌ Error inserting exception for {transaction_id}: {e}")
            traceback.print_exc()
            self.conn.rollback()
            raise


# ---------------- Helper Wrapper ----------------
def exception(
    transaction_id: str,
    script_gen_status: str = None,
    filegenration: str = None,
    code_gen: str = None,
    script_written: str = None,
    merge_status: str = None,
    video_status: str = None,
    exception_message: str = None,
    trace: str = None,
):
    """Flexible one-line exception logger."""
    handler = ExceptionHandler()
    try:
        handler.connect_db()
        handler.create_table_if_not_exists()
        handler.upsert_exception(
            transaction_id,
            script_gen_status,
            filegenration,
            code_gen,
            script_written,
            merge_status,
            video_status,
            exception_message,
            trace,
        )
    except Exception as e:
        print(f"❌ Failed to log exception for transaction {transaction_id}: {e}")
        traceback.print_exc()
    finally:
        handler.close_db()
