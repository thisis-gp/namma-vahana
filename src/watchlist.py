"""Repeat-offender watchlist — chronic vehicles with many parking violations.

A vehicle-level enforcement lever (escalating penalty / targeted action) derived
purely from the provided dataset's anonymized but stable `vehicle_number`.
"""
import pandas as pd
from src.config import INTERIM, ARTIFACTS
from src import schema

MIN_VIOLATIONS = 10
TOP_N = 250


def _mode(s):
    m = s.mode()
    return m.iat[0] if not m.empty else ""


def run() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    df = df[df["vehicle_number"].notna() & (df["vehicle_number"] != "NULL")]
    sev = None
    try:
        from src.scoring import severity_for
        sev = [severity_for(v, vt) for v, vt in zip(df["violations"], df["vehicle_type"])]
    except Exception:
        sev = 0
    df = df.assign(sev=sev)
    g = df.groupby("vehicle_number")
    wl = g.agg(
        vehicle_type=("vehicle_type", _mode),
        violations=("id", "count"),
        distinct_cells=("h3", "nunique"),
        top_location=("location", _mode),
        top_junction=("junction_name", _mode),
        severity_sum=("sev", "sum"),
        first_seen=("date", "min"),
        last_seen=("date", "max"),
    ).reset_index()
    wl = wl[wl["violations"] >= MIN_VIOLATIONS].sort_values("violations", ascending=False)
    wl = wl.head(TOP_N)[schema.WATCHLIST]
    wl.to_parquet(ARTIFACTS / "watchlist.parquet")
    print(f"Watchlist: {len(wl)} chronic offenders (>= {MIN_VIOLATIONS} violations). "
          f"Worst vehicle: {int(wl['violations'].max())} violations.")
    return wl


if __name__ == "__main__":
    run()
