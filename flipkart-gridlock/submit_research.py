"""Submit research tournament winner + anchor variants for LB A/B."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor

from src.pipeline import FEATURES, load_raw, prepare
from src.model import train_gbm, predict_gbm, PARAMS
from src.research_features import (
    FEATURES_IX, FEATURES_IX_RATIO, build_ratio_g_table,
    prepare_full_d48_test, cat_idx,
)
from src.classic_features import prepare_full_train_test, to_design_matrix

REPORT = Path("submissions/research_report.json")
OUT = "submissions/sub_research.csv"


def main():
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    winner = report.get("winner", "gbm_ix_ratio")
    meta_th = {}
    for r in report.get("results", []):
        if r["bracket"] == "TESTHOURS":
            meta_th = r.get("meta", {})
            break

    tr, te = load_raw()
    trc, tec, _, _ = prepare(tr, te)
    ratio = build_ratio_g_table(trc)

    tr_ix, te_ix = prepare_full_d48_test(trc, tec, ratio, with_ratio=True)
    tr_cl, te_cl = prepare_full_train_test(trc, tec)
    ytr = tr_ix["demand"].to_numpy()

    variants = {}

    # baseline anchor
    bit = meta_th.get("baseline_gbm", {}).get("best_iteration", 245)
    m0, _ = train_gbm(tr_ix[FEATURES], ytr, cat_idx(FEATURES),
                       use_log=True, num_boost_round=bit, params=PARAMS)
    variants["baseline_gbm"] = predict_gbm(m0, te_ix[FEATURES])

    bit_ix = meta_th.get("gbm_interactions", {}).get("best_iteration", 245)
    m1, _ = train_gbm(tr_ix[FEATURES_IX], ytr, cat_idx(FEATURES_IX),
                      use_log=True, num_boost_round=bit_ix, params=PARAMS)
    variants["gbm_interactions"] = predict_gbm(m1, te_ix[FEATURES_IX])

    bit_r = meta_th.get("gbm_ix_ratio", {}).get("best_iteration", 245)
    m2, _ = train_gbm(tr_ix[FEATURES_IX_RATIO], ytr, cat_idx(FEATURES_IX_RATIO),
                      use_log=True, num_boost_round=bit_r, params=PARAMS)
    pred_gbm = predict_gbm(m2, te_ix[FEATURES_IX_RATIO])
    variants["gbm_ix_ratio"] = pred_gbm

    Xtr, _, rt = to_design_matrix(tr_cl)
    Xte, _, _ = to_design_matrix(te_cl, rt)
    et = ExtraTreesRegressor(
        n_estimators=400, max_depth=16, min_samples_leaf=10,
        max_features="sqrt", random_state=0, n_jobs=-1,
    )
    et.fit(Xtr, tr_cl["demand"].to_numpy())
    pred_et = np.clip(et.predict(Xte), 0.0, 1.0)

    w = meta_th.get("blend_ix_ratio_et", {}).get("w_gbm", 0.7)
    variants["blend_ix_ratio_et"] = np.clip(w * pred_gbm + (1 - w) * pred_et, 0.0, 1.0)

    def write(path, pred, name):
        out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": pred})
        assert out.shape == (41778, 2)
        assert np.isfinite(out["demand"]).all()
        assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all()
        out.to_csv(path, index=False)
        print(f"wrote {path}  model={name}  mean={pred.mean():.4f}")

    write(OUT, variants[winner], winner)
    for name, pred in variants.items():
        if name != winner:
            write(f"submissions/sub_research_{name}.csv", pred, name)


if __name__ == "__main__":
    main()
