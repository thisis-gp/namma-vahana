import json
import pandas as pd
from src.config import INTERIM, ARTIFACTS


def run() -> dict:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")
    total = len(df)
    confirmed = int(df["confirmed"].sum())
    vol = df.groupby("h3")["id"].count().rename("n").reset_index().merge(
        cis[["h3", "cis"]], on="h3", how="left")
    vol["impact"] = vol["n"] * vol["cis"].fillna(0)
    top20 = vol.nlargest(20, "impact")["impact"].sum() / vol["impact"].sum()
    evening = (df["shift"] == "EVENING").mean()
    veh_counts = df.groupby("vehicle_number")["id"].count()
    repeats = int((veh_counts >= 10).sum())
    repeat_share = float(veh_counts[veh_counts >= 10].sum() / len(df))
    fm_path = ARTIFACTS / "_forecast_metrics.json"
    fm = json.load(open(fm_path)) if fm_path.exists() else {}
    naive_p20 = fm.get("naive_precision_at_20")
    lgbm_p20 = fm.get("precision_at_20")
    bt_path = ARTIFACTS / "backtest.parquet"
    uplift_k = pp_cov = re_cov = uplift_pp = None
    if bt_path.exists():
        import pandas as _pd
        from src.config import OPT
        bt = _pd.read_parquet(bt_path)
        k = OPT["n_units_per_shift"]
        r = bt[bt["k"] == k].iloc[0]
        uplift_k = int(k)
        pp_cov = round(float(r["parkpulse_coverage"]), 3)
        re_cov = round(float(r["reactive_coverage"]), 3)
        uplift_pp = round(float(r["uplift_pp"]), 1)
    k = {
        "total_violations": total,
        "confirmed_violations": confirmed,
        "n_stations": int(df["police_station"].nunique()),
        "n_hotspots": int(cis["h3"].nunique()),
        "top20_impact_share": round(float(top20), 3),
        "evening_enforcement_share": round(float(evening), 3),
        "repeat_offenders": repeats,
        "repeat_offender_share": round(repeat_share, 3),
        "precision_at_20": round(lgbm_p20, 3) if lgbm_p20 is not None else None,
        "naive_precision_at_20": round(naive_p20, 3) if naive_p20 is not None else None,
        "uplift_k": uplift_k,
        "parkpulse_coverage": pp_cov,
        "reactive_coverage": re_cov,
        "uplift_pp": uplift_pp,
        "speed_corr_spearman": None,
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
    }
    json.dump(k, open(ARTIFACTS / "kpis.json", "w"), indent=2)
    print("KPIs:", k)
    return k


if __name__ == "__main__":
    run()
