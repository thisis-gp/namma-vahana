"""Experiment A: regularization sweep to reduce the train-valid overfit gap.
Build features once (train Day 48, eval Day 49), evaluate several LightGBM param
configs. Keeps nothing automatically -- prints a table; you pick the winner
(highest valid R2; tie-break smaller gap) and paste it into model.py PARAMS.
"""
import numpy as np
from sklearn.metrics import r2_score
from src.pipeline import load_raw, prepare, add_hist_features, FEATURES, CAT_COLS
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm, PARAMS

CONFIGS = {
    "baseline": dict(num_leaves=63, min_child_samples=40,  lambda_l2=1.0),
    "reg_A1":   dict(num_leaves=31, min_child_samples=80,  lambda_l2=3.0),
    "reg_A2":   dict(num_leaves=31, min_child_samples=120, lambda_l2=5.0,
                     feature_fraction=0.7, bagging_fraction=0.7),
    "reg_A3":   dict(num_leaves=15, min_child_samples=100, lambda_l2=5.0),
    "reg_A4":   dict(num_leaves=31, min_child_samples=60,  lambda_l2=2.0,
                     learning_rate=0.02),
}


def main():
    tr, te = load_raw()
    trc, _tec, agg, _tm = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 49].copy(), agg, False), sp, agg)
    cat_idx = [FEATURES.index(c) for c in CAT_COLS]
    Xtr, ytr = d48[FEATURES], d48["demand"].to_numpy()
    Xva, yva = d49[FEATURES], d49["demand"].to_numpy()

    print(f"{'config':10s} {'train':>7} {'valid':>7} {'gap':>8} {'iters':>6}")
    rows = []
    for name, override in CONFIGS.items():
        params = {**PARAMS, **override}
        model, best_iter = train_gbm(Xtr, ytr, cat_idx, eval_X=Xva, eval_y=yva,
                                     use_log=True, params=params)
        r2tr = r2_score(ytr, predict_gbm(model, Xtr))
        r2va = r2_score(yva, predict_gbm(model, Xva))
        rows.append((name, r2va, r2tr - r2va, best_iter, override))
        print(f"{name:10s} {r2tr:7.4f} {r2va:7.4f} {r2tr-r2va:+8.4f} {best_iter:6d}")

    best = max(rows, key=lambda r: r[1])
    print(f"\nBEST valid R2: {best[0]}  valid={best[1]:.4f}  gap={best[2]:+.4f}  best_iter={best[3]}")
    print(f"  override = {best[4]}")
    print("DECISION: if best valid > 0.7590, paste its override into model.py PARAMS")
    print("          and set submit.py BEST_ITER = best_iter; else keep baseline.")


if __name__ == "__main__":
    main()
