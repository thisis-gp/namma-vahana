import numpy as np
import pandas as pd
import h3
from sklearn.cluster import DBSCAN
from src.config import INTERIM, ARTIFACTS
from src import schema


def _mode(s):
    m = s.mode()
    return m.iat[0] if not m.empty else "Unknown"


def _display_location(s):
    m = s.dropna().astype(str).str.strip()
    m = m[m.ne("")]
    if m.empty:
        return ""
    raw = m.mode().iat[0]
    parts = [
        p.strip() for p in raw.split(",")
        if p.strip()
        and "pin-" not in p.lower()
        and p.strip().lower() not in {"india", "karnataka", "bengaluru"}
    ]
    return ", ".join(parts[:3]) if parts else raw


def run() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    agg = df.groupby("h3").agg(
        violation_count=("id", "count"),
        confirmed_count=("confirmed", "sum"),
        junction_name=("junction_name", _mode),
        display_location=("location", _display_location),
        police_station=("police_station", _mode),
        dominant_vehicle=("vehicle_type", _mode),
    ).reset_index()
    expl = pd.read_parquet(INTERIM / "violations_exploded.parquet").dropna(subset=["violation"])
    dom_v = (expl.groupby("h3")["violation"].agg(_mode)
             .rename("dominant_violation").reset_index())
    agg = agg.merge(dom_v, on="h3", how="left")
    agg["dominant_violation"] = agg["dominant_violation"].fillna("UNKNOWN")
    cents = np.array([h3.cell_to_latlng(c) for c in agg["h3"]])
    agg["lat"], agg["lon"] = cents[:, 0], cents[:, 1]
    coords = np.radians(cents)
    db = DBSCAN(eps=400 / 6371000, min_samples=3, metric="haversine").fit(coords)
    agg["dbscan_cluster"] = db.labels_
    agg["confirmed_count"] = agg["confirmed_count"].astype(int)
    agg = agg[schema.HOTSPOT_CELLS]
    agg.to_parquet(ARTIFACTS / "hotspot_cells.parquet")
    print(f"Hotspots: {len(agg):,} active H3 cells, "
          f"{(agg.dbscan_cluster >= 0).sum():,} in DBSCAN clusters")
    return agg


if __name__ == "__main__":
    run()
