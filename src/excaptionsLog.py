import psycopg2
from psycopg2.extras import execute_values
from logger import pipeline_logger

# Your Postgres credentials (replace with your env vars or config)
POSTGRES = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "your_password",
    "dbname": "your_database"
}

class PostgresErrorHandler(logging.Handler):
    """Custom logging handler that writes ERROR logs to PostgreSQL."""

    def __init__(self, log_type, db_config):
        super().__init__(level=logging.ERROR)
        self.log_type = log_type
        self.db_config = db_config

    def emit(self, record):
        try:
            msg = self.format(record)
            part_name = getattr(record, "part_name", "unknown_part")

            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO error_logs (log_type, part_name, error_details)
                VALUES (%s, %s, %s)
                """,
                (self.log_type, part_name, msg)
            )

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"⚠️ Failed to log error to Postgres: {e}")
