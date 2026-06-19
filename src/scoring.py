import numpy as np
import pandas as pd
from src.config import (INTERIM, ARTIFACTS, SEVERITY, VEH_FOOTPRINT,
                        CIS_WEIGHTS, footprint_class)
from src import schema


def severity_for(violations, vehicle_type) -> float:
    vs = [] if violations is None else list(violations)
    if len(vs) == 0:
        base = 0.0
    else:
        base = max(SEVERITY.get(v, SEVERITY["_default"]) for v in vs)
    mult = VEH_FOOTPRINT[footprint_class(vehicle_type if isinstance(vehicle_type, str) else "")]
    return base * mult


def normalize(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = np.nanmin(x), np.nanmax(x)
    return np.zeros_like(x) if hi == lo else (x - lo) / (hi - lo)


def run(road_scores: dict | None = None) -> pd.DataFrame:
    if road_scores is None:
        try:
            from src.osm_roads import load_cached
            road_scores = load_cached()
            if road_scores:
                print("Using cached OSM road classes for road-criticality factor.")
        except Exception:
            road_scores = None
    df = pd.read_parquet(INTERIM / "clean.parquet")
    df["sev"] = [severity_for(v, vt) for v, vt in zip(df["violations"], df["vehicle_type"])]
    cells = df.groupby("h3").agg(
        n=("id", "count"),
        sev=("sev", "mean"),
        peak=("is_peak", "mean"),
    ).reset_index()
    cells["f_volume"] = normalize(np.log1p(cells["n"]))
    cells["f_severity"] = normalize(cells["sev"])
    cells["f_peak"] = normalize(cells["peak"])
    if road_scores:
        cells["f_road"] = cells["h3"].map(
            lambda h: road_scores[h][1] if h in road_scores else 0.5)
        cells["road_class"] = cells["h3"].map(
            lambda h: road_scores[h][0] if h in road_scores else "unknown")
    else:
        cells["f_road"] = 0.5
        cells["road_class"] = "unknown"
    w = CIS_WEIGHTS
    cells["cis"] = (w["volume"] * cells["f_volume"] + w["severity"] * cells["f_severity"]
                    + w["road"] * cells["f_road"] + w["peak"] * cells["f_peak"])
    hs = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")[["h3", "lat", "lon"]]
    cells = cells.merge(hs, on="h3", how="left")
    cells["rank"] = cells["cis"].rank(ascending=False, method="min").astype(int)
    out = cells.sort_values("rank")[schema.CIS_SCORES]
    out.to_parquet(ARTIFACTS / "cis_scores.parquet")
    print(f"CIS scored {len(out):,} cells (proxy index).")
    return out


def build_hourly_heat() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "cis", "lat", "lon"]]
    heat = (df.groupby(["h3", "hour", "is_weekend"])["id"].count()
            .rename("count").reset_index())
    heat = heat.merge(cis, on="h3", how="left")
    cmax = heat["count"].max() or 1
    heat["cis_hour"] = heat["cis"].fillna(0) * (heat["count"] / cmax)
    heat = heat[schema.HOURLY_HEAT]
    heat.to_parquet(ARTIFACTS / "hourly_heat.parquet")
    print(f"Hourly heat: {len(heat):,} cell-hour rows")
    return heat


if __name__ == "__main__":
    run()
    build_hourly_heat()
