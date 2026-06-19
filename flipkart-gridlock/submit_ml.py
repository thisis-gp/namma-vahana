"""ML-only submission — no lookup, no blend. Pure learned model."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.pipeline import load_raw, prepare, add_hist_features
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import (
    train_gbm, predict_gbm, train_residual_gbm, predict_residual_gbm,
)
from src.ml_features import (
    FEATURES, FEATURES_V2, RESIDUAL_FEATURES,
    build_geohash_profiles, enrich_ml_features, cat_idx_for,
)

# Set from validate_ml_v2.py output
MODEL = "baseline"  # testhours winner; v2/residual did not beat baseline on 2:15-13:45
BEST_ITER = 245     # solution.ipynb LB ~90 (testhours early-stop suggested 209)
USE_LOG = True
TRAIN_ON_DAY49 = False


def _feature_cols():
    if MODEL == "baseline":
        return FEATURES
    if MODEL == "v2":
        return FEATURES_V2
    if MODEL == "residual":
        return RESIDUAL_FEATURES
    raise ValueError(f"unknown MODEL={MODEL!r}")


def main():
    cols = _feature_cols()
    tr, te = load_raw()
    trc, tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    prof = build_geohash_profiles(trc[trc["day"] == 48])

    d48 = enrich_ml_features(
        add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg),
        prof,
    )
    test = enrich_ml_features(
        add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg),
        prof,
    )
    if TRAIN_ON_DAY49:
        d49 = enrich_ml_features(
            add_neighbor_feature(add_hist_features(trc[trc["day"] == 49].copy(), agg, False), sp, agg),
            prof,
        )
        train_df = pd.concat([d48, d49], ignore_index=True)
    else:
        train_df = d48

    cat = cat_idx_for(cols)
    y = train_df["demand"].to_numpy()

    if MODEL == "residual":
        baseline = train_df["hist_g"].to_numpy()
        booster, _ = train_residual_gbm(
            train_df[cols], y, baseline, cat, num_boost_round=BEST_ITER,
        )
        pred = predict_residual_gbm(booster, test[cols], test["hist_g"].to_numpy())
    else:
        booster, _ = train_gbm(
            train_df[cols], y, cat, use_log=USE_LOG, num_boost_round=BEST_ITER,
        )
        pred = predict_gbm(booster, test[cols], use_log=USE_LOG)

    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": pred})
    assert out.shape == (41778, 2)
    assert np.isfinite(out["demand"]).all()
    assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all()
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    path = "submissions/sub_gbm.csv"
    out.to_csv(path, index=False)
    print(f"model={MODEL}  iter={BEST_ITER}")
    print(f"wrote {path}  mean={pred.mean():.4f} min={pred.min():.4f} max={pred.max():.4f}")


if __name__ == "__main__":
    main()
