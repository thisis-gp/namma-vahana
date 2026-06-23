"""Load pipeline parquet artifacts into SQLite for the API layer."""
from __future__ import annotations

import json
import sqlite3

import pandas as pd

from backend.config import get_db_path
from backend.database import init_db, session
from backend.repositories.analytics import clear_analytics
from src.config import ARTIFACTS, ROOT

HOT_COLS = [
    "h3", "lat", "lon", "priority_pct", "rank", "violation_count",
    "dominant_station", "junction_name", "display_location", "dominant_vehicle",
    "dominant_violation", "severity_10", "road_class", "intervention_type",
    "peak_hours", "repeat_offender_ratio", "confidence_flag", "units_recommended",
    "near_school", "near_hospital", "blocks_bus", "nl_summary",
]


def _clean_place_names(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("junction_name", "display_location", "dominant_station", "police_station", "top_junction"):
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .replace({"No Junction": "", "null": "", "NULL": "", "None": ""})
            )
    return df


def _bool_to_int(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(bool).astype(int)
    return df


def _insert_df(con: sqlite3.Connection, table: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    table_cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    cols = [c for c in df.columns if c in table_cols]
    if not cols:
        return 0
    subset = df[cols]
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    con.executemany(sql, subset.itertuples(index=False, name=None))
    return len(subset)


def run() -> None:
    if not (ARTIFACTS / "kpis.json").exists():
        raise FileNotFoundError(
            f"Artifacts missing at {ARTIFACTS}. Run `python -m src.run_pipeline` first."
        )

    init_db()

    kp = json.loads((ARTIFACTS / "kpis.json").read_text(encoding="utf-8"))
    if (ARTIFACTS / "_nb_meta.json").exists():
        kp.update(json.loads((ARTIFACTS / "_nb_meta.json").read_text(encoding="utf-8")))

    hot = _bool_to_int(
        _clean_place_names(pd.read_parquet(ARTIFACTS / "hotspots.parquet")[HOT_COLS]),
        ["near_school", "near_hospital", "blocks_bus"],
    )
    st = pd.read_parquet(ARTIFACTS / "stations.parquet")
    cz = _clean_place_names(pd.read_parquet(ARTIFACTS / "citizen.parquet"))
    bt = pd.read_parquet(ARTIFACTS / "backtest.parquet")
    nb = pd.read_parquet(ARTIFACTS / "nb_forecast.parquet")
    pt = _clean_place_names(pd.read_parquet(ARTIFACTS / "patrol_plan.parquet"))
    wl = _clean_place_names(pd.read_parquet(ARTIFACTS / "watchlist.parquet").head(60))

    with session() as con:
        clear_analytics(con)
        con.execute(
            "INSERT OR REPLACE INTO kpis (id, payload) VALUES (1, ?)",
            [json.dumps(kp)],
        )
        counts = {
            "hotspots": _insert_df(con, "hotspots", hot),
            "stations": _insert_df(con, "stations", st),
            "citizen": _insert_df(con, "citizen", cz),
            "backtest": _insert_df(con, "backtest", bt),
            "nb_forecast": _insert_df(con, "nb_forecast", nb),
            "patrol_plan": _insert_df(con, "patrol_plan", pt),
            "watchlist": _insert_df(con, "watchlist", wl),
        }

    db_path = get_db_path()
    print(f"Exported analytics to {db_path}")
    for name, n in counts.items():
        print(f"  {name}: {n} rows")


if __name__ == "__main__":
    run()
