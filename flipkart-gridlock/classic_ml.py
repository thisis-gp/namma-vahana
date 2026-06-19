"""Classic ML tournament: same engineered features, multiple learners.

Models: Ridge, ElasticNet, RandomForest, ExtraTrees, HistGBM, LightGBM-classic.
Reports R² on testhours / random / morning. No lookup.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.pipeline import load_raw, prepare, FEATURES, CAT_COLS
from src.model import train_gbm, predict_gbm, PARAMS
from src.classic_features import (
    FEATURE_GROUPS, prepare_fold, prepare_full_day48_day49, to_design_matrix,
)

TESTBAND = set(range(2 * 60 + 15, 13 * 60 + 46))
OUT = Path("submissions/classic_ml_report.json")

MODEL_NAMES = [
    "ridge", "elasticnet", "random_forest", "extra_trees",
    "hist_gbm", "lgbm_classic",
]


def _fit_ridge(Xtr, ytr, Xva=None, yva=None):
    pipe = Pipeline([("sc", StandardScaler()), ("m", Ridge())])
    gs = GridSearchCV(pipe, {"m__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
                      cv=3, scoring="r2", n_jobs=-1)
    gs.fit(Xtr, ytr)
    return gs.best_estimator_, {"alpha": gs.best_params_["m__alpha"]}


def _fit_elastic(Xtr, ytr, Xva=None, yva=None):
    pipe = Pipeline([
        ("sc", StandardScaler()),
        ("m", ElasticNet(max_iter=5000, random_state=0)),
    ])
    gs = GridSearchCV(
        pipe,
        {"m__alpha": [0.001, 0.01, 0.1, 1.0], "m__l1_ratio": [0.1, 0.5, 0.9]},
        cv=3, scoring="r2", n_jobs=-1,
    )
    gs.fit(Xtr, ytr)
    return gs.best_estimator_, gs.best_params_


def _fit_rf(Xtr, ytr, Xva=None, yva=None):
    m = RandomForestRegressor(
        n_estimators=300, max_depth=14, min_samples_leaf=15,
        max_features="sqrt", random_state=0, n_jobs=-1,
    )
    m.fit(Xtr, ytr)
    return m, {}


def _fit_extratrees(Xtr, ytr, Xva=None, yva=None):
    m = ExtraTreesRegressor(
        n_estimators=400, max_depth=16, min_samples_leaf=10,
        max_features="sqrt", random_state=0, n_jobs=-1,
    )
    m.fit(Xtr, ytr)
    return m, {}


def _fit_hist_gbm(Xtr, ytr, Xva=None, yva=None):
    m = HistGradientBoostingRegressor(
        max_depth=10, learning_rate=0.05, max_iter=400,
        min_samples_leaf=20, l2_regularization=1.0, random_state=0,
    )
    m.fit(Xtr, ytr)
    return m, {}


def _fit_lgbm_classic(Xtr, ytr, Xva=None, yva=None):
    """LightGBM on the 35-feature classic matrix (notebook params)."""
    booster, bit = train_gbm(
        Xtr, ytr, cat_idx=[],
        eval_X=Xva, eval_y=yva,
        use_log=True, params=PARAMS, num_boost_round=3000,
    )
    return booster, {"best_iteration": bit}


def _predict(name: str, model, X):
    if name == "lgbm_classic":
        return predict_gbm(model, X, use_log=True)
    return model.predict(X)


FITTERS: dict[str, Callable] = {
    "ridge": _fit_ridge,
    "elasticnet": _fit_elastic,
    "random_forest": _fit_rf,
    "extra_trees": _fit_extratrees,
    "hist_gbm": _fit_hist_gbm,
    "lgbm_classic": _fit_lgbm_classic,
}


def _score(name, model, Xte, yte):
    return float(r2_score(yte, np.clip(_predict(name, model, Xte), 0.0, 1.0)))


def _top_coefs(model, colnames, n=8):
    if not hasattr(model, "named_steps"):
        return []
    coef = model.named_steps["m"].coef_
    imp = sorted(zip(colnames, np.abs(coef)), key=lambda t: -t[1])[:n]
    return [{"feature": f, "abs_coef": round(v, 5)} for f, v in imp]


def _top_tree_importance(model, colnames, n=8):
    if not hasattr(model, "feature_importances_"):
        return []
    imp = sorted(zip(colnames, model.feature_importances_), key=lambda t: -t[1])[:n]
    return [{"feature": f, "importance": round(v, 5)} for f, v in imp]


def incremental_r2(tr: pd.DataFrame, te: pd.DataFrame):
    ytr, yte = tr["demand"].to_numpy(), te["demand"].to_numpy()
    rt_cats = sorted(tr["RoadType"].astype(int).unique().tolist())
    order = ["location", "time", "road", "weather", "interactions"]
    cols_so_far: list[str] = []
    roadtype_on = False
    rows = []
    for g in order:
        cols_so_far.extend(FEATURE_GROUPS[g])
        if g == "road":
            roadtype_on = True
        inc_rt = roadtype_on
        sub_tr = tr[cols_so_far + (["RoadType"] if inc_rt else [])]
        sub_te = te[cols_so_far + (["RoadType"] if inc_rt else [])]
        Xtr, names, _ = to_design_matrix(
            sub_tr, rt_cats, numeric_cols=cols_so_far, include_roadtype=inc_rt,
        )
        Xte, _, _ = to_design_matrix(
            sub_te, rt_cats, numeric_cols=cols_so_far, include_roadtype=inc_rt,
        )
        m, meta = _fit_ridge(Xtr, ytr)
        rows.append({
            "group_added": g, "n_features": len(names),
            "R2": round(_score("ridge", m, Xte, yte), 4),
            "ridge_alpha": meta["alpha"],
        })
    return rows


def evaluate_bracket(tr, te, label):
    ytr, yte = tr["demand"].to_numpy(), te["demand"].to_numpy()
    Xtr, cols, rt_cats = to_design_matrix(tr)
    Xte, _, _ = to_design_matrix(te, rt_cats)

    scores = {}
    meta = {}
    for name in MODEL_NAMES:
        m, mmeta = FITTERS[name](Xtr, ytr, Xva=Xte, yva=yte)
        scores[name] = round(_score(name, m, Xte, yte), 4)
        meta[name] = mmeta

    cat = [FEATURES.index(c) for c in CAT_COLS]
    gbm_raw, gbm_bit = train_gbm(
        tr[FEATURES], ytr, cat, eval_X=te[FEATURES], eval_y=yte,
        use_log=True, params=PARAMS, num_boost_round=3000,
    )
    scores["gbm_raw_features"] = round(
        r2_score(yte, predict_gbm(gbm_raw, te[FEATURES])), 4,
    )
    meta["gbm_raw_features"] = {"best_iteration": gbm_bit}

    res = {
        "bracket": label,
        "n_train": len(tr),
        "n_hold": len(te),
        "total_var": float(np.var(yte)),
        "scores": scores,
        "model_meta": meta,
        "incremental_R2": incremental_r2(tr, te) if label == "TESTHOURS" else [],
        "ridge_top_coefs": [],
    }

    ridge_m, _ = FITTERS["ridge"](Xtr, ytr)
    res["ridge_top_coefs"] = _top_coefs(ridge_m, cols)

    print(f"\n--- {label} ---")
    print(f"  holdout variance : {res['total_var']:.6f}")
    for name in MODEL_NAMES + ["gbm_raw_features"]:
        extra = ""
        if name == "lgbm_classic" and "best_iteration" in meta.get(name, {}):
            extra = f"  iter={meta[name]['best_iteration']}"
        print(f"  {name:18s}: R2={scores[name]:.4f}{extra}")
    if res["incremental_R2"]:
        print("  Incremental R2 by feature group (Ridge):")
        for row in res["incremental_R2"]:
            print(f"    +{row['group_added']:12s}  R2={row['R2']:.4f}")
    return res


def pick_winner(results: list[dict]) -> tuple[str, float, float]:
    th = next(r for r in results if r["bracket"] == "TESTHOURS")
    rd = next(r for r in results if r["bracket"] == "RANDOM")
    best_name, best_combo = "", -1e9
    for name in MODEL_NAMES:
        combo = 0.6 * th["scores"][name] + 0.4 * rd["scores"][name]
        if combo > best_combo:
            best_combo = combo
            best_name = name
    return best_name, th["scores"][best_name], rd["scores"][best_name]


def main():
    tr_raw, te_raw = load_raw()
    trc, _tec, _, _ = prepare(tr_raw, te_raw)
    d48 = trc[trc["day"] == 48].copy()

    rng = np.random.RandomState(0)
    rmask = rng.rand(len(d48)) < 0.8
    tb = d48["minutes"].isin(TESTBAND).to_numpy()

    print("=== Classic ML tournament (same 35 features, no lookup) ===")

    results = []
    tr_th, te_th = prepare_fold(d48, ~tb)
    results.append(evaluate_bracket(tr_th, te_th, "TESTHOURS"))

    tr_rd, te_rd = prepare_fold(d48, rmask)
    results.append(evaluate_bracket(tr_rd, te_rd, "RANDOM"))

    tr49, te49 = prepare_full_day48_day49(trc)
    results.append(evaluate_bracket(tr49, te49, "D49_MORNING"))

    winner, th_r2, rd_r2 = pick_winner(results)
    th = results[0]["scores"]
    print(f"\nWINNER (0.6*testhours + 0.4*random): {winner}")
    print(f"  testhours R2={th_r2:.4f}  random R2={rd_r2:.4f}")
    print(f"  lgbm_classic testhours={th['lgbm_classic']:.4f}  gbm_raw={th['gbm_raw_features']:.4f}")

    report = {
        "results": results,
        "winner": winner,
        "winner_testhours_R2": th_r2,
        "winner_random_R2": rd_r2,
        "selection": "0.6 * testhours_R2 + 0.4 * random_R2",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {OUT}")
    print(f"-> python submit_classic.py  (MODEL from report)")


if __name__ == "__main__":
    main()
