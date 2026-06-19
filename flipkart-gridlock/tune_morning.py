"""Morning-validated LightGBM tuning. Objective = day48->day49 morning R2.
Keep ONLY if it beats reg_A3 (0.7710) by >= +0.005, else keep reg_A3."""
import numpy as np, optuna
from sklearn.metrics import r2_score
from src.pipeline import load_raw, prepare, add_hist_features, FEATURES, CAT_COLS
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm

BASELINE = 0.7710  # reg_A3 morning holdout
MARGIN = 0.005


def main():
    tr, te = load_raw()
    trc, _te, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = add_neighbor_feature(add_hist_features(trc[trc.day == 48].copy(), agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(trc[trc.day == 49].copy(), agg, False), sp, agg)
    cat = [FEATURES.index(c) for c in CAT_COLS]
    X, y = d48[FEATURES], d48["demand"].to_numpy()
    Xv, yv = d49[FEATURES], d49["demand"].to_numpy()

    def objective(trial):
        p = dict(
            objective="regression", metric="rmse", verbose=-1, bagging_freq=1,
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            num_leaves=trial.suggest_int("num_leaves", 8, 128),
            min_child_samples=trial.suggest_int("min_child_samples", 20, 400),
            feature_fraction=trial.suggest_float("feature_fraction", 0.5, 1.0),
            bagging_fraction=trial.suggest_float("bagging_fraction", 0.5, 1.0),
            lambda_l1=trial.suggest_float("lambda_l1", 0.0, 10.0),
            lambda_l2=trial.suggest_float("lambda_l2", 0.0, 10.0),
        )
        m, _ = train_gbm(X, y, cat, eval_X=Xv, eval_y=yv, use_log=True, params=p)
        return r2_score(yv, predict_gbm(m, Xv))

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=0))
    study.optimize(objective, n_trials=60, show_progress_bar=False)

    print(f"\nbaseline reg_A3 morning R2 : {BASELINE:.4f}")
    print(f"best tuned morning R2      : {study.best_value:.4f}")
    print(f"best params                : {study.best_params}")
    # refit best to get best_iteration for submit.py
    bp = dict(objective="regression", metric="rmse", verbose=-1, bagging_freq=1,
              **study.best_params)
    _, bit = train_gbm(X, y, cat, eval_X=Xv, eval_y=yv, use_log=True, params=bp)
    print(f"best_iteration             : {bit}")
    if study.best_value >= BASELINE + MARGIN:
        print(f"\nDECISION: KEEP. Paste best params into model.py PARAMS (add the")
        print(f"  objective/metric/verbose/bagging_freq lines) and set submit.py BEST_ITER={bit}.")
    else:
        print(f"\nDECISION: DISCARD. Gain < +{MARGIN} over reg_A3 -> likely holdout noise; keep reg_A3.")


if __name__ == "__main__":
    main()
