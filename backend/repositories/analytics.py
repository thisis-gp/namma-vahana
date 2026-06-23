"""Analytics data access — read-only pipeline artifacts from SQLite."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter

from backend.database import rows_to_dicts, session

_BOOL_COLS = {"near_school", "near_hospital", "blocks_bus"}


def _strip_addr(s: str) -> str:
    """Drop the ', Bengaluru, Karnataka. Pin-… (India)' tail from an address."""
    return re.split(r",\s*Bengaluru", s or "")[0].strip()


def _build_station_index(con) -> tuple[dict, dict]:
    """Map junction → station and area-token → station from the hotspots table.

    Lets us attribute a repeat offender to a station even when they have no
    named junction, by matching their top_location's area words — all in-dataset
    (no geocoding / external lookup, per the rules).
    """
    junction_station: dict[str, Counter] = {}
    token_station: dict[str, Counter] = {}
    for r in con.execute(
        "SELECT display_location, junction_name, dominant_station "
        "FROM hotspots WHERE dominant_station IS NOT NULL"
    ).fetchall():
        station = r["dominant_station"]
        if r["junction_name"]:
            junction_station.setdefault(r["junction_name"], Counter())[station] += 1
        for seg in _strip_addr(r["display_location"]).split(","):
            tok = seg.strip().lower()
            if len(tok) > 4:
                token_station.setdefault(tok, Counter())[station] += 1
    return junction_station, token_station


def _resolve_station(
    junction: str, location: str, junction_station: dict, token_station: dict
) -> tuple[str | None, bool]:
    """(station, exact?) — exact when matched on a named junction."""
    if junction and junction in junction_station:
        return junction_station[junction].most_common(1)[0][0], True
    for seg in _strip_addr(location).split(","):
        tok = seg.strip().lower()
        if tok in token_station:
            return token_station[tok].most_common(1)[0][0], False
    return None, False


def _boolify(row: dict) -> dict:
    for col in _BOOL_COLS:
        if col in row:
            row[col] = bool(row[col])
    return row


def get_kpis() -> dict | None:
    with session() as con:
        row = con.execute("SELECT payload FROM kpis WHERE id = 1").fetchone()
        return json.loads(row["payload"]) if row else None


def list_hotspots(station: str | None = None, limit: int | None = None) -> list[dict]:
    sql = "SELECT * FROM hotspots"
    args: list = []
    if station:
        sql += " WHERE dominant_station = ?"
        args.append(station)
    sql += " ORDER BY rank ASC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with session() as con:
        return [_boolify(dict(r)) for r in con.execute(sql, args).fetchall()]


def list_stations() -> list[dict]:
    with session() as con:
        return rows_to_dicts(
            con.execute("SELECT * FROM stations ORDER BY violations DESC").fetchall()
        )


def list_citizen(limit: int | None = None) -> list[dict]:
    sql = "SELECT * FROM citizen ORDER BY fine_risk DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with session() as con:
        return rows_to_dicts(con.execute(sql).fetchall())


def list_backtest() -> list[dict]:
    with session() as con:
        return rows_to_dicts(con.execute("SELECT * FROM backtest ORDER BY k").fetchall())


def list_nb_forecast() -> list[dict]:
    with session() as con:
        return rows_to_dicts(
            con.execute("SELECT * FROM nb_forecast ORDER BY forecast_next_week DESC").fetchall()
        )


def list_patrol(station: str | None = None, shift: str | None = None) -> list[dict]:
    sql = (
        "SELECT shift, h3, junction_name, display_location, police_station, "
        "expected_violations, dominant_vehicle, dominant_violation, assigned_unit, rank "
        "FROM patrol_plan WHERE 1=1"
    )
    args: list = []
    if station:
        sql += " AND police_station = ?"
        args.append(station)
    if shift:
        sql += " AND shift = ?"
        args.append(shift)
    sql += " ORDER BY shift, rank"
    with session() as con:
        return rows_to_dicts(con.execute(sql, args).fetchall())


def list_watchlist(limit: int = 60, station: str | None = None) -> list[dict]:
    # The watchlist has no station column. Attribute each offender to a station
    # by their most-frequent junction; if they have none, fall back to matching
    # the area words in their top_location. Whatever can't be resolved stays
    # city-wide (station=None) rather than being dropped from the filter.
    with session() as con:
        rows = rows_to_dicts(
            con.execute(
                "SELECT * FROM watchlist ORDER BY violations DESC"
            ).fetchall()
        )
        junction_station, token_station = _build_station_index(con)

    for r in rows:
        st, exact = _resolve_station(
            r.get("top_junction", ""), r.get("top_location", ""),
            junction_station, token_station,
        )
        r["station"] = st
        r["station_exact"] = exact

    if station:
        rows = [r for r in rows if r["station"] == station]
    return rows[:limit]


def clear_analytics(con: sqlite3.Connection) -> None:
    for table in (
        "kpis", "hotspots", "stations", "citizen", "backtest",
        "nb_forecast", "patrol_plan", "watchlist",
    ):
        con.execute(f"DELETE FROM {table}")
