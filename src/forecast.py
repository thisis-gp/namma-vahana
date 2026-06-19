import json
import pandas as pd
from src.config import INTERIM, ARTIFACTS, SPLIT, SHIFT_SLOTS
from src import schema


def precision_at_k(actual: dict, pred: dict, k: int) -> float:
    top_actual = set(sorted(actual, key=actual.get, reverse=True)[:k])
    top_pred = set(sorted(pred, key=pred.get, reverse=True)[:k])
    return len(top_actual & top_pred) / k


def _panel() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    panel = (df.groupby(["h3", "date", "shift"])["id"].count()
             .rename("y").reset_index())
    panel["date"] = pd.to_datetime(panel["date"])
    return panel.sort_values("date")


def run() -> pd.DataFrame:
    panel = _panel()
    panel["dow"] = panel["date"].dt.dayofweek
    train = panel[panel["date"] < pd.Timestamp(SPLIT["train_end"])]
    naive = (train.groupby(["h3", "dow", "shift"])["y"].mean()
             .rename("naive").reset_index())
    last_date = panel["date"].max()
    next_date = last_date + pd.Timedelta(days=1)
    nd = next_date.dayofweek
    grid = (naive[naive["dow"] == nd]
            .groupby(["h3", "shift"])["naive"].mean().reset_index())
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "lat", "lon", "cis"]]
    grid = grid.merge(cis, on="h3", how="left")
    grid["date"] = next_date.date().isoformat()
    cis_fill = grid["cis"].median()
    grid["pred_intensity"] = grid["naive"] * grid["cis"].fillna(cis_fill)
    grid["expected_violations"] = grid["naive"].round().astype(int)
    out = grid[schema.FORECAST]
    out.to_parquet(ARTIFACTS / "forecast.parquet")

    test = panel[panel["date"] > pd.Timestamp(SPLIT["val_end"])]
    p20 = None
    if len(test):
        actual = test.groupby("h3")["y"].sum().to_dict()
        pred_naive = naive.groupby("h3")["naive"].mean().to_dict()
        p20 = precision_at_k(actual, pred_naive, 20)
        print(f"Forecast written. Seasonal-naive Precision@20 (test) = {p20:.2f}")
    json.dump({"naive_precision_at_20": p20},
              open(ARTIFACTS / "_forecast_metrics.json", "w"))
    return out


if __name__ == "__main__":
    run()
