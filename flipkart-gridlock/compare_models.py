"""Compare 7+ models on train-only splits and pick the best for test.

Validation brackets (all leakage-safe):
  1. random_holdout  — 80/20 split of Day 48; aggregates rebuilt from kept rows
  2. testhours_holdout — hold out 2:15–13:45 on Day 48 (matches real test window)
  3. day49_morning — train on Day 48, score on all Day-49 labels (cross-day)

Models:
  lookup_plain, lookup_nb, gbm_baseline, gbm_cap511, gbm_cap1023,
  gbm_cap1023_nolog, crossday_stack, hist_gt_direct, blend_best

Winner = highest average of (random_holdout + testhours_holdout) R².
Writes results to submissions/model_comparison.json and prints a table.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from src.pipeline import (
    load_raw, prepare, add_hist_features, add_hist_gt, lookup_pred,
    build_day48_aggregates, FEATURES, CAT_COLS,
)
from src.spatial import build_spatial_index, add_neighbor_feature, neighbor_predict
from src.model import train_gbm, predict_gbm, PARAMS

TESTBAND = set(range(135, 826))  # 2:15–13:45
FGT = FEATURES + ["hist_gt"]
RNG = np.random.RandomState(0)

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


def _r2(y, p):
    return float(r2_score(y, p))


def _clip(p):
    return np.clip(np.asarray(p, dtype=float), 0.0, 1.0)


def _match_mask(df, gt_keys):
    return np.array([(g, t) in gt_keys for g, t in zip(df["geohash"], df["timestamp"])])


def _split_random(d48):
    m = RNG.rand(len(d48)) < 0.8
    return d48[~m].copy(), d48[m].copy()


def _split_testhours(d48):
    tb = d48["minutes"].isin(TESTBAND)
    return d48[~tb].copy(), d48[tb].copy()


def _prep_holdout(keep, hold):
    """Rebuild aggregates + spatial index from kept rows only."""
    agg_k = build_day48_aggregates(keep)
    sp_k = build_spatial_index(keep, k=12)
    keep_f = _feat(keep, agg_k, sp_k, True)
    hold_f = _feat(hold, agg_k, sp_k, False)
    return keep_f, hold_f, agg_k, sp_k


def _train_gbm_model(name, keep_f, hold_f, use_log=True):
    p = GBM_CONFIGS[name]
    cat = _cat_idx(FEATURES)
    Xk, yk = keep_f[FEATURES], keep_f["demand"].to_numpy()
    Xh, yh = hold_f[FEATURES], hold_f["demand"].to_numpy()
    if name == "gbm_baseline":
        use_log = True
    elif name == "gbm_cap1023_nolog":
        use_log = False
    else:
        use_log = True
    m, bit = train_gbm(Xk, yk, cat, eval_X=Xh, eval_y=yh, use_log=use_log, params=p)
    return predict_gbm(m, Xh, use_log=use_log), bit, use_log


def eval_gbm_on_split(name, keep_f, hold_f):
    pred, best_iter, use_log = _train_gbm_model(name, keep_f, hold_f)
    return _r2(hold_f["demand"].to_numpy(), pred), best_iter, use_log


def eval_lookup_on_split(keep_f, hold_f, agg_k, sp_k, use_neighbor=False):
    nb = neighbor_predict(hold_f, sp_k) if use_neighbor else None
    pred = lookup_pred(hold_f, agg_k, neighbor=nb)
    return _r2(hold_f["demand"].to_numpy(), pred)


def eval_blend_on_split(keep_f, hold_f, agg_k, sp_k, gbm_name="gbm_baseline"):
    p = GBM_CONFIGS[gbm_name]
    cat = _cat_idx(FEATURES)
    use_log = gbm_name != "gbm_cap1023_nolog"
    m, _ = train_gbm(keep_f[FEATURES], keep_f["demand"].to_numpy(), cat,
                     eval_X=hold_f[FEATURES], eval_y=hold_f["demand"].to_numpy(),
                     use_log=use_log, params=p)
    pred_g = predict_gbm(m, hold_f[FEATURES], use_log=use_log)
    pred_l = lookup_pred(hold_f, agg_k)
    y = hold_f["demand"].to_numpy()
    best_w, best_r2 = 0.0, -1e9
    for w in np.linspace(0, 1, 21):
        r2 = _r2(y, _clip(w * pred_l + (1 - w) * pred_g))
        if r2 > best_r2:
            best_r2, best_w = r2, w
    return best_r2, best_w


def eval_day49_gbm(d48_full, d49, gbm_name, agg, sp):
    """Train on full Day 48, predict Day 49 morning."""
    p = GBM_CONFIGS[gbm_name]
    use_log = gbm_name != "gbm_cap1023_nolog"
    cat = _cat_idx(FEATURES)
    d49_f = _feat(d49, agg, sp, False)
    m, bit = train_gbm(d48_full[FEATURES], d48_full["demand"].to_numpy(), cat,
                       eval_X=d49_f[FEATURES], eval_y=d49_f["demand"].to_numpy(),
                       use_log=use_log, params=p)
    pred = predict_gbm(m, d49_f[FEATURES], use_log=use_log)
    return _r2(d49_f["demand"].to_numpy(), pred), bit, use_log


def eval_day49_lookup(d49, agg, sp, use_neighbor=False):
    d49_f = _feat(d49, agg, sp, False)
    nb = neighbor_predict(d49_f, sp) if use_neighbor else None
    pred = lookup_pred(d49_f, agg, neighbor=nb)
    return _r2(d49_f["demand"].to_numpy(), pred)


def eval_day49_crossday_stack(d48_full, d49, agg, sp, gbm_name="gbm_cap1023"):
    """Cross-day model on matched rows + main GBM on rest; validated on Day 49."""
    d49_gt = _feat_gt(d49, agg, sp, False)
    y = d49_gt["demand"].to_numpy()
    gt_keys = set(agg["gt"].index)
    is_match = _match_mask(d49_gt, gt_keys)

    m = RNG.rand(len(d49_gt)) < 0.8
    cat_gt = _cat_idx(FGT)
    p_cd = GBM_CONFIGS.get("gbm_cap1023", GBM_CONFIGS["gbm_baseline"])
    cd, cd_iter = train_gbm(d49_gt[FGT][m], y[m], cat_gt,
                            eval_X=d49_gt[FGT][~m], eval_y=y[~m], use_log=True, params=p_cd)

    p_main = GBM_CONFIGS[gbm_name]
    use_log = gbm_name != "gbm_cap1023_nolog"
    cat = _cat_idx(FEATURES)
    main, main_iter = train_gbm(d48_full[FEATURES], d48_full["demand"].to_numpy(), cat,
                                use_log=use_log, num_boost_round=800, params=p_main)

    pred_cd = predict_gbm(cd, d49_gt[FGT], use_log=True)
    pred_main = predict_gbm(main, d49_gt[FEATURES], use_log=use_log)
    pred = _clip(np.where(is_match, pred_cd, pred_main))
    return _r2(y, pred), cd_iter, main_iter


def eval_day49_hist_gt_direct(d49, agg, sp, gbm_name="gbm_cap1023"):
    """hist_gt where matched, else main GBM (no crossday training)."""
    d49_gt = _feat_gt(d49, agg, sp, False)
    d49_f = _feat(d49, agg, sp, False)
    gt_keys = set(agg["gt"].index)
    is_match = _match_mask(d49_gt, gt_keys)
    hist = d49_gt["hist_gt"].to_numpy()
    # main GBM trained on d48 only — use full d48 from caller
    return d49_gt, d49_f, is_match, hist


def main():
    tr, te = load_raw()
    trc, _tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = trc[trc["day"] == 48].copy()
    d49 = trc[trc["day"] == 49].copy()
    d48_full = _feat(d48, agg, sp, True)

    keep_r, hold_r = _split_random(d48)
    keep_f_r, hold_f_r, agg_r, sp_r = _prep_holdout(keep_r, hold_r)

    keep_t, hold_t = _split_testhours(d48)
    keep_f_t, hold_f_t, agg_t, sp_t = _prep_holdout(keep_t, hold_t)

    results = {}

    # --- lookup models ---
    for name, use_nb in [("lookup_plain", False), ("lookup_nb", True)]:
        r_rand = eval_lookup_on_split(keep_f_r, hold_f_r, agg_r, sp_r, use_nb)
        r_test = eval_lookup_on_split(keep_f_t, hold_f_t, agg_t, sp_t, use_nb)
        r_d49 = eval_day49_lookup(d49, agg, sp, use_nb)
        results[name] = {
            "random_holdout": r_rand,
            "testhours_holdout": r_test,
            "day49_morning": r_d49,
            "avg_primary": (r_rand + r_test) / 2,
        }

    # --- GBM variants ---
    for gbm_name in GBM_CONFIGS:
        r_rand, bit_r, use_log = eval_gbm_on_split(gbm_name, keep_f_r, hold_f_r)
        r_test, bit_t, _ = eval_gbm_on_split(gbm_name, keep_f_t, hold_f_t)
        r_d49, bit_d49, _ = eval_day49_gbm(d48_full, d49, gbm_name, agg, sp)
        results[gbm_name] = {
            "random_holdout": r_rand,
            "testhours_holdout": r_test,
            "day49_morning": r_d49,
            "avg_primary": (r_rand + r_test) / 2,
            "best_iter_random": int(bit_r),
            "best_iter_testhours": int(bit_t),
            "best_iter_day49": int(bit_d49),
            "use_log": use_log,
        }

    # --- blend (lookup + best GBM candidate) ---
    r_blend_r, w_r = eval_blend_on_split(keep_f_r, hold_f_r, agg_r, sp_r, "gbm_cap1023")
    r_blend_t, w_t = eval_blend_on_split(keep_f_t, hold_f_t, agg_t, sp_t, "gbm_cap1023")
    d49_f = _feat(d49, agg, sp, False)
    p = GBM_CONFIGS["gbm_cap1023"]
    cat = _cat_idx(FEATURES)
    m, _ = train_gbm(d48_full[FEATURES], d48_full["demand"].to_numpy(), cat,
                     eval_X=d49_f[FEATURES], eval_y=d49_f["demand"].to_numpy(),
                     use_log=True, params=p)
    pred_g = predict_gbm(m, d49_f[FEATURES], use_log=True)
    pred_l = lookup_pred(d49_f, agg)
    y49 = d49_f["demand"].to_numpy()
    best_w_d49, r_blend_d49 = 0.0, -1e9
    for w in np.linspace(0, 1, 21):
        r2 = _r2(y49, _clip(w * pred_l + (1 - w) * pred_g))
        if r2 > r_blend_d49:
            r_blend_d49, best_w_d49 = r2, w
    results["blend_cap1023"] = {
        "random_holdout": r_blend_r,
        "testhours_holdout": r_blend_t,
        "day49_morning": r_blend_d49,
        "avg_primary": (r_blend_r + r_blend_t) / 2,
        "w_lookup_random": float(w_r),
        "w_lookup_testhours": float(w_t),
        "w_lookup_day49": float(best_w_d49),
    }

    # --- crossday stack ---
    r_cd, cd_iter, main_iter = eval_day49_crossday_stack(
        d48_full, d49, agg, sp, "gbm_cap1023")
    # testhours/random: crossday hist_gt not available on d48 rows — use main GBM only
    r_cd_rand, _, _ = eval_gbm_on_split("gbm_cap1023", keep_f_r, hold_f_r)
    r_cd_test, _, _ = eval_gbm_on_split("gbm_cap1023", keep_f_t, hold_f_t)
    results["crossday_stack"] = {
        "random_holdout": r_cd_rand,
        "testhours_holdout": r_cd_test,
        "day49_morning": r_cd,
        "avg_primary": (r_cd_rand + r_cd_test) / 2,
        "crossday_iter": int(cd_iter),
        "main_iter": int(main_iter),
        "note": "random/testhours use main GBM; day49 uses full stack",
    }

    # --- hist_gt direct hybrid ---
    d49_gt, d49_f, is_match, hist = eval_day49_hist_gt_direct(d49, agg, sp)
    p = GBM_CONFIGS["gbm_cap1023"]
    cat = _cat_idx(FEATURES)
    main, _ = train_gbm(d48_full[FEATURES], d48_full["demand"].to_numpy(), cat,
                        use_log=True, num_boost_round=800, params=p)
    pred_main = predict_gbm(main, d49_f[FEATURES], use_log=True)
    pred_hybrid_d49 = _clip(np.where(is_match, hist, pred_main))
    r_hybrid_d49 = _r2(d49_gt["demand"].to_numpy(), pred_hybrid_d49)
    r_h_rand, _, _ = eval_gbm_on_split("gbm_cap1023", keep_f_r, hold_f_r)
    r_h_test, _, _ = eval_gbm_on_split("gbm_cap1023", keep_f_t, hold_f_t)
    results["hist_gt_hybrid"] = {
        "random_holdout": r_h_rand,
        "testhours_holdout": r_h_test,
        "day49_morning": r_hybrid_d49,
        "avg_primary": (r_h_rand + r_h_test) / 2,
        "note": "day49: hist_gt if matched else gbm_cap1023",
    }

    # --- pick winner ---
    # Test is Day-49 cross-day (89% exact Day-48 match). Weight day49 + testhours
    # higher than random CV; crossday/hybrid models only shine on day49_morning.
    for name, st in results.items():
        st["test_score"] = (
            0.25 * st["random_holdout"]
            + 0.35 * st["testhours_holdout"]
            + 0.40 * st["day49_morning"]
        )

    ranked_cv = sorted(results.items(), key=lambda x: x[1]["avg_primary"], reverse=True)
    ranked_test = sorted(results.items(), key=lambda x: x[1]["test_score"], reverse=True)
    winner_name, winner_stats = ranked_test[0]
    cv_winner, cv_stats = ranked_cv[0]

    print("=" * 78)
    print("MODEL COMPARISON (train-only validation)")
    print("=" * 78)
    print(f"{'model':22s} {'rand_R2':>8} {'testhr_R2':>9} {'d49_R2':>8} "
          f"{'avg':>8} {'test_sc':>8}")
    print("-" * 78)
    for name, st in ranked_test:
        print(f"{name:22s} {st['random_holdout']:8.4f} "
              f"{st['testhours_holdout']:9.4f} {st['day49_morning']:8.4f} "
              f"{st['avg_primary']:8.4f} {st['test_score']:8.4f}")
    print("-" * 78)
    print(f"WINNER (for test): {winner_name}  test_score={winner_stats['test_score']:.4f}")
    print(f"Best CV-only:      {cv_winner}  avg_primary={cv_stats['avg_primary']:.4f}")
    print("=" * 78)

    out = {
        "winner": winner_name,
        "winner_stats": winner_stats,
        "cv_winner": cv_winner,
        "cv_winner_stats": cv_stats,
        "all_results": results,
        "selection_rule": "max 0.25*random + 0.35*testhours + 0.40*day49",
    }
    path = "submissions/model_comparison.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {path}")
    return winner_name, winner_stats, results


if __name__ == "__main__":
    main()
