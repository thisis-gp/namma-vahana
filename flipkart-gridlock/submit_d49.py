"""A/B candidate: train on Day-48 + Day-49 morning labels (6-seed ensemble).

Rationale (measured 2026-06-05): the LB-90 model trains on Day-48 ONLY, discarding
the 7,872 Day-49 morning labels. Adding them lifts held-out Day-49 R2 0.77 -> 0.88,
a gain driven by a per-geohash Day-49 level adjustment that transfers to 97.8% of
test rows (their geohash appears in the Day-49 morning data). Seed-ensembling is
pure variance reduction on top. Writes a distinct CSV; does NOT touch sub_gbm.csv.
"""
import numpy as np
import pandas as pd
import lightgbm as lgb
from src.pipeline import (load_raw, prepare, add_hist_features,
                          FEATURES, CAT_COLS)
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import PARAMS

BEST_ITER = 245
N_SEEDS = 6


def main():
    tr, te = load_raw()
    trc, tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)

    d48 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 49].copy(), agg, False), sp, agg)
    test = add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg)
    train_df = pd.concat([d48, d49], ignore_index=True)

    cat_idx = [FEATURES.index(c) for c in CAT_COLS]
    X = train_df[FEATURES]
    y = np.log1p(train_df["demand"].to_numpy())
    Xte = test[FEATURES]

    preds = np.zeros(len(test))
    for seed in range(N_SEEDS):
        params = {**PARAMS, "seed": seed, "bagging_seed": seed, "feature_fraction_seed": seed}
        booster = lgb.train(params, lgb.Dataset(X, y, categorical_feature=cat_idx),
                            num_boost_round=BEST_ITER, callbacks=[lgb.log_evaluation(0)])
        preds += np.clip(np.expm1(booster.predict(Xte)), 0.0, 1.0)
    preds /= N_SEEDS

    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": preds})
    assert out.shape == (41778, 2), out.shape
    assert list(out.columns) == ["Index", "demand"]
    assert np.isfinite(out["demand"]).all()
    assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all()
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    path = "submissions/sub_gbm_d49train.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path}  mean={preds.mean():.4f} min={preds.min():.4f} max={preds.max():.4f}")

    base = pd.read_csv("submissions/sub_gbm.csv")["demand"].to_numpy()
    print(f"vs anchor sub_gbm.csv: mean Δ={preds.mean()-base.mean():+.4f}  "
          f"mean|Δ|={np.abs(preds-base).mean():.4f}  corr={np.corrcoef(preds, base)[0,1]:.4f}")


if __name__ == "__main__":
    main()
