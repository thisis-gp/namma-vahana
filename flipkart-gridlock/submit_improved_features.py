"""Feature-addition experiments around improved_notebook.ipynb.

Adds conservative signals to the user's winning XGBoost setup:
- absolute time coordinate
- g5 prefix target mean/std
- road-type range clipping as post-processing
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from submit_improved_style import DATA_DIR, SUB_DIR, write

ROAD_BOUNDS = {
    "Residential": (0.0, 0.22),
    "Street": (0.22, 0.35),
    "Highway": (0.35, 1.0),
}


def add_features(train: pd.DataFrame, test: pd.DataFrame):
    import pygeohash as pgh

    def fe(df: pd.DataFrame, gh_stats: pd.DataFrame, g5_stats: pd.DataFrame, is_train: bool):
        out = df.copy()
        hm = out["timestamp"].str.split(":", expand=True).astype(int)
        out["hour"] = hm[0]
        out["minute"] = hm[1]
        out["time_of_day"] = out["hour"] * 60 + out["minute"]
        out["abs_time"] = out["day"] * 1440 + out["time_of_day"]
        out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
        out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
        out["is_peak"] = out["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)
        out["lat"] = out["geohash"].map(lambda x: float(pgh.decode(x)[0]))
        out["lon"] = out["geohash"].map(lambda x: float(pgh.decode(x)[1]))
        out["g5"] = out["geohash"].str[:5]

        out = out.merge(gh_stats, on="geohash", how="left")
        out = out.merge(g5_stats, on="g5", how="left")
        out["geohash_mean"] = out["geohash_mean"].fillna(gh_stats["geohash_mean"].mean())
        out["geohash_std"] = out["geohash_std"].fillna(0)
        out["g5_mean"] = out["g5_mean"].fillna(g5_stats["g5_mean"].mean())
        out["g5_std"] = out["g5_std"].fillna(0)

        out["lanes_x_highway"] = out["NumberofLanes"] * (out["RoadType"] == "Highway").astype(int)
        out["Temperature"] = out["Temperature"].fillna(out["Temperature"].median())
        out["Weather"] = out["Weather"].fillna(out["Weather"].mode()[0])
        out["RoadType"] = out["RoadType"].fillna(out["RoadType"].mode()[0])
        out = out.drop(columns=["timestamp", "geohash", "g5"])
        out = pd.get_dummies(
            out,
            columns=["RoadType", "LargeVehicles", "Landmarks", "Weather"],
            drop_first=True,
        )
        return out

    gh_stats = train.groupby("geohash")["demand"].agg(
        geohash_mean="mean", geohash_std="std"
    ).reset_index()
    gh_stats["geohash_std"] = gh_stats["geohash_std"].fillna(0)
    train_g5 = train.assign(g5=train["geohash"].str[:5])
    g5_stats = train_g5.groupby("g5")["demand"].agg(g5_mean="mean", g5_std="std").reset_index()
    g5_stats["g5_std"] = g5_stats["g5_std"].fillna(0)

    tr = fe(train, gh_stats, g5_stats, True)
    te = fe(test, gh_stats, g5_stats, False)
    y = tr["demand"].to_numpy(float)
    X = tr.drop(columns=["demand", "Index"])
    Xtest = te.drop(columns=["Index"]).reindex(columns=X.columns, fill_value=0)
    return X, y, Xtest, test["Index"].to_numpy(), test


def model(seed: int):
    return XGBRegressor(
        n_estimators=2000,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        tree_method="hist",
        random_state=seed,
        objective="reg:squarederror",
        n_jobs=-1,
        early_stopping_rounds=50,
    )


def clip_by_road(raw_test: pd.DataFrame, pred: np.ndarray) -> np.ndarray:
    out = np.asarray(pred, dtype=float).copy()
    for rt, (lo, hi) in ROAD_BOUNDS.items():
        mask = raw_test["RoadType"].fillna("Residential").to_numpy() == rt
        out[mask] = np.clip(out[mask], lo, hi)
    return np.clip(out, 0.0, 1.0)


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    X, y, Xtest, index, raw_test = add_features(train, test)

    preds = []
    for seed in [23, 42, 71]:
        Xtr, Xv, ytr, yv = train_test_split(X, y, test_size=0.2, random_state=seed)
        m = model(seed)
        m.fit(Xtr, ytr, eval_set=[(Xv, yv)], verbose=False)
        p = np.clip(m.predict(Xtest), 0.0, 1.0)
        preds.append(p)
        write(index, p, SUB_DIR / f"sub_improved_feat_seed{seed}.csv")
        write(index, clip_by_road(raw_test, p), SUB_DIR / f"sub_improved_feat_seed{seed}_rtclip.csv")

    ens = np.mean(preds, axis=0)
    write(index, ens, SUB_DIR / "sub_improved_feat_ens.csv")
    write(index, clip_by_road(raw_test, ens), SUB_DIR / "sub_improved_feat_ens_rtclip.csv")


if __name__ == "__main__":
    main()
