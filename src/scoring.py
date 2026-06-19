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


def road_class_from_text(text):
    """Road-importance proxy parsed from the dataset's own `location` text.
    100% in-dataset — no external data."""
    t = (text or "").lower() if isinstance(text, str) else ""
    if any(k in t for k in ("ring road", "national highway", "highway", "flyover", "elevated")):
        return "arterial", 1.0
    if "main road" in t:
        return "main_road", 0.8
    if "circle" in t:
        return "major_junction", 0.7
    if "road" in t:
        return "road", 0.55
    if any(k in t for k in ("cross", "street", "lane")):
        return "minor_street", 0.45
    if any(k in t for k in ("layout", "nagar", "colony", "extension")):
        return "residential", 0.35
    return "unknown", 0.5


def _mode(s):
    m = s.mode()
    return m.iat[0] if not m.empty else "unknown"


def run() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    df["sev"] = [severity_for(v, vt) for v, vt in zip(df["violations"], df["vehicle_type"])]
    rc = df["location"].map(road_class_from_text)
    df["road_class_row"] = [x[0] for x in rc]
    df["road_w"] = [x[1] for x in rc]
    cells = df.groupby("h3").agg(
        n=("id", "count"),
        sev=("sev", "mean"),
        peak=("is_peak", "mean"),
        f_road=("road_w", "mean"),
        road_class=("road_class_row", _mode),
    ).reset_index()
    cells["f_volume"] = normalize(np.log1p(cells["n"]))
    cells["f_severity"] = normalize(cells["sev"])
    cells["f_peak"] = normalize(cells["peak"])
    cells["f_road"] = cells["f_road"].fillna(0.5)
    w = CIS_WEIGHTS
    cells["cis"] = (w["volume"] * cells["f_volume"] + w["severity"] * cells["f_severity"]
                    + w["road"] * cells["f_road"] + w["peak"] * cells["f_peak"])
    hs = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")[["h3", "lat", "lon"]]
    cells = cells.merge(hs, on="h3", how="left")
    cells["rank"] = cells["cis"].rank(ascending=False, method="min").astype(int)
    out = cells.sort_values("rank")[schema.CIS_SCORES]
    out.to_parquet(ARTIFACTS / "cis_scores.parquet")
    print(f"CIS scored {len(out):,} cells (proxy index, road factor from in-dataset "
          f"location text). Road-class mix: {cells['road_class'].value_counts().head(5).to_dict()}")
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
