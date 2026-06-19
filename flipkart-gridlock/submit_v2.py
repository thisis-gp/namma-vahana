"""Train crossday_v2 winner + baseline; write test submission CSVs."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.pipeline import load_raw, prepare, FEATURES, CAT_COLS
from src.spatial import build_spatial_index
from src.crossday_model import (
    build_features, match_mask, train_main_gbm, train_crossday_gbm,
    predict_stack,
)
from src.model import train_gbm, predict_gbm, PARAMS


def _write(tec, preds, path):
    preds = np.clip(np.asarray(preds, dtype=float), 0.0, 1.0)
    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": preds})
    assert out.shape == (41778, 2)
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    out.to_csv(path, index=False)
    print(f"wrote {path}  mean={preds.mean():.4f} min={preds.min():.4f} max={preds.max():.4f}")


def main():
    with open("submissions/crossday_v2_comparison.json") as f:
        comp = json.load(f)
    winner = comp["winner"]
    wst = comp["winner_stats"]
    print(f"Winner: {winner}  (holdout R2={wst['holdout_r2']:.4f})")

    tr, te = load_raw()
    trc, tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)

    d48 = build_features(trc[trc["day"] == 48].copy(), agg, sp, True)
    d49_gt = build_features(trc[trc["day"] == 49].copy(), agg, sp, False)
    test_gt = build_features(tec.copy(), agg, sp, False)
    test_plain = test_gt
    is_match = match_mask(test_gt, agg)

    if winner == "gbm_baseline":
        cat = [FEATURES.index(c) for c in CAT_COLS]
        m, _ = train_gbm(d48[FEATURES], d48["demand"].to_numpy(), cat,
                         use_log=True, num_boost_round=int(wst["main_iter"]),
                         params=PARAMS)
        preds = predict_gbm(m, test_plain[FEATURES], use_log=True)
    else:
        cd_log = wst["cd_use_log"]
        main_log = wst["main_use_log"]
        cd, _ = train_crossday_gbm(d49_gt, use_log=cd_log,
                                   num_boost_round=int(wst["crossday_iter"]))
        main, _ = train_main_gbm(d48, d49_eval=d49_gt, use_log=main_log)
        preds = predict_stack(test_gt, test_plain, cd, main, is_match,
                              cd_use_log=cd_log, main_use_log=main_log)

    _write(tec, preds, "submissions/sub_best.csv")
    _write(tec, preds, "submissions/sub_crossday_v2.csv")

    # also refresh LB-best baseline for A/B
    cat = [FEATURES.index(c) for c in CAT_COLS]
    base, _ = train_gbm(d48[FEATURES], d48["demand"].to_numpy(), cat,
                        eval_X=d49_gt[FEATURES], eval_y=d49_gt["demand"].to_numpy(),
                        use_log=True, params=PARAMS)
    base_preds = predict_gbm(base, test_plain[FEATURES], use_log=True)
    _write(tec, base_preds, "submissions/sub_gbm.csv")


if __name__ == "__main__":
    main()
