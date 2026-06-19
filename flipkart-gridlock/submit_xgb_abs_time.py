"""Notebook-inspired XGBoost candidate using absolute time.

The Kaggle notebook's transferable idea is an absolute time coordinate rather
than only within-day minutes. This script adapts that idea to our richer feature
set and writes standalone plus micro-blended candidates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from src.pipeline import FEATURES, add_hist_features, load_raw, prepare
from src.spatial import add_neighbor_feature, build_spatial_index

ANCHOR_PATH = "submissions/sub_gbm.csv"
OUT_PATH = "submissions/sub_xgb_abs_time.csv"
BLEND_WEIGHTS = [0.03, 0.05, 0.08, 0.10, 0.15, 0.20]


def add_abs_time(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["abs_time"] = df["day"] * 1440 + df["minutes"]
    return df


def write(tec: pd.DataFrame, pred: np.ndarray, path: str) -> None:
    pred = np.clip(np.asarray(pred, dtype=float), 0.0, 1.0)
    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": pred})
    assert out.shape == (41778, 2)
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    assert np.isfinite(out["demand"]).all()
    assert out["demand"].between(0, 1).all()
    out.to_csv(path, index=False)
    print(f"wrote {path} mean={pred.mean():.5f} min={pred.min():.5f} max={pred.max():.5f}")


def main() -> None:
    tr_raw, te_raw = load_raw()
    trc, tec, agg, _ = prepare(tr_raw, te_raw)
    sp = build_spatial_index(trc, k=12)

    d48 = add_abs_time(
        add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg)
    )
    test = add_abs_time(
        add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg)
    )

    cols = FEATURES + ["abs_time", "day"]
    model = XGBRegressor(
        n_estimators=700,
        learning_rate=0.03,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=2.0,
        objective="reg:squarederror",
        n_jobs=-1,
        random_state=7,
    )
    model.fit(d48[cols], d48["demand"])
    pred_xgb = model.predict(test[cols])
    write(tec, pred_xgb, OUT_PATH)

    anchor = pd.read_csv(ANCHOR_PATH)
    assert (anchor["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    a = anchor["demand"].to_numpy(dtype=float)
    x = np.clip(pred_xgb, 0.0, 1.0)
    for w in BLEND_WEIGHTS:
        pred = (1.0 - w) * a + w * x
        write(tec, pred, f"submissions/sub_micro_xgb_abs_time_w{int(w * 100):02d}.csv")


if __name__ == "__main__":
    main()
