"""Per-hotspot enrichment + station + citizen tables — all from the provided dataset.

Adds the merged-in features (rebuilt with in-dataset signals only, no external data):
severity 1-10, repeat-offender ratio -> intervention type, correction-rate confidence
flag, in-text context flags (school/hospital/bus), Location-Quotient peak window,
plain-language summary, station enforcement gap, allocation, and citizen fine-risk.
"""
import numpy as np
import pandas as pd
from src.config import (INTERIM, ARTIFACTS, SEVERITY_10, SEVERITY_10_DEFAULT,
                        REPEAT_MIN_APPEARANCES, REPEAT_RATIO_HIGH, CORRECTION_FLAG_MULT,
                        VIOL_CLEARED_PER_UNIT, SHIFTS_PER_DAY, COVERAGE_TARGET,
                        GAP_CONF_STD_MULT)
from src import schema

ROAD_DESC = {"arterial": "Arterial-road", "main_road": "Main-road",
             "major_junction": "Junction", "road": "Road-side",
             "minor_street": "Side-street", "residential": "Residential",
             "unknown": "Roadside"}


def _sev10(violations) -> int:
    vs = [] if violations is None else list(violations)
    if not vs:
        return SEVERITY_10_DEFAULT
    return max(SEVERITY_10.get(v, SEVERITY_10_DEFAULT) for v in vs)


def _norm(s):
    s = s.astype(float)
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0.0


def _nl_summary(r) -> str:
    road = ROAD_DESC.get(r["road_class"], "Roadside")
    near = []
    if r["near_school"]:
        near.append("a school")
    if r["near_hospital"]:
        near.append("a hospital")
    if r["blocks_bus"]:
        near.append("a bus stop")
    near_txt = (" near " + " and ".join(near)) if near else ""
    area = r["dominant_station"] or "Bengaluru"
    vol = int(r["violation_count"])
    dv = str(r["dominant_violation"]).title()
    if r["repeat_offender_ratio"] >= REPEAT_RATIO_HIGH:
        why = "driven by repeat offenders — targeted enforcement over signage"
    else:
        why = "mostly one-off parkers — an infrastructure / signage fix"
    return (f"{road} hotspot in {area}{near_txt}. {vol:,} violations, mostly {dv}. "
            f"{why}. Peak risk {r['peak_hours']}.")


def run():
    df = pd.read_parquet(INTERIM / "clean.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")
    hs = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")
    lq = pd.read_parquet(ARTIFACTS / "lq_table.parquet")

    # repeat offenders (global vehicle appearances >= 3)
    vc = df.groupby("vehicle_number")["id"].count()
    repeat_vehicles = set(vc[vc >= REPEAT_MIN_APPEARANCES].index)
    df["is_repeat"] = df["vehicle_number"].isin(repeat_vehicles)
    df["sev10"] = [_sev10(v) for v in df["violations"]]
    loc = df["location"].fillna("").str.lower()
    df["near_school"] = loc.str.contains("school", regex=False)
    df["near_hospital"] = loc.str.contains("hospital", regex=False)
    df["blocks_bus"] = loc.str.contains("bus", regex=False)

    cell = df.groupby("h3").agg(
        severity_10=("sev10", "mean"),
        repeat_offender_ratio=("is_repeat", "mean"),
        correction_rate=("corrected", "mean"),
        near_school=("near_school", "any"),
        near_hospital=("near_hospital", "any"),
        blocks_bus=("blocks_bus", "any"),
    ).reset_index()
    cell["severity_10"] = cell["severity_10"].round().clip(1, 10).astype(int)

    # ---- stations: enforcement gap (violations / devices), confidence ----
    st = df.groupby("police_station").agg(
        violations=("id", "count"),
        devices=("device_id", "nunique"),
        dev_corr=("corrected", "mean"),
    ).reset_index()
    st["gap_raw"] = st["violations"] / st["devices"].clip(lower=1)
    p95 = st["gap_raw"].quantile(0.95)
    st["enforcement_gap"] = (st["gap_raw"] / p95 * 10).clip(0, 10).round(1)
    thr = st["dev_corr"].mean() + GAP_CONF_STD_MULT * st["dev_corr"].std()
    st["gap_confidence"] = np.where(st["dev_corr"] >= thr, "lower", "ok")

    # merge everything onto the cis/hotspot base
    h = (cis.merge(hs[["h3", "violation_count", "confirmed_count", "junction_name",
                       "police_station", "dominant_vehicle", "dominant_violation"]], on="h3")
         .merge(cell, on="h3").merge(lq, on="h3"))
    h = h.rename(columns={"police_station": "dominant_station"})

    avg_corr = float(df["corrected"].mean())
    h["confidence_flag"] = np.where(h["correction_rate"] >= avg_corr * CORRECTION_FLAG_MULT,
                                    "lower", "ok")
    h["intervention_type"] = np.where(h["repeat_offender_ratio"] >= REPEAT_RATIO_HIGH,
                                      "Targeted enforcement (repeat offenders)",
                                      "Infrastructure / signage fix")
    # station gap -> per-cell boost for priority
    gap_map = st.set_index("police_station")["enforcement_gap"].to_dict()
    h["station_gap"] = h["dominant_station"].map(gap_map).fillna(0.0)
    h["priority_score"] = h["cis"] * (1 + 0.5 * h["station_gap"] / 10)
    h["priority_pct"] = (_norm(h["priority_score"]) * 100).round(1)
    h = h.sort_values("priority_score", ascending=False).reset_index(drop=True)
    h["rank"] = np.arange(1, len(h) + 1)

    # ---- allocation: units to cover COVERAGE_TARGET of severity-weighted demand ----
    # demand expressed per WEEK so it matches per-week patrol throughput
    dd = pd.to_datetime(df["date"])
    n_weeks = max((dd.max() - dd.min()).days / 7.0, 1.0)
    h["demand"] = (h["severity_10"] * h["violation_count"]) / n_weeks
    total_demand = h["demand"].sum()
    throughput = VIOL_CLEARED_PER_UNIT * SHIFTS_PER_DAY  # violations cleared / unit / week
    cum = h["demand"].cumsum()
    covered = cum <= COVERAGE_TARGET * total_demand
    h["units_recommended"] = np.where(covered,
                                      np.ceil(h["demand"] / throughput).clip(1, 8), 0).astype(int)

    h["nl_summary"] = h.apply(_nl_summary, axis=1)
    enriched = h[schema.HOTSPOTS_ENRICHED]
    enriched.to_parquet(ARTIFACTS / "hotspots.parquet")

    # station units = sum of its hotspots' units
    su = h.groupby("dominant_station")["units_recommended"].sum().rename("units_recommended")
    st = st.merge(su, left_on="police_station", right_index=True, how="left")
    st["units_recommended"] = st["units_recommended"].fillna(0).astype(int)
    st[schema.STATIONS].to_parquet(ARTIFACTS / "stations.parquet")

    # ---- citizen fine-risk ----
    cz = h.copy()
    cz["fine_risk"] = ((0.6 * _norm(cz["violation_count"]) + 0.4 * _norm(cz["cis"])) * 100).round(1)
    q = cz["fine_risk"].rank(pct=True)
    cz["risk_band"] = np.select(
        [q >= 0.90, q >= 0.70, q >= 0.40],
        ["VERY HIGH", "HIGH", "MODERATE"], default="LOWER")
    cz[schema.CITIZEN].to_parquet(ARTIFACTS / "citizen.parquet")

    print(f"Enriched {len(enriched):,} hotspots · {len(st)} stations · "
          f"total units rec. {int(st['units_recommended'].sum())} · "
          f"chronic-offender hotspots {(h['repeat_offender_ratio'] >= REPEAT_RATIO_HIGH).sum()}")
    return enriched


if __name__ == "__main__":
    run()
