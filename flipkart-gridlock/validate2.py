"""Iteration-2 selection harness. Evaluate LightGBM param configs on two honest
brackets of Day 48 (the leaderboard sits between them):
  - random 20% holdout  -> optimistic bound (early-stopped; gives best_iter)
  - testhours holdout    -> pessimistic bound (train non-2:15-13:45, predict the band)
Pick the config best on BOTH, paste its override into model.py PARAMS, set
submit.py BEST_ITER = its rand_iter, then regenerate submissions.
"""
import numpy as np
from sklearn.metrics import r2_score
from src.pipeline import load_raw, prepare, add_hist_features, FEATURES, CAT_COLS
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm, PARAMS

TESTBAND = set(range(135, 826))  # 2:15-13:45 (matches real test hours)

CONFIGS = {
    "current(PARAMS)": {},  # whatever model.py PARAMS is right now (reg_A3 baseline)
    "cap255":  dict(num_leaves=255,  min_child_samples=10, lambda_l2=1.0),
    "cap511":  dict(num_leaves=511,  min_child_samples=5,  lambda_l2=1.0),
    "cap511r": dict(num_leaves=511,  min_child_samples=5,  lambda_l2=0.5,
                    feature_fraction=0.9, bagging_fraction=0.9),
    "cap1023": dict(num_leaves=1023, min_child_samples=3,  lambda_l2=0.5),
}


def main():
    tr, te = load_raw()
    trc, _tec, agg, _tm = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg)
    cat = [FEATURES.index(c) for c in CAT_COLS]
    X = d48[FEATURES]; y = d48["demand"].to_numpy()

    rng = np.random.RandomState(0)
    rmask = rng.rand(len(d48)) < 0.8                       # random 80/20
    tb = d48["minutes"].isin(TESTBAND).to_numpy()          # testhours band

    print(f"{'config':16s} {'rand_iter':>9} {'rand_R2':>8} {'testhrs_R2':>10}")
    results = []
    for name, ov in CONFIGS.items():
        p = {**PARAMS, **ov}
        # random holdout, early-stopped -> best_iter + optimistic R2
        mr, bit = train_gbm(X[rmask], y[rmask], cat, eval_X=X[~rmask], eval_y=y[~rmask],
                            use_log=True, params=p)
        rand_r2 = r2_score(y[~rmask], predict_gbm(mr, X[~rmask]))
        # testhours holdout at the same iteration count -> pessimistic R2
        mt, _ = train_gbm(X[~tb], y[~tb], cat, use_log=True, num_boost_round=bit, params=p)
        th_r2 = r2_score(y[tb], predict_gbm(mt, X[tb]))
        results.append((name, bit, rand_r2, th_r2, ov))
        print(f"{name:16s} {bit:9d} {rand_r2:8.4f} {th_r2:10.4f}")

    # winner = best average of the two brackets, excluding the current baseline row
    cand = [r for r in results if r[0] != "current(PARAMS)"]
    best = max(cand, key=lambda r: r[2] + r[3])
    print(f"\nBEST: {best[0]}  rand={best[2]:.4f}  testhrs={best[3]:.4f}  rand_iter={best[1]}")
    print(f"  override = {best[4]}")
    print("DECISION: if BEST beats current on BOTH brackets, paste override into")
    print("          model.py PARAMS and set submit.py BEST_ITER = rand_iter; else keep current.")


if __name__ == "__main__":
    main()
