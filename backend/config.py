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
    if os.environ.get("VERCEL") and DEPLOY_DB_PATH.exists():
        return DEPLOY_DB_PATH
    return ROOT / "data" / "parkpulse.db"


# Back-compat alias — prefer get_db_path() so tests can redirect via env.
DB_PATH = get_db_path()
HOST = "127.0.0.1"
PORT = 8000


def cors_origins() -> list[str]:
    origins = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    extra = os.environ.get("CORS_ORIGINS", "")
    if extra:
        origins.extend(x.strip() for x in extra.split(",") if x.strip())
    vercel_url = os.environ.get("VERCEL_URL")
    if vercel_url:
        origins.append(f"https://{vercel_url}")
    production = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
    if production:
        origins.append(f"https://{production}")
    return origins


CORS_ORIGINS = cors_origins()
