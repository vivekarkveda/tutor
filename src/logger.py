import os
import logging
from datetime import datetime


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


# File paths with timestamp
pipeline_log_file = os.path.join(pipeline_log_dir, f"pipeline_{timestamp}.log")
validation_log_file = os.path.join(validation_log_dir, f"validation_{timestamp}.log")


# PIPELINE LOGGER
pipeline_logger = logging.getLogger("pipeline")
pipeline_logger.setLevel(logging.INFO)
pipeline_logger.propagate = False


if not pipeline_logger.handlers:
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    pipeline_handler = logging.FileHandler(pipeline_log_file, mode="w", encoding="utf-8")
    pipeline_handler.setFormatter(formatter)
    pipeline_logger.addHandler(pipeline_handler)


# VALIDATION LOGGER
validation_logger = logging.getLogger("validation")
validation_logger.setLevel(logging.INFO)
validation_logger.propagate = False


if not validation_logger.handlers:
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    validation_handler = logging.FileHandler(validation_log_file, mode="w", encoding="utf-8")
    validation_handler.setFormatter(formatter)
    validation_logger.addHandler(validation_handler)



