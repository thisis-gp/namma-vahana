import json
import itertools
import numpy as np
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


FEATURES = ["lag1", "lag7", "roll28", "expmean", "dow", "is_weekend",
            "shift_code", "cis", "f_road"]


def _build_grid():
    df = pd.read_parquet(INTERIM / "clean.parquet")
    obs = (df.groupby(["h3", "date", "shift"])["id"].count().rename("y").reset_index())
    cells = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")["h3"].unique()
    shifts = list(SHIFT_SLOTS)
    dates = sorted(obs["date"].unique())
    hist = pd.DataFrame(itertools.product(cells, dates, shifts),
                        columns=["h3", "date", "shift"]).merge(
        obs, on=["h3", "date", "shift"], how="left")
    hist["y"] = hist["y"].fillna(0.0)
    max_date = pd.to_datetime(dates[-1])
    next_date = max_date + pd.Timedelta(days=1)
    fut = pd.DataFrame(itertools.product(cells, [next_date.date().isoformat()], shifts),
                       columns=["h3", "date", "shift"])
    fut["y"] = np.nan
    panel = pd.concat([hist, fut], ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    panel["shift_code"] = panel["shift"].map({s: i for i, s in enumerate(shifts)})
    panel = panel.sort_values(["h3", "shift", "date"])
    grp = panel.groupby(["h3", "shift"], sort=False)["y"]
    panel["lag1"] = grp.shift(1)
    panel["lag7"] = grp.shift(7)
    panel["roll28"] = grp.transform(lambda s: s.shift(1).rolling(28, min_periods=1).mean())
    panel["expmean"] = grp.transform(lambda s: s.shift(1).expanding().mean())
    panel["dow"] = panel["date"].dt.dayofweek
    panel["is_weekend"] = (panel["dow"] >= 5).astype(int)
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "cis", "f_road", "lat", "lon"]]
    panel = panel.merge(cis, on="h3", how="left")
    for c in ["lag1", "lag7", "roll28", "expmean"]:
        panel[c] = panel[c].fillna(0.0)
    return panel, next_date


def run_lgbm() -> pd.DataFrame:
    import lightgbm as lgb
    panel, next_date = _build_grid()
    hist = panel[panel["y"].notna()]
    fut = panel[panel["y"].isna()].copy()
    train = hist[hist["date"] < pd.Timestamp(SPLIT["train_end"])]
    val = hist[(hist["date"] >= pd.Timestamp(SPLIT["train_end"])) &
               (hist["date"] < pd.Timestamp(SPLIT["val_end"]))]
    test = hist[hist["date"] > pd.Timestamp(SPLIT["val_end"])].copy()

    model = lgb.LGBMRegressor(
        objective="tweedie", tweedie_variance_power=1.2, n_estimators=600,
        learning_rate=0.05, num_leaves=63, min_child_samples=100,
        subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=-1)
    model.fit(train[FEATURES], train["y"],
              eval_set=[(val[FEATURES], val["y"])],
              callbacks=[lgb.early_stopping(40, verbose=False)])

    test["pred"] = model.predict(test[FEATURES]).clip(min=0)
    actual = test.groupby("h3")["y"].sum().to_dict()
    pred_agg = test.groupby("h3")["pred"].sum().to_dict()
    p20_lgbm = precision_at_k(actual, pred_agg, 20)
    naive_map = train.groupby(["h3", "dow", "shift"])["y"].mean().rename("naive")
    t2 = test.merge(naive_map, on=["h3", "dow", "shift"], how="left")
    naive_agg = t2.groupby("h3")["naive"].sum().to_dict()
    p20_naive = precision_at_k(actual, naive_agg, 20)

    fut["pred"] = model.predict(fut[FEATURES]).clip(min=0)
    fut["date"] = next_date.date().isoformat()
    fut["pred_intensity"] = fut["pred"]
    fut["expected_violations"] = fut["pred"].round().astype(int)
    out = fut[schema.FORECAST]
    out.to_parquet(ARTIFACTS / "forecast.parquet")
    json.dump({"naive_precision_at_20": p20_naive, "precision_at_20": p20_lgbm},
              open(ARTIFACTS / "_forecast_metrics.json", "w"))
    print(f"LightGBM forecast written. Precision@20: LGBM={p20_lgbm:.2f} "
          f"vs naive={p20_naive:.2f} (best_iter={model.best_iteration_})")
    return out


def run_best() -> pd.DataFrame:
    try:
        return run_lgbm()
    except Exception as e:
        print(f"LightGBM unavailable ({e}); falling back to seasonal-naive.")
        return run()


if __name__ == "__main__":
    run_best()
