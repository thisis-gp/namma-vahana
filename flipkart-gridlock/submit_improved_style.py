"""Submission candidates based on the user's improved XGBoost notebook.

Core method:
- timestamp split + cyclic hour features
- geohash lat/lon
- full-train geohash demand mean/std target encoding
- one-hot low-cardinality categoricals
- XGBoost with random validation early stopping

This script also writes all-train refit and micro-blends for leaderboard A/B.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pygeohash as pgh
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split

DATA_DIR = Path("dataset")
SUB_DIR = Path("submissions")
ANCHOR = SUB_DIR / "sub_gbm.csv"


def _decode_lat(gh: str) -> float:
    return float(pgh.decode(gh)[0])


def _decode_lon(gh: str) -> float:
    return float(pgh.decode(gh)[1])


def engineer_features(
    df: pd.DataFrame,
    geohash_stats: pd.DataFrame,
    temp_fill: float,
    weather_fill: str,
    road_fill: str,
) -> pd.DataFrame:
    out = df.copy()
    hhmm = out["timestamp"].str.split(":", expand=True).astype(int)
    out["hour"] = hhmm[0]
    out["minute"] = hhmm[1]
    out["time_of_day"] = out["hour"] * 60 + out["minute"]
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["is_peak"] = out["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)
    out["lat"] = out["geohash"].map(_decode_lat)
    out["lon"] = out["geohash"].map(_decode_lon)
    out["g5"] = out["geohash"].str[:5]

    out = out.merge(geohash_stats, on="geohash", how="left")
    out["geohash_mean"] = out["geohash_mean"].fillna(geohash_stats["geohash_mean"].mean())
    out["geohash_std"] = out["geohash_std"].fillna(0.0)

    out["lanes_x_highway"] = out["NumberofLanes"] * (out["RoadType"] == "Highway").astype(int)
    out["Temperature"] = out["Temperature"].fillna(temp_fill)
    out["Weather"] = out["Weather"].fillna(weather_fill)
    out["RoadType"] = out["RoadType"].fillna(road_fill)

    out = out.drop(columns=["timestamp", "geohash", "g5"])
    out = pd.get_dummies(
        out,
        columns=["RoadType", "LargeVehicles", "Landmarks", "Weather"],
        drop_first=True,
    )
    return out


def engineer_features_notebook_exact(
    df: pd.DataFrame,
    geohash_stats: pd.DataFrame | None = None,
    is_train: bool = True,
):
    """Mirror the improved notebook's feature engineering exactly."""
    out = df.copy()
    out[["hour", "minute"]] = out["timestamp"].str.split(":", expand=True).astype(int)
    out["time_of_day"] = out["hour"] * 60 + out["minute"]
    out = out.drop(columns=["timestamp"])

    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["is_peak"] = out["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)
    out["lat"] = out["geohash"].map(_decode_lat)
    out["lon"] = out["geohash"].map(_decode_lon)

    if is_train:
        geohash_stats = (
            out.groupby("geohash")["demand"]
            .agg(geohash_mean="mean", geohash_std="std")
            .reset_index()
        )
        geohash_stats["geohash_std"] = geohash_stats["geohash_std"].fillna(0)

    out = out.merge(geohash_stats, on="geohash", how="left")
    global_mean = geohash_stats["geohash_mean"].mean()
    out["geohash_mean"] = out["geohash_mean"].fillna(global_mean)
    out["geohash_std"] = out["geohash_std"].fillna(0)
    out = out.drop(columns=["geohash"])

    out["lanes_x_highway"] = out["NumberofLanes"] * (out["RoadType"] == "Highway").astype(int)
    out["Temperature"] = out["Temperature"].fillna(out["Temperature"].median())
    out["Weather"] = out["Weather"].fillna(out["Weather"].mode()[0])
    out["RoadType"] = out["RoadType"].fillna(out["RoadType"].mode()[0])
    out = pd.get_dummies(
        out,
        columns=["RoadType", "LargeVehicles", "Landmarks", "Weather"],
        drop_first=True,
    )

    if is_train:
        return out, geohash_stats
    return out


def make_matrix(train: pd.DataFrame, test: pd.DataFrame):
    geohash_stats = (
        train.groupby("geohash")["demand"]
        .agg(geohash_mean="mean", geohash_std="std")
        .reset_index()
    )
    geohash_stats["geohash_std"] = geohash_stats["geohash_std"].fillna(0.0)

    # Match the notebook's spirit: these fills are learned from available data.
    temp_fill = float(train["Temperature"].median())
    weather_fill = train["Weather"].mode(dropna=True)[0]
    road_fill = train["RoadType"].mode(dropna=True)[0]

    tr_fe = engineer_features(train, geohash_stats, temp_fill, weather_fill, road_fill)
    te_fe = engineer_features(test, geohash_stats, temp_fill, weather_fill, road_fill)

    y = tr_fe["demand"].to_numpy(dtype=float)
    X = tr_fe.drop(columns=["demand", "Index"])
    te_index = te_fe["Index"].to_numpy()
    Xtest = te_fe.drop(columns=["Index"])
    Xtest = Xtest.reindex(columns=X.columns, fill_value=0)
    return X, y, Xtest, te_index


def make_matrix_notebook_exact(train: pd.DataFrame, test: pd.DataFrame):
    tr_fe, geohash_stats = engineer_features_notebook_exact(train, is_train=True)
    te_fe = engineer_features_notebook_exact(test, geohash_stats=geohash_stats, is_train=False)
    y = tr_fe["demand"].to_numpy(dtype=float)
    X = tr_fe.drop(columns=["demand", "Index"])
    te_index = te_fe["Index"].to_numpy()
    Xtest = te_fe.drop(columns=["Index"])
    Xtest = Xtest.reindex(columns=X.columns, fill_value=0)
    return X, y, Xtest, te_index


def xgb_model(n_estimators: int = 2000, early_stopping_rounds: int | None = 50):
    kwargs = dict(
        n_estimators=n_estimators,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        tree_method="hist",
        random_state=42,
        objective="reg:squarederror",
        n_jobs=-1,
    )
    if early_stopping_rounds is not None:
        kwargs["early_stopping_rounds"] = early_stopping_rounds
    return XGBRegressor(**kwargs)


def write(index: np.ndarray, pred: np.ndarray, path: Path) -> None:
    pred = np.clip(np.asarray(pred, dtype=float), 0.0, 1.0)
    out = pd.DataFrame({"Index": index, "demand": pred})
    assert out.shape == (41778, 2)
    assert np.isfinite(out["demand"]).all()
    assert out["demand"].between(0, 1).all()
    out.to_csv(path, index=False)
    print(f"wrote {path} mean={pred.mean():.5f} min={pred.min():.5f} max={pred.max():.5f}")


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    X_exact, y_exact, Xtest_exact, test_index_exact = make_matrix_notebook_exact(train, test)

    X_train, X_valid, y_train, y_valid = train_test_split(
        X_exact, y_exact, test_size=0.2, random_state=42
    )

    model = xgb_model()
    model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
    best_iter = int(getattr(model, "best_iteration", model.n_estimators - 1)) + 1
    print(f"random early-stop best_iter={best_iter}")

    pred_notebook_exact = model.predict(Xtest_exact)
    write(test_index_exact, pred_notebook_exact, SUB_DIR / "sub_improved_notebook_exact.csv")

    # Also keep the train-fill variant from earlier experiments for A/B.
    X, y, Xtest, test_index = make_matrix(train, test)
    model_train_fill = xgb_model()
    X_train_tf, X_valid_tf, y_train_tf, y_valid_tf = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model_train_fill.fit(
        X_train_tf,
        y_train_tf,
        eval_set=[(X_valid_tf, y_valid_tf)],
        verbose=False,
    )
    pred_exact_style = model_train_fill.predict(Xtest)
    write(test_index, pred_exact_style, SUB_DIR / "sub_improved_style_random_es.csv")

    # Refit on all available labels at the learned complexity.
    all_model = xgb_model(n_estimators=best_iter, early_stopping_rounds=None)
    all_model.fit(X, y, verbose=False)
    pred_all = all_model.predict(Xtest)
    write(test_index, pred_all, SUB_DIR / f"sub_improved_style_all_{best_iter}.csv")

    if ANCHOR.exists():
        anchor = pd.read_csv(ANCHOR)
        assert (anchor["Index"].to_numpy() == test_index).all()
        a = anchor["demand"].to_numpy(dtype=float)
        for name, pred in [("random_es", pred_exact_style), ("all", pred_all)]:
            p = np.clip(pred, 0.0, 1.0)
            for w in [0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50]:
                blend = (1.0 - w) * a + w * p
                write(test_index, blend, SUB_DIR / f"sub_micro_improved_{name}_w{int(w * 100):02d}.csv")


if __name__ == "__main__":
    main()
