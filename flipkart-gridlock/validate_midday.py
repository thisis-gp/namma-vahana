"""Honesty-check: is the model as good on the real TEST hours (2:15-13:45) as
on the morning hours validate.py scores on (0:00-2:00)?

Within Day 48: hold out a band of hours, REBUILD all aggregates from the kept
rows only (no leak), train on the rest, predict the band. Compare the two bands'
R2. A big gap means validate.py (morning-only) is optimistic vs the leaderboard.
"""
import numpy as np
from sklearn.metrics import r2_score
from src.pipeline import (load_raw, prepare, add_hist_features,
                          build_day48_aggregates, FEATURES, CAT_COLS)
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm

# Day-49 TRAIN labels are 0:00-2:00; the real TEST is the contiguous band
# 2:15-13:45 (47 slots) -- NOT just midday. Hold out the true test hours.
MORNING   = set(range(0, 2 * 60 + 1))               # 0:00-2:00  (matches Day-49 TRAIN)
TESTHOURS = set(range(2 * 60 + 15, 13 * 60 + 46))   # 2:15-13:45 (matches real TEST)


def run_band(d48, band, label):
    """Hold out `band` from Day 48; rebuild aggregates + spatial index from the
    KEPT rows ONLY, so held-out targets never leak through hist_* or neighbors
    (BLOCKER fix). Then predict the band as pure inference. This is a conservative
    lower bound on skill -- in reality Day-48 features for those hours DO exist."""
    hold = d48[d48["minutes"].isin(band)].copy()
    keep = d48[~d48["minutes"].isin(band)].copy()
    agg_k = build_day48_aggregates(keep)
    sp_k = build_spatial_index(keep, k=12)
    keep = add_neighbor_feature(add_hist_features(keep, agg_k, True), sp_k, agg_k)
    hold = add_neighbor_feature(add_hist_features(hold, agg_k, False), sp_k, agg_k)
    cat_idx = [FEATURES.index(c) for c in CAT_COLS]
    m, _ = train_gbm(keep[FEATURES], keep["demand"].to_numpy(), cat_idx,
                     use_log=True, num_boost_round=800)
    p = predict_gbm(m, hold[FEATURES], use_log=True)
    r2 = r2_score(hold["demand"].to_numpy(), p)
    print(f"{label:9s}: model R2 = {r2:.4f}  (n={len(hold)}, mean demand={hold['demand'].mean():.3f})")
    return r2


def main():
    tr, te = load_raw()
    trc, _tec, _agg, _tm = prepare(tr, te)
    d48 = trc[trc["day"] == 48].copy()
    r2_morn = run_band(d48, MORNING, "MORNING")
    r2_test = run_band(d48, TESTHOURS, "TESTHOURS")
    gap = r2_morn - r2_test
    print(f"\nGap (morning - testhours) = {gap:+.4f}")
    if gap > 0.05:
        print("WARNING: weaker on test-like hours -> trust validate.py (morning) LESS;"
              " expect leaderboard below the Day-49 number.")
    else:
        print("OK: test-hours skill ~ morning skill -> validate.py is a fair proxy.")


if __name__ == "__main__":
    main()
