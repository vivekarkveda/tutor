import os
import logging
from datetime import datetime

# ---------------- CONFIG ----------------
# Set your log level here: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
LOG_LEVEL = "DEBUG"
# ----------------------------------------

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

# Custom filter that only allows messages of the exact level
class ExactLevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        return record.levelno == self.level

# Common formatter
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)

# ---------------- PIPELINE LOGGER ----------------
pipeline_logger = logging.getLogger("pipeline")
pipeline_logger.setLevel(level)
pipeline_logger.propagate = False

if not pipeline_logger.handlers:
    pipeline_handler = logging.FileHandler(pipeline_log_file, mode="w", encoding="utf-8")
    pipeline_handler.setFormatter(formatter)
    pipeline_handler.setLevel(level)
    pipeline_handler.addFilter(ExactLevelFilter(level))  # only same-level logs
    pipeline_logger.addHandler(pipeline_handler)

# ---------------- VALIDATION LOGGER ----------------
validation_logger = logging.getLogger("validation")
validation_logger.setLevel(level)
validation_logger.propagate = False

if not validation_logger.handlers:
    validation_handler = logging.FileHandler(validation_log_file, mode="w", encoding="utf-8")
    validation_handler.setFormatter(formatter)
    validation_handler.setLevel(level)
    validation_handler.addFilter(ExactLevelFilter(level))  # only same-level logs
    validation_logger.addHandler(validation_handler)

# ---------------- TEST (Optional) ----------------
if __name__ == "__main__":
    pipeline_logger.debug("This is a DEBUG message")
    pipeline_logger.info("This is an INFO message")
    pipeline_logger.warning("This is a WARNING message")

    validation_logger.debug("Validation DEBUG")
    validation_logger.info("Validation INFO")
