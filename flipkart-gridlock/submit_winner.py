"""Train the compare_models.py winner on full train data and write test CSV."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from src.pipeline import (
    load_raw, prepare, add_hist_features, add_hist_gt, lookup_pred,
    FEATURES, CAT_COLS,
)
from src.spatial import build_spatial_index, add_neighbor_feature, neighbor_predict
from src.model import train_gbm, predict_gbm, PARAMS

FGT = FEATURES + ["hist_gt"]

GBM_CONFIGS = {
    "gbm_baseline":      dict(PARAMS),
    "gbm_cap511":        {**PARAMS, "num_leaves": 511, "min_child_samples": 5, "lambda_l2": 1.0},
    "gbm_cap1023":       {**PARAMS, "num_leaves": 1023, "min_child_samples": 3, "lambda_l2": 0.5},
    "gbm_cap1023_nolog": {**PARAMS, "num_leaves": 1023, "min_child_samples": 3, "lambda_l2": 0.5},
}


def _feat(df, agg, sp, is48):
    return add_neighbor_feature(add_hist_features(df, agg, is48), sp, agg)


def _feat_gt(df, agg, sp, is48):
    return add_hist_gt(_feat(df, agg, sp, is48), agg)


def _cat_idx(cols):
    return [cols.index(c) for c in CAT_COLS]


def _match_mask(df, gt_keys):
    return np.array([(g, t) in gt_keys for g, t in zip(df["geohash"], df["timestamp"])])


def _write(tec, preds, path):
    preds = np.clip(np.asarray(preds, dtype=float), 0.0, 1.0)
    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": preds})
    assert out.shape == (41778, 2)
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    out.to_csv(path, index=False)
    print(f"wrote {path}  mean={preds.mean():.4f} min={preds.min():.4f} max={preds.max():.4f}")


def predict_test(winner: str, stats: dict, trc, tec, agg, sp):
    d48 = _feat(trc[trc["day"] == 48].copy(), agg, sp, True)
    test = _feat(tec.copy(), agg, sp, False)
    y48 = d48["demand"].to_numpy()

    if winner in ("lookup_plain", "lookup_nb"):
        nb = neighbor_predict(test, sp) if winner == "lookup_nb" else None
        return lookup_pred(test, agg, neighbor=nb)

    if winner in GBM_CONFIGS:
        use_log = winner != "gbm_cap1023_nolog"
        p = GBM_CONFIGS[winner]
        bit = stats.get("best_iter_day49") or stats.get("best_iter_random") or 800
        cat = _cat_idx(FEATURES)
        m, _ = train_gbm(d48[FEATURES], y48, cat, use_log=use_log,
                         num_boost_round=int(bit), params=p)
        return predict_gbm(m, test[FEATURES], use_log=use_log)

    if winner == "blend_cap1023":
        w = stats.get("w_lookup_day49", stats.get("w_lookup_random", 0.0))
        p = GBM_CONFIGS["gbm_cap1023"]
        cat = _cat_idx(FEATURES)
        m, _ = train_gbm(d48[FEATURES], y48, cat, use_log=True, num_boost_round=800, params=p)
        pred_g = predict_gbm(m, test[FEATURES], use_log=True)
        pred_l = lookup_pred(test, agg)
        return w * pred_l + (1 - w) * pred_g

    if winner == "crossday_stack":
        d49 = trc[trc["day"] == 49].copy()
        d49_gt = _feat_gt(d49, agg, sp, False)
        test_gt = _feat_gt(tec.copy(), agg, sp, False)
        gt_keys = set(agg["gt"].index)
        is_match = _match_mask(test_gt, gt_keys)

        cat_gt = _cat_idx(FGT)
        p_cd = GBM_CONFIGS["gbm_cap1023"]
        cd_iter = stats.get("crossday_iter", 300)
        cd, _ = train_gbm(d49_gt[FGT], d49_gt["demand"].to_numpy(), cat_gt,
                          use_log=True, num_boost_round=int(cd_iter), params=p_cd)

        cat = _cat_idx(FEATURES)
        main_iter = stats.get("main_iter", 800)
        main, _ = train_gbm(d48[FEATURES], y48, cat, use_log=True,
                            num_boost_round=int(main_iter), params=p_cd)
        pred_cd = predict_gbm(cd, test_gt[FGT], use_log=True)
        pred_main = predict_gbm(main, test[FEATURES], use_log=True)
        return np.where(is_match, pred_cd, pred_main)

    if winner == "hist_gt_hybrid":
        test_gt = _feat_gt(tec.copy(), agg, sp, False)
        gt_keys = set(agg["gt"].index)
        is_match = _match_mask(test_gt, gt_keys)
        hist = test_gt["hist_gt"].to_numpy()
        p = GBM_CONFIGS["gbm_cap1023"]
        cat = _cat_idx(FEATURES)
        main, _ = train_gbm(d48[FEATURES], y48, cat, use_log=True,
                            num_boost_round=800, params=p)
        pred_main = predict_gbm(main, test[FEATURES], use_log=True)
        return np.where(is_match, hist, pred_main)

    raise ValueError(f"unknown winner: {winner}")


def main():
    with open("submissions/model_comparison.json") as f:
        comp = json.load(f)
    winner = comp["winner"]
    stats = comp["winner_stats"]
    print(f"Submitting winner: {winner}")

    tr, te = load_raw()
    trc, tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)

    preds = predict_test(winner, stats, trc, tec, agg, sp)
    _write(tec, preds, "submissions/sub_best.csv")
    _write(tec, preds, "submissions/sub_gbm.csv")  # overwrite primary candidate


if __name__ == "__main__":
    main()
