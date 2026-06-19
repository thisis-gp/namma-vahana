"""Best-evidence candidate: bundles all validated gains over the LB-90 model.

Changes vs sub_gbm.csv (each validated; both proxies agree, which is rare here):
  1. Train on Day-48 + Day-49 morning labels   (banked +0.2 LB)
  2. Raw target instead of log1p   (fixes systematic underprediction of high-demand
     Highway/Street rows; log1p + expm1 shrinks them via Jensen's inequality)
  3. Sample weight 1 + 3*demand   (RMSE was dominated by 88% low-demand residential
     rows; this makes the fit serve the high-demand rows that drive R²)
  4. 6-seed ensemble   (pure variance reduction)

Morning holdout: 0.884 -> 0.899 ; testhours holdout: 0.840 -> 0.850.
Writes a distinct CSV; leaves sub_gbm.csv and sub_gbm_d49train.csv intact.
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
WEIGHT_EXP = 3.0   # sample weight = 1 + WEIGHT_EXP * demand


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
    y = train_df["demand"].to_numpy()          # raw target, no log
    w = 1.0 + WEIGHT_EXP * y
    Xte = test[FEATURES]

    preds = np.zeros(len(test))
    for seed in range(N_SEEDS):
        params = {**PARAMS, "seed": seed, "bagging_seed": seed, "feature_fraction_seed": seed}
        booster = lgb.train(params, lgb.Dataset(X, y, weight=w, categorical_feature=cat_idx),
                            num_boost_round=BEST_ITER, callbacks=[lgb.log_evaluation(0)])
        preds += np.clip(booster.predict(Xte), 0.0, 1.0)
    preds /= N_SEEDS

    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": preds})
    assert out.shape == (41778, 2), out.shape
    assert list(out.columns) == ["Index", "demand"]
    assert np.isfinite(out["demand"]).all()
    assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all()
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    path = "submissions/sub_bundle.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path}  mean={preds.mean():.4f} min={preds.min():.4f} max={preds.max():.4f}")

    for ref in ["sub_gbm.csv", "sub_gbm_d49train.csv"]:
        b = pd.read_csv(f"submissions/{ref}")["demand"].to_numpy()
        print(f"  vs {ref:22s} mean diff={preds.mean()-b.mean():+.4f}  "
              f"mean abs={np.abs(preds-b).mean():.4f}  corr={np.corrcoef(preds, b)[0,1]:.4f}")


if __name__ == "__main__":
    main()
