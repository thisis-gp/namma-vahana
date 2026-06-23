"""Database connection and schema initialization."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator

from backend.config import SCHEMA_PATH, get_db_path


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def session() -> Generator[sqlite3.Connection, None, None]:
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _add_column_if_missing(con, table: str, column: str, decl: str) -> None:
    cols = {r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with session() as con:
        con.executescript(schema)
        # Lightweight migrations for DBs created before these columns existed.
        _add_column_if_missing(con, "reports", "image", "TEXT DEFAULT ''")
        _add_column_if_missing(con, "parking_spots", "image", "TEXT DEFAULT ''")


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]
