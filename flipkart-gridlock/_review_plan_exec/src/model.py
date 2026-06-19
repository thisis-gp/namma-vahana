"""LightGBM training + prediction with optional log1p target transform."""
from __future__ import annotations
import numpy as np
import lightgbm as lgb

PARAMS = dict(
    objective="regression",
    metric="rmse",
    learning_rate=0.03,
    num_leaves=63,
    min_child_samples=40,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    lambda_l2=1.0,
    verbose=-1,
)


def train_gbm(X, y, cat_idx, eval_X=None, eval_y=None,
              use_log=True, num_boost_round=3000):
    """Train LightGBM. With an eval set: early-stop and return best_iteration;
    else train full num_boost_round. Returns (booster, best_iteration)."""
    yt = np.log1p(y) if use_log else y
    dtrain = lgb.Dataset(X, label=yt, categorical_feature=cat_idx)
    callbacks = [lgb.log_evaluation(period=0)]
    valid_sets = None
    if eval_X is not None:
        eyt = np.log1p(eval_y) if use_log else eval_y
        dvalid = lgb.Dataset(eval_X, label=eyt, categorical_feature=cat_idx,
                             reference=dtrain)
        valid_sets = [dvalid]
        callbacks.append(lgb.early_stopping(stopping_rounds=100, verbose=False))
    booster = lgb.train(PARAMS, dtrain, num_boost_round=num_boost_round,
                        valid_sets=valid_sets, callbacks=callbacks)
    best_iter = booster.best_iteration or num_boost_round
    return booster, best_iter


def predict_gbm(booster, X, use_log=True):
    raw = booster.predict(X, num_iteration=booster.best_iteration or None)
    pred = np.expm1(raw) if use_log else raw
    return np.clip(pred, 0.0, 1.0)