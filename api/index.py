"""Vercel serverless entry — prepares bundled SQLite then exposes FastAPI app."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("VERCEL", "1")

DEPLOY_DB = ROOT / "backend" / "deploy" / "parkpulse.db"
TMP_DB = Path("/tmp/parkpulse.db")

if DEPLOY_DB.exists():
    if not TMP_DB.exists() or TMP_DB.stat().st_mtime < DEPLOY_DB.stat().st_mtime:
        shutil.copy2(DEPLOY_DB, TMP_DB)
    os.environ["PARKPULSE_DB"] = str(TMP_DB)
elif not os.environ.get("PARKPULSE_DB"):
    os.environ["PARKPULSE_DB"] = str(DEPLOY_DB)

from backend.main import app  # noqa: E402
