import json
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid
import traceback
from config import Settings  # DB config

psycopg2.extras.register_uuid()


class ExceptionHandler:
    """Handles insertion and update of minimal exception records."""

    def __init__(self):
        self.db_config = Settings.POSTGRES
        self.conn = None
        self.cursor = None

    # ---------------- Connection ----------------
    def connect_db(self):
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
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception as e:
            print("⚠️ Error closing DB connection:", e)

    # ---------------- Table Creation ----------------
    def create_table_if_not_exists(self):
        """Create table with only required columns."""
        try:
            query = """
            CREATE TABLE IF NOT EXISTS exception_store (
                exception_id UUID PRIMARY KEY,
                transaction_id TEXT,
                type TEXT,
                description TEXT,
                module TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP
            );
            """
            self.cursor.execute(query)
            self.conn.commit()

            # Auto-heal if missing
            alter_queries = [
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS transaction_id TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS type TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS description TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS module TEXT;",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",
                "ALTER TABLE exception_store ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;"
            ]

            for q in alter_queries:
                self.cursor.execute(q)
            self.conn.commit()

        except Exception as e:
            print("❌ Error creating/updating exception_store:", str(e))
            traceback.print_exc()
            self.conn.rollback()
            raise

    # ---------------- UPSERT ----------------
    def upsert_exception(
        self,
        transaction_id: str,
        type: str = None,
        description: str = None,
        module: str = None,
    ):
        """Insert or update error record."""
        try:
            exception_id = uuid.uuid4()
            now = datetime.now()

            query = """
                INSERT INTO exception_store (
                    exception_id, transaction_id, type,
                    description, module, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exception_id)
                DO UPDATE SET
                    type = COALESCE(EXCLUDED.type, exception_store.type),
                    description = COALESCE(EXCLUDED.description, exception_store.description),
                    module = COALESCE(EXCLUDED.module, exception_store.module),
                    updated_at = EXCLUDED.updated_at;
            """

            self.cursor.execute(
                query,
                (exception_id, transaction_id, type, description, module, now, now),
            )
            self.conn.commit()

            print(f"⚠️ Exception logged for transaction {transaction_id} → {exception_id}")

        except Exception as e:
            print(f"❌ Error inserting exception for {transaction_id}: {e}")
            traceback.print_exc()
            self.conn.rollback()
            raise


# ---------------- Wrapper ----------------
def exception(
    transaction_id: str,
    type: str = None,
    description: str = None,
    module: str = None,
):
    """Lightweight one-line exception logger."""
    handler = ExceptionHandler()
    try:
        handler.connect_db()
        handler.create_table_if_not_exists()
        handler.upsert_exception(transaction_id, type, description, module)
    except Exception as e:
        print(f"❌ Failed to log exception for transaction {transaction_id}: {e}")
        traceback.print_exc()
    finally:
        handler.close_db()