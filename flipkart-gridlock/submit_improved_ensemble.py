"""Improve the user's XGBoost notebook with seed/bagging ensembles.

Keeps the same core feature engineering as improved_notebook.ipynb, then writes
several controlled ensemble candidates.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from submit_improved_style import (
    DATA_DIR,
    SUB_DIR,
    make_matrix_notebook_exact,
    write,
)

SEEDS = [11, 23, 37, 42, 57, 71, 89]


def make_model(seed: int, n_estimators: int = 2000, early_stopping_rounds: int | None = 50):
    kwargs = dict(
        n_estimators=n_estimators,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        tree_method="hist",
        random_state=seed,
        objective="reg:squarederror",
        n_jobs=-1,
    )
    if early_stopping_rounds is not None:
        kwargs["early_stopping_rounds"] = early_stopping_rounds
    return XGBRegressor(**kwargs)


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    X, y, Xtest, test_index = make_matrix_notebook_exact(train, test)

    preds_es = []
    preds_all = []
    iters = []

    for seed in SEEDS:
        X_train, X_valid, y_train, y_valid = train_test_split(
            X, y, test_size=0.2, random_state=seed
        )
        model = make_model(seed)
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
        bit = int(getattr(model, "best_iteration", model.n_estimators - 1)) + 1
        iters.append(bit)
        pred_es = np.clip(model.predict(Xtest), 0.0, 1.0)
        preds_es.append(pred_es)
        write(test_index, pred_es, SUB_DIR / f"sub_improved_seed{seed}_es.csv")

        refit = make_model(seed, n_estimators=bit, early_stopping_rounds=None)
        refit.fit(X, y, verbose=False)
        pred_all = np.clip(refit.predict(Xtest), 0.0, 1.0)
        preds_all.append(pred_all)
        write(test_index, pred_all, SUB_DIR / f"sub_improved_seed{seed}_all.csv")
        print(f"seed={seed} best_iter={bit}")

    print("best_iters:", iters)
    print("iter median:", int(np.median(iters)), "mean:", float(np.mean(iters)))

    pred_es_mean = np.mean(preds_es, axis=0)
    pred_all_mean = np.mean(preds_all, axis=0)
    write(test_index, pred_es_mean, SUB_DIR / "sub_improved_ens_es_mean.csv")
    write(test_index, pred_all_mean, SUB_DIR / "sub_improved_ens_all_mean.csv")

    # Weighted blend: keep some validation-split regularization while using all-label refits.
    for w_all in [0.25, 0.5, 0.75]:
        pred = w_all * pred_all_mean + (1.0 - w_all) * pred_es_mean
        write(test_index, pred, SUB_DIR / f"sub_improved_ens_mix_all{int(w_all * 100):02d}.csv")


if __name__ == "__main__":
    main()
