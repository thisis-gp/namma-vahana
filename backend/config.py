"""Backend configuration — single source of truth for paths and server settings."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).resolve().parent / "migrations" / "schema.sql"


def get_db_path() -> Path:
    """SQLite path; override with PARKPULSE_DB for tests."""
    override = os.environ.get("PARKPULSE_DB")
    if override:
        return Path(override)
    return ROOT / "data" / "parkpulse.db"


# Back-compat alias — prefer get_db_path() so tests can redirect via env.
DB_PATH = get_db_path()
HOST = "127.0.0.1"
PORT = 8000
CORS_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]
