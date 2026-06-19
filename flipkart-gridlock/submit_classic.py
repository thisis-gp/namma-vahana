"""Submit predictions from classic ML tournament winner (no lookup)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.pipeline import load_raw, prepare
from src.model import train_gbm, predict_gbm, PARAMS
from src.classic_features import prepare_full_train_test, to_design_matrix

REPORT = Path("submissions/classic_ml_report.json")
MODEL = "lgbm_classic"
OUT = "submissions/sub_classic.csv"


def _build_model(name: str, report: dict):
    meta = {}
    for r in report.get("results", []):
        if r["bracket"] == "TESTHOURS":
            meta = r.get("model_meta", {}).get(name, {})
            break

    if name == "ridge":
        alpha = meta.get("alpha", 100.0)
        return Pipeline([("sc", StandardScaler()), ("m", Ridge(alpha=alpha))]), {}
    if name == "elasticnet":
        return Pipeline([
            ("sc", StandardScaler()),
            ("m", ElasticNet(
                alpha=meta.get("m__alpha", 0.01),
                l1_ratio=meta.get("m__l1_ratio", 0.5),
                max_iter=5000, random_state=0,
            )),
        ]), {}
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=300, max_depth=14, min_samples_leaf=15,
            max_features="sqrt", random_state=0, n_jobs=-1,
        ), {}
    if name == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=400, max_depth=16, min_samples_leaf=10,
            max_features="sqrt", random_state=0, n_jobs=-1,
        ), {}
    if name == "hist_gbm":
        return HistGradientBoostingRegressor(
            max_depth=10, learning_rate=0.05, max_iter=400,
            min_samples_leaf=20, l2_regularization=1.0, random_state=0,
        ), {}
    if name == "lgbm_classic":
        return "lgbm", {"best_iteration": meta.get("best_iteration", 245)}
    raise ValueError(f"unknown model {name!r}")


def _predict(model_name, report, Xtr, ytr, Xte):
    model, extra = _build_model(model_name, report)
    if model == "lgbm":
        bit = extra["best_iteration"]
        booster, _ = train_gbm(Xtr, ytr, cat_idx=[], use_log=True,
                               num_boost_round=bit, params=PARAMS)
        return predict_gbm(booster, Xte, use_log=True)
    model.fit(Xtr, ytr)
    return np.clip(model.predict(Xte), 0.0, 1.0)


def _write(path, tec, pred):
    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": pred})
    assert out.shape == (41778, 2)
    assert np.isfinite(out["demand"]).all()
    assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all()
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    out.to_csv(path, index=False)
    print(f"wrote {path}  mean={pred.mean():.4f} min={pred.min():.4f} max={pred.max():.4f}")


def main():
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    winner = report.get("winner", MODEL)
    tr, te = load_raw()
    trc, tec, _, _ = prepare(tr, te)
    tr_df, te_df = prepare_full_train_test(trc, tec)

    Xtr, _cols, rt_cats = to_design_matrix(tr_df)
    Xte, _, _ = to_design_matrix(te_df, rt_cats)
    ytr = tr_df["demand"].to_numpy()

    # Winner + top testhours models for LB A/B
    th_scores = report.get("results", [{}])[0].get("scores", {})
    top_th = sorted(
        ((k, v) for k, v in th_scores.items() if k != "gbm_raw_features"),
        key=lambda t: -t[1],
    )[:3]
    to_submit = []
    seen = set()
    for name, _ in [("winner", 0)] + top_th:
        m = winner if name == "winner" else name
        if m in seen:
            continue
        seen.add(m)
        to_submit.append(m)

    for model_name in to_submit:
        pred = _predict(model_name, report, Xtr, ytr, Xte)
        fname = OUT if model_name == winner else f"submissions/sub_classic_{model_name}.csv"
        _write(fname, tec, pred)
        print(f"  model={model_name}")


if __name__ == "__main__":
    main()
