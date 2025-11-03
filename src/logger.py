import os
import logging
from datetime import datetime
import psycopg2
from config import Settings

# ---------------- CONFIG ----------------
LOG_LEVEL = "ERROR"
# ----------------------------------------

POSTGRES = Settings.POSTGRES

base_dir = os.path.dirname(__file__)
log_dir = os.path.join(base_dir, "logs")

# Subfolders
pipeline_log_dir = os.path.join(log_dir, "pipeline")
validation_log_dir = os.path.join(log_dir, "validation")

# Create folders if they don't exist
os.makedirs(pipeline_log_dir, exist_ok=True)
os.makedirs(validation_log_dir, exist_ok=True)

# Timestamp for log filenames
timestamp = datetime.now().strftime("%Y_%m_%d_at_%H-%M-%S")

# File paths
pipeline_log_file = os.path.join(pipeline_log_dir, f"pipeline_{timestamp}.log")
validation_log_file = os.path.join(validation_log_dir, f"validation_{timestamp}.log")

# Convert LOG_LEVEL string to logging constant
level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

# ---------------- FILTER ----------------
class ExactLevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        return record.levelno == self.level

# ---------------- FORMATTER ----------------
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)

# ---------------- FILE LOGGERS ----------------
pipeline_logger = logging.getLogger("pipeline")
pipeline_logger.setLevel(level)
pipeline_logger.propagate = False

if not pipeline_logger.handlers:
    pipeline_handler = logging.FileHandler(pipeline_log_file, mode="w", encoding="utf-8")
    pipeline_handler.setFormatter(formatter)
    pipeline_handler.setLevel(level)
    pipeline_handler.addFilter(ExactLevelFilter(level))
    pipeline_logger.addHandler(pipeline_handler)

validation_logger = logging.getLogger("validation")
validation_logger.setLevel(level)
validation_logger.propagate = False

if not validation_logger.handlers:
    validation_handler = logging.FileHandler(validation_log_file, mode="w", encoding="utf-8")
    validation_handler.setFormatter(formatter)
    validation_handler.setLevel(level)
    validation_handler.addFilter(ExactLevelFilter(level))
    validation_logger.addHandler(validation_handler)

# ---------------- POSTGRES ERROR HANDLER ----------------
class PostgresErrorHandler(logging.Handler):
    """
    Logs full ERROR blocks (STDERR, STDOUT, Tracebacks, etc.)
    into the PostgreSQL 'exceptions' table.
    """

    def __init__(self, log_type, db_config):
        super().__init__(level=logging.ERROR)
        self.log_type = log_type
        self.db_config = db_config
        self._ensure_table_exists()

    def _connect(self):
        return psycopg2.connect(
            host=self.db_config["host"],
            port=self.db_config["port"],
            user=self.db_config["user"],
            password=self.db_config["password"],
            dbname=self.db_config["dbname"],
        )

    def _ensure_table_exists(self):
        """Creates the table if missing."""
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS exceptions (
                    id SERIAL PRIMARY KEY,
                    log_type VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    part_name VARCHAR(255),
                    error_summary TEXT,
                    error_details TEXT NOT NULL
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Failed to ensure 'exceptions' table exists: {e}")

    def emit(self, record):
        """Insert a new full log record."""
        try:
            # Get full formatted message (entire block)
            full_message = self.format(record) if self.formatter else record.getMessage()
            part_name = getattr(record, "part_name", None)

            # Extract short summary (first line or first sentence)
            lines = full_message.strip().splitlines()
            error_summary = lines[0].strip() if lines else "Unknown Error"

            conn = self._connect()
            cur = conn.cursor()

            insert_sql = """
                INSERT INTO exceptions (log_type, part_name, error_summary, error_details)
                VALUES (%s, %s, %s, %s);
            """
            cur.execute(insert_sql, (self.log_type, part_name, error_summary, full_message))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"⚠️ Failed to log error to Postgres: {e}")

# ---------------- ATTACH HANDLERS ----------------
def add_postgres_handlers():
    global pipeline_logger, validation_logger
    if not any(isinstance(h, PostgresErrorHandler) for h in pipeline_logger.handlers):
        pg_pipeline_handler = PostgresErrorHandler("pipeline", POSTGRES)
        pg_pipeline_handler.setLevel(logging.ERROR)
        pg_pipeline_handler.setFormatter(formatter)
        pipeline_logger.addHandler(pg_pipeline_handler)

    if not any(isinstance(h, PostgresErrorHandler) for h in validation_logger.handlers):
        pg_validation_handler = PostgresErrorHandler("validation", POSTGRES)
        pg_validation_handler.setLevel(logging.ERROR)
        pg_validation_handler.setFormatter(formatter)
        validation_logger.addHandler(pg_validation_handler)

add_postgres_handlers()

# ---------------- TEST ----------------
if __name__ == "__main__":
    # Example: a detailed multi-line error (like Manim)
    big_error_block = """
❌ Error running Manim on C:/Vivek_Main/Manim_project/inputbox/input_data_20251031_171519/script_seq4/script_seq4.py
──────────────────────────────────────────────
STDERR:
+--------------------- Traceback (most recent call last) ---------------------+
| C:\\Manim\\scene.py:237 in render |
| > 237 self.construct() |
+-----------------------------------------------------------------------------+
TypeError: Angle.__init__() got multiple values for argument 'radius'

STDOUT:
Manim Community v0.19.0
──────────────────────────────────────────────
"""
    pipeline_logger.error(big_error_block, extra={"part_name": "VideoFactory"})
    validation_logger.error("❌ HTTP 500: Video and audio lists must have the same length", extra={"part_name": "MergerFactory"})
    print("✅ Detailed error blocks logged successfully.")
