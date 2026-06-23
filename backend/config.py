"""Backend configuration — single source of truth for paths and server settings."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).resolve().parent / "migrations" / "schema.sql"
DEPLOY_DB_PATH = Path(__file__).resolve().parent / "deploy" / "parkpulse.db"


def get_db_path() -> Path:
    """SQLite path; override with PARKPULSE_DB for tests."""
    override = os.environ.get("PARKPULSE_DB")
    if override:
        return Path(override)
    if os.environ.get("RENDER") and DEPLOY_DB_PATH.exists():
        return DEPLOY_DB_PATH
    if os.environ.get("VERCEL") and DEPLOY_DB_PATH.exists():
        return DEPLOY_DB_PATH
    return ROOT / "data" / "parkpulse.db"


# Back-compat alias — prefer get_db_path() so tests can redirect via env.
DB_PATH = get_db_path()
HOST = "127.0.0.1"
PORT = 8000
IS_PRODUCTION = os.environ.get("RENDER") == "true" or os.environ.get("VERCEL") == "1"


def cors_origins() -> list[str]:
    """Explicit allowlist only — no wildcard subdomains."""
    origins = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://namma-vahana.vercel.app",
    ]
    extra = os.environ.get("CORS_ORIGINS", "")
    if extra:
        for origin in extra.split(","):
            origin = origin.strip()
            if origin and origin not in origins:
                origins.append(origin)
    return origins


CORS_ORIGINS = cors_origins()
