from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pygeohash as pgh
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


DATA_DIR = Path("dataset")
SUB_DIR = Path("submissions")
SUB_DIR.mkdir(exist_ok=True)


CONFIGS = [
    ("base", dict(learning_rate=0.05, max_depth=6, min_child_weight=3, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0)),
    ("d5_lr03", dict(learning_rate=0.03, max_depth=5, min_child_weight=3, subsample=0.85, colsample_bytree=0.85, reg_alpha=0.1, reg_lambda=1.5)),
    ("d5_lr04", dict(learning_rate=0.04, max_depth=5, min_child_weight=2, subsample=0.85, colsample_bytree=0.85, reg_alpha=0.05, reg_lambda=1.2)),
    ("d5_strongreg", dict(learning_rate=0.035, max_depth=5, min_child_weight=5, subsample=0.85, colsample_bytree=0.8, reg_alpha=0.3, reg_lambda=2.5)),
    ("d6_lr03", dict(learning_rate=0.03, max_depth=6, min_child_weight=3, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.5)),
    ("d6_lessreg", dict(learning_rate=0.04, max_depth=6, min_child_weight=2, subsample=0.9, colsample_bytree=0.85, reg_alpha=0.02, reg_lambda=0.8)),
    ("d6_child1", dict(learning_rate=0.04, max_depth=6, min_child_weight=1, subsample=0.85, colsample_bytree=0.8, reg_alpha=0.05, reg_lambda=1.0)),
    ("d6_child5", dict(learning_rate=0.04, max_depth=6, min_child_weight=5, subsample=0.85, colsample_bytree=0.85, reg_alpha=0.1, reg_lambda=2.0)),
    ("d7_lr025", dict(learning_rate=0.025, max_depth=7, min_child_weight=3, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.2, reg_lambda=2.0)),
    ("d7_lr035", dict(learning_rate=0.035, max_depth=7, min_child_weight=3, subsample=0.75, colsample_bytree=0.75, reg_alpha=0.3, reg_lambda=2.5)),
    ("d4_smooth", dict(learning_rate=0.04, max_depth=4, min_child_weight=3, subsample=0.9, colsample_bytree=0.9, reg_alpha=0.05, reg_lambda=1.0)),
    ("d4_lr025", dict(learning_rate=0.025, max_depth=4, min_child_weight=2, subsample=0.95, colsample_bytree=0.9, reg_alpha=0.0, reg_lambda=0.8)),
]


def decode_lat(gh: str) -> float:
    return pgh.decode(gh)[0]


def decode_lon(gh: str) -> float:
    return pgh.decode(gh)[1]


def engineer_features(df: pd.DataFrame, geohash_stats: pd.DataFrame | None = None, is_train: bool = True):
    df = df.copy()
    df[["hour", "minute"]] = df["timestamp"].str.split(":", expand=True).astype(int)
    df["time_of_day"] = df["hour"] * 60 + df["minute"]
    df.drop("timestamp", axis=1, inplace=True)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["is_peak"] = df["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)

    df["lat"] = df["geohash"].apply(decode_lat)
    df["lon"] = df["geohash"].apply(decode_lon)

    if is_train:
        geohash_stats = (
            df.groupby("geohash")["demand"]
            .agg(geohash_mean="mean", geohash_std="std")
            .reset_index()
        )
        geohash_stats["geohash_std"] = geohash_stats["geohash_std"].fillna(0)

    assert geohash_stats is not None
    df = df.merge(geohash_stats, on="geohash", how="left")
    global_mean = geohash_stats["geohash_mean"].mean()
    df["geohash_mean"] = df["geohash_mean"].fillna(global_mean)
    df["geohash_std"] = df["geohash_std"].fillna(0)
    df.drop("geohash", axis=1, inplace=True)

    df["lanes_x_highway"] = df["NumberofLanes"] * (df["RoadType"] == "Highway").astype(int)
    df["Temperature"] = df["Temperature"].fillna(df["Temperature"].median())
    df["Weather"] = df["Weather"].fillna(df["Weather"].mode()[0])
    df["RoadType"] = df["RoadType"].fillna(df["RoadType"].mode()[0])

    df = pd.get_dummies(
        df,
        columns=["RoadType", "LargeVehicles", "Landmarks", "Weather"],
        drop_first=True,
    )
    if is_train:
        return df, geohash_stats
    return df


def make_xy(train: pd.DataFrame, test: pd.DataFrame | None = None):
    train_fe, stats = engineer_features(train, is_train=True)
    X = train_fe.drop(["demand", "Index"], axis=1)
    y = train_fe["demand"]
    if test is None:
        return X, y, None, None
    test_fe = engineer_features(test, geohash_stats=stats, is_train=False)
    Xtest = test_fe.drop(["Index"], axis=1).reindex(columns=X.columns, fill_value=0)
    return X, y, Xtest, test["Index"].copy()


def model_from(params: dict, seed: int = 42, n_estimators: int = 2500, early_stop: int | None = 80):
    kwargs = dict(
        n_estimators=n_estimators,
        objective="reg:squarederror",
        tree_method="hist",
        random_state=seed,
        n_jobs=-1,
        **params,
    )
    if early_stop is not None:
        kwargs["early_stopping_rounds"] = early_stop
    return XGBRegressor(**kwargs)


def random_score(X: pd.DataFrame, y: pd.Series, params: dict):
    Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.2, random_state=42)
    model = model_from(params)
    model.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    pred = np.clip(model.predict(Xva), 0, 1)
    return r2_score(yva, pred), int(getattr(model, "best_iteration", model.n_estimators - 1)) + 1


def temporal_score(train: pd.DataFrame, params: dict):
    day48 = train[train["day"] == 48].copy()
    day49 = train[train["day"] == 49].copy()
    Xtr, ytr, _, _ = make_xy(day48)
    train_fe, stats = engineer_features(day48, is_train=True)
    Xtr = train_fe.drop(["demand", "Index"], axis=1)
    ytr = train_fe["demand"]
    valid_fe = engineer_features(day49, geohash_stats=stats, is_train=False)
    Xva = valid_fe.drop(["demand", "Index"], axis=1).reindex(columns=Xtr.columns, fill_value=0)
    yva = valid_fe["demand"]
    Xfit, Xstop, yfit, ystop = train_test_split(Xtr, ytr, test_size=0.2, random_state=42)
    model = model_from(params)
    model.fit(Xfit, yfit, eval_set=[(Xstop, ystop)], verbose=False)
    pred = np.clip(model.predict(Xva), 0, 1)
    return r2_score(yva, pred), int(getattr(model, "best_iteration", model.n_estimators - 1)) + 1


def write_submission(index: pd.Series, pred: np.ndarray, path: Path) -> None:
    out = pd.DataFrame({"Index": index.to_numpy(), "demand": np.clip(pred, 0, 1)})
    assert out.shape == (41778, 2)
    assert list(out.columns) == ["Index", "demand"]
    assert out["Index"].equals(index.reset_index(drop=True))
    assert np.isfinite(out["demand"]).all()
    assert out["demand"].between(0, 1).all()
    out.to_csv(path, index=False)
    print(f"wrote {path} mean={out.demand.mean():.6f} std={out.demand.std():.6f}")


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    X, y, Xtest, test_index = make_xy(train, test)

    rows = []
    for name, params in CONFIGS:
        print(f"\n=== {name} ===")
        r2_rand, iter_rand = random_score(X, y, params)
        r2_temp, iter_temp = temporal_score(train, params)
        n_final = max(100, int(round((iter_rand + iter_temp) / 2)))
        rows.append(
            dict(
                name=name,
                random_r2=r2_rand,
                temporal_r2=r2_temp,
                iter_random=iter_rand,
                iter_temporal=iter_temp,
                n_final=n_final,
                **params,
            )
        )
        print(f"random_r2={r2_rand:.6f} iter={iter_rand} temporal_r2={r2_temp:.6f} iter={iter_temp} n_final={n_final}")

    summary = pd.DataFrame(rows).sort_values(["temporal_r2", "random_r2"], ascending=False)
    summary.to_csv(SUB_DIR / "improved_xgb_tuning_summary.csv", index=False)
    print("\nTOP CONFIGS")
    print(summary[["name", "random_r2", "temporal_r2", "iter_random", "iter_temporal", "n_final"]].to_string(index=False))

    for _, row in summary.head(5).iterrows():
        params = {k: row[k] for k in CONFIGS[0][1].keys()}
        name = row["name"]
        for n_final in [int(row["iter_random"]), int(row["n_final"])]:
            model = model_from(params, n_estimators=n_final, early_stop=None)
            model.fit(X, y, verbose=False)
            pred = model.predict(Xtest)
            write_submission(test_index, pred, SUB_DIR / f"sub_imp_tuned_{name}_{n_final}.csv")


if __name__ == "__main__":
    main()
