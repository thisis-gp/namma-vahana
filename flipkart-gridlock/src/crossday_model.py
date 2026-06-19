"""Cross-day stack: hist_gt LightGBM on matched rows, reg_A3 GBM on the rest.

Validated on Day-49 morning holdout (the metric that tracks the leaderboard).
"""
from __future__ import annotations

import numpy as np

from src.pipeline import (
    add_hist_features, add_hist_gt, FEATURES, CAT_COLS,
)
from src.spatial import add_neighbor_feature
from src.model import train_gbm, predict_gbm, PARAMS

FGT = FEATURES + ["hist_gt"]
MAIN_BEST_ITER = 223  # reg_A3 early-stop on Day-49 morning (LB ~88.95)


def build_features(df, agg, sp, is_day48_train: bool):
    df = add_neighbor_feature(add_hist_features(df, agg, is_day48_train), sp, agg)
    return add_hist_gt(df, agg)


def match_mask(df, agg) -> np.ndarray:
    gt_keys = set(agg["gt"].index)
    return np.array([(g, t) in gt_keys for g, t in zip(df["geohash"], df["timestamp"])])


def _cat_idx(cols):
    return [cols.index(c) for c in CAT_COLS]


def train_main_gbm(d48, d49_eval=None, use_log=True, num_boost_round=None):
    """Day-48 structure model. Early-stops on Day-49 morning when eval is given."""
    cat = _cat_idx(FEATURES)
    X = d48[FEATURES]
    y = d48["demand"].to_numpy()
    kwargs = dict(use_log=use_log, params=PARAMS)
    if d49_eval is not None:
        m, bit = train_gbm(X, y, cat,
                           eval_X=d49_eval[FEATURES], eval_y=d49_eval["demand"].to_numpy(),
                           **kwargs)
        return m, bit
    rounds = num_boost_round if num_boost_round is not None else MAIN_BEST_ITER
    m, bit = train_gbm(X, y, cat, num_boost_round=rounds, **kwargs)
    return m, bit


def train_crossday_gbm(d49_gt, train_mask=None, eval_mask=None, use_log=True,
                       num_boost_round=None):
    """Day-49 cross-day model with hist_gt. Uses reg_A3 params."""
    cat = _cat_idx(FGT)
    if train_mask is None:
        X = d49_gt[FGT]
        y = d49_gt["demand"].to_numpy()
        if eval_mask is not None:
            m, bit = train_gbm(X[~eval_mask], y[~eval_mask], cat,
                               eval_X=X[eval_mask], eval_y=y[eval_mask],
                               use_log=use_log, params=PARAMS)
            return m, bit
        rounds = num_boost_round if num_boost_round is not None else 500
        m, bit = train_gbm(X, y, cat, num_boost_round=rounds,
                           use_log=use_log, params=PARAMS)
        return m, bit
    m, bit = train_gbm(d49_gt[FGT][train_mask], d49_gt["demand"].to_numpy()[train_mask],
                       cat, eval_X=d49_gt[FGT][~train_mask],
                       eval_y=d49_gt["demand"].to_numpy()[~train_mask],
                       use_log=use_log, params=PARAMS)
    return m, bit


def predict_stack(df_gt, df_plain, cd_model, main_model, is_match,
                  cd_use_log=True, main_use_log=True) -> np.ndarray:
    pred_cd = predict_gbm(cd_model, df_gt[FGT], use_log=cd_use_log)
    pred_main = predict_gbm(main_model, df_plain[FEATURES], use_log=main_use_log)
    return np.clip(np.where(is_match, pred_cd, pred_main), 0.0, 1.0)
