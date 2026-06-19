"""Experiment C (advanced, optional): cross-day exact-match model.
Train ONLY on Day-49 rows with hist_gt added (target=Day49, feature=Day48 ->
leak-free). Apply to the 37,136 matched test rows; use the main Day-48 GBM for
the rest. CANNOT be validated for daytime -- sanity-check on a Day-49 morning
split only, then treat the CSV as a leaderboard experiment.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from src.pipeline import (load_raw, prepare, add_hist_features, add_hist_gt,
                          FEATURES, CAT_COLS)
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm, PARAMS

MAIN_BEST_ITER = 223    # reg_A3 — early-stop on Day-49 morning (LB ~88.95)


def feats(df, agg, sp, is48):
    df = add_neighbor_feature(add_hist_features(df, agg, is48), sp, agg)
    return add_hist_gt(df, agg)


def main():
    tr, te = load_raw()
    trc, tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    FGT = FEATURES + ["hist_gt"]
    cat_gt = [FGT.index(c) for c in CAT_COLS]

    d49 = feats(trc[trc["day"] == 49].copy(), agg, sp, False)
    y49 = d49["demand"].to_numpy()

    # sanity check on a Day-49 morning 80/20 split (NOT a daytime guarantee)
    rng = np.random.RandomState(0)
    m = rng.rand(len(d49)) < 0.8
    chk, ci = train_gbm(d49[FGT][m], y49[m], cat_gt,
                        eval_X=d49[FGT][~m], eval_y=y49[~m],
                        use_log=False, params=PARAMS)
    r2 = r2_score(y49[~m], predict_gbm(chk, d49[FGT][~m]))
    print(f"cross-day model Day-49 morning holdout R2: {r2:.4f}  (sanity only, n={int((~m).sum())})")

    # final cross-day model on all Day-49
    final, _ = train_gbm(d49[FGT], y49, cat_gt, use_log=False, params=PARAMS,
                         num_boost_round=(chk.best_iteration or 300))
    test = feats(tec.copy(), agg, sp, False)
    pred_cd = predict_gbm(final, test[FGT], use_log=False)

    # main Day-48 GBM for the unmatched rows (reg_A3, identity link)
    d48 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg)
    d49_eval = add_neighbor_feature(add_hist_features(trc[trc["day"] == 49].copy(), agg, False), sp, agg)
    cat_main = [FEATURES.index(c) for c in CAT_COLS]
    main_gbm, _ = train_gbm(d48[FEATURES], d48["demand"].to_numpy(), cat_main,
                            eval_X=d49_eval[FEATURES], eval_y=d49_eval["demand"].to_numpy(),
                            use_log=False, params=PARAMS)
    pred_main = predict_gbm(main_gbm, test[FEATURES], use_log=False)

    # use cross-day only where the exact (geohash, timestamp) exists in Day 48
    gt_keys = set(agg["gt"].index)               # set of (geohash, timestamp) tuples
    is_match = np.array([(g, t) in gt_keys
                         for g, t in zip(test["geohash"], test["timestamp"])])
    pred = np.clip(np.where(is_match, pred_cd, pred_main), 0.0, 1.0)

    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": pred})
    assert out.shape == (41778, 2)
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    out.to_csv("submissions/sub_crossday.csv", index=False)
    print(f"wrote submissions/sub_crossday.csv  matched={int(is_match.sum())}/{len(test)}  mean={pred.mean():.4f}")


if __name__ == "__main__":
    main()
