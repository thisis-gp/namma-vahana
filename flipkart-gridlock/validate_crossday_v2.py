"""Select best cross-day variant using Day-49 morning holdout (LB proxy).

Compares:
  gbm_baseline       — reg_A3 Day-48 GBM only (LB reference ~88.95)
  crossday_log       — crossday use_log=True  + reg_A3 main fallback
  crossday_nolog     — crossday use_log=False + reg_A3 main fallback (log)
  crossday_nolog_all — both models identity link
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.metrics import r2_score

from src.pipeline import load_raw, prepare
from src.spatial import build_spatial_index
from src.crossday_model import (
    build_features, match_mask, train_main_gbm, train_crossday_gbm,
    predict_stack, MAIN_BEST_ITER,
)
from src.model import train_gbm, predict_gbm, PARAMS

RNG = np.random.RandomState(0)


def _r2(y, p):
    return float(r2_score(y, p))


def _eval_gbm_baseline(d48, d49):
    from src.pipeline import FEATURES, CAT_COLS
    cat = [FEATURES.index(c) for c in CAT_COLS]
    m, bit = train_gbm(d48[FEATURES], d48["demand"].to_numpy(), cat,
                       eval_X=d49[FEATURES], eval_y=d49["demand"].to_numpy(),
                       use_log=True, params=PARAMS)
    pred = predict_gbm(m, d49[FEATURES], use_log=True)
    return _r2(d49["demand"].to_numpy(), pred), int(bit)


def _eval_crossday(d48, d49_gt, d49_plain, agg, cd_log, main_log):
    m = RNG.rand(len(d49_gt)) < 0.8
    cd, cd_iter = train_crossday_gbm(d49_gt, train_mask=m, use_log=cd_log)
    main, main_iter = train_main_gbm(d48, d49_eval=d49_plain, use_log=main_log)
    is_match = match_mask(d49_gt, agg)
    pred = predict_stack(d49_gt[~m], d49_plain[~m], cd, main, is_match[~m],
                         cd_use_log=cd_log, main_use_log=main_log)
    hold_r2 = _r2(d49_gt["demand"].to_numpy()[~m], pred)

    cd_f, _ = train_crossday_gbm(d49_gt, use_log=cd_log,
                                 num_boost_round=cd.best_iteration or cd_iter)
    main_f, _ = train_main_gbm(d48, d49_eval=d49_plain, use_log=main_log)
    pred_full = predict_stack(d49_gt, d49_plain, cd_f, main_f, is_match,
                              cd_use_log=cd_log, main_use_log=main_log)
    full_r2 = _r2(d49_gt["demand"].to_numpy(), pred_full)
    return hold_r2, full_r2, int(cd.best_iteration or cd_iter), int(main_iter)


def main():
    tr, te = load_raw()
    trc, _tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)

    d48 = build_features(trc[trc["day"] == 48].copy(), agg, sp, True)
    d49_gt = build_features(trc[trc["day"] == 49].copy(), agg, sp, False)
    d49_plain = d49_gt  # same columns; plain view for main model (no hist_gt in FEATURES)

    results = {}

    r2, bit = _eval_gbm_baseline(d48, d49_plain)
    results["gbm_baseline"] = {
        "holdout_r2": r2, "full_r2": r2,
        "main_iter": bit, "crossday_iter": 0,
        "cd_use_log": None, "main_use_log": True,
    }

    variants = [
        ("crossday_log",       True,  True),
        ("crossday_nolog",     False, True),
        ("crossday_nolog_all", False, False),
    ]
    for name, cd_log, main_log in variants:
        hold, full, cd_it, main_it = _eval_crossday(
            d48, d49_gt, d49_plain, agg, cd_log, main_log)
        results[name] = {
            "holdout_r2": hold, "full_r2": full,
            "crossday_iter": cd_it, "main_iter": main_it,
            "cd_use_log": cd_log, "main_use_log": main_log,
        }

    ranked = sorted(results.items(), key=lambda x: x[1]["holdout_r2"], reverse=True)
    winner, wst = ranked[0]

    print("=" * 72)
    print("CROSSDAY V2 — Day-49 morning holdout (LB proxy)")
    print("=" * 72)
    print(f"{'model':22s} {'holdout':>9} {'full_d49':>9} {'cd_iter':>8} {'main_iter':>9}")
    print("-" * 72)
    for name, st in ranked:
        print(f"{name:22s} {st['holdout_r2']:9.4f} {st['full_r2']:9.4f} "
              f"{st['crossday_iter']:8d} {st['main_iter']:9d}")
    print("-" * 72)
    print(f"WINNER: {winner}  holdout_r2={wst['holdout_r2']:.4f}")
    print(f"  cd_use_log={wst['cd_use_log']}  main_use_log={wst['main_use_log']}")
    print("=" * 72)

    out = {"winner": winner, "winner_stats": wst, "all_results": results,
           "selection_rule": "max Day-49 morning 80/20 holdout R2"}
    path = "submissions/crossday_v2_comparison.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
