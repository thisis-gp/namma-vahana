import pandas as pd
from src.config import ARTIFACTS, OPT
from src import schema


def greedy_allocate(cells: pd.DataFrame, n_units: int) -> pd.DataFrame:
    """Per shift, assign the n_units highest-value cells to units."""
    out = []
    for shift, grp in cells.sort_values("value", ascending=False).groupby("shift"):
        for i, (_, r) in enumerate(grp.head(n_units).iterrows()):
            row = r.to_dict()
            if row.get("expected_violations", 0) <= 0 and row.get("value", 0) > 0:
                row["expected_violations"] = 1
            row["assigned_unit"] = f"Unit {i + 1}"
            row["rank"] = i + 1
            out.append(row)
    return pd.DataFrame(out)


def run() -> pd.DataFrame:
    fc = pd.read_parquet(ARTIFACTS / "forecast.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "cis"]]
    hs = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")[
        ["h3", "junction_name", "display_location", "police_station",
         "dominant_vehicle", "dominant_violation"]]
    df = fc.merge(cis, on="h3", how="left").merge(hs, on="h3", how="left")
    df["value"] = df["pred_intensity"].fillna(0) * df["cis"].fillna(0)
    plan = greedy_allocate(df, OPT["n_units_per_shift"])
    plan = plan[schema.PATROL_PLAN]
    plan.to_parquet(ARTIFACTS / "patrol_plan.parquet")
    print(f"Patrol plan: {len(plan)} assignments across {plan['shift'].nunique()} shifts")
    return plan


if __name__ == "__main__":
    run()
