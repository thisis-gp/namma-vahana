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
    repeats = int((df.groupby("vehicle_number")["id"].count() >= 10).sum())
    fm_path = ARTIFACTS / "_forecast_metrics.json"
    naive_p20 = json.load(open(fm_path)).get("naive_precision_at_20") if fm_path.exists() else None
    k = {
        "total_violations": total,
        "confirmed_violations": confirmed,
        "n_stations": int(df["police_station"].nunique()),
        "n_hotspots": int(cis["h3"].nunique()),
        "top20_impact_share": round(float(top20), 3),
        "evening_enforcement_share": round(float(evening), 3),
        "repeat_offenders": repeats,
        "precision_at_20": None,
        "naive_precision_at_20": round(naive_p20, 3) if naive_p20 is not None else None,
        "speed_corr_spearman": None,
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
    }
    json.dump(k, open(ARTIFACTS / "kpis.json", "w"), indent=2)
    print("KPIs:", k)
    return k


if __name__ == "__main__":
    run()
