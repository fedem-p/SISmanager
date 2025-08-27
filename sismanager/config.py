"""Centralized configuration and logging for SISmanager."""

import os
import logging

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("SISMANAGER_DATA_DIR", os.path.join(BASE_DIR, "data"))
BACKUP_DIR = os.environ.get("SISMANAGER_BACKUP_DIR", os.path.join(DATA_DIR, "backups"))
CENTRAL_DB_PATH = os.environ.get(
    "SISMANAGER_CENTRAL_DB_PATH", os.path.join(DATA_DIR, "central_db.csv")
)

# Database connection config (for future migration)
DB_TYPE = os.environ.get("SISMANAGER_DB_TYPE", "csv")  # or 'sqlite', 'postgresql', etc.
DB_URL = os.environ.get("SISMANAGER_DB_URL", "")  # e.g., sqlite:///path/to/db.sqlite

# Logging
LOG_LEVEL = os.environ.get("SISMANAGER_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_FILE = os.path.join(BASE_DIR, "sismanager.log")

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)

logger = logging.getLogger("sismanager")
