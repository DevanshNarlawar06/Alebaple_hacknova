"""
utils.py — Shared utilities for the dataset pipeline.

Provides:
  - Environment loading
  - SQLite connection factory
  - UUID generation
  - ISO 8601 timestamp helpers
  - Logging setup
  - Schema version constant
"""

import os
import uuid
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

SCHEMA_VERSION = "0.1"
PROJECT_ROOT   = Path(__file__).parent.parent
SQLITE_DB_PATH = PROJECT_ROOT / os.getenv("SQLITE_DB_PATH", "data/db/evidence.db")
SCHEMA_SQL     = PROJECT_ROOT / "schema" / "schema.sql"


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given script name."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    return logging.getLogger(name)


def get_db(db_path: Path = SQLITE_DB_PATH) -> sqlite3.Connection:
    """
    Return a WAL-mode SQLite connection with foreign keys enabled.
    Creates the database and applies schema if it does not yet exist.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def new_id(prefix: str = "") -> str:
    """Generate a short prefixed UUID4 identifier."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def now_utc() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_latitude(lat) -> bool:
    if lat is None:
        return True  # NULL is allowed
    try:
        return -90.0 <= float(lat) <= 90.0
    except (TypeError, ValueError):
        return False


def validate_longitude(lon) -> bool:
    if lon is None:
        return True
    try:
        return -180.0 <= float(lon) <= 180.0
    except (TypeError, ValueError):
        return False
