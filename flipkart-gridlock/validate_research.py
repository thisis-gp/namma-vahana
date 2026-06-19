"""Research tournament: baseline GBM vs interactions vs ratio_g vs blend."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import r2_score

from src.pipeline import FEATURES, load_raw, prepare
from src.model import train_gbm, predict_gbm, PARAMS
from src.research_features import (
    FEATURES_IX, FEATURES_IX_RATIO, build_ratio_g_table,
    prepare_d48_frame, cat_idx,
)
from src.classic_features import prepare_fold, to_design_matrix

TESTBAND = set(range(2 * 60 + 15, 13 * 60 + 46))
OUT = Path("submissions/research_report.json")
BASELINE_TH = 0.8400  # gbm raw on testhours from classic_ml report
MARGIN = 0.005


def _gbm_r2(tr, te, cols, bit=None):
    cat = cat_idx(cols)
    ytr, yte = tr["demand"].to_numpy(), te["demand"].to_numpy()
    m, best = train_gbm(
        tr[cols], ytr, cat, eval_X=te[cols], eval_y=yte,
        use_log=True, params=PARAMS, num_boost_round=3000,
    )
    use_iter = bit if bit is not None else best
    m.best_iteration = use_iter
    return float(r2_score(yte, predict_gbm(m, te[cols]))), use_iter, m


def _extratrees_r2(tr_cl, te_cl):
    Xtr, _, rt = to_design_matrix(tr_cl)
    Xte, _, _ = to_design_matrix(te_cl, rt)
    ytr, yte = tr_cl["demand"].to_numpy(), te_cl["demand"].to_numpy()
    et = ExtraTreesRegressor(
        n_estimators=400, max_depth=16, min_samples_leaf=10,
        max_features="sqrt", random_state=0, n_jobs=-1,
    )
    et.fit(Xtr, ytr)
    return float(r2_score(yte, np.clip(et.predict(Xte), 0.0, 1.0))), et


def _blend_r2(pred_a, pred_b, y, weights):
    best_r2, best_w = -1e9, 0.0
    for w in weights:
        p = np.clip(w * pred_a + (1 - w) * pred_b, 0.0, 1.0)
        r2 = float(r2_score(y, p))
        if r2 > best_r2:
            best_r2, best_w = r2, w
    return best_r2, best_w


def evaluate_bracket(d48, trc, ratio, train_mask, label):
    tr_ix, te_ix = prepare_d48_frame(d48, train_mask, ratio, with_ratio=True)
    tr_cl, te_cl = prepare_fold(d48, train_mask)
    tr, te = tr_ix, te_ix

    yte = te["demand"].to_numpy()
    scores = {}
    meta = {}

    r, bit, _ = _gbm_r2(tr, te, FEATURES)
    scores["baseline_gbm"] = r
    meta["baseline_gbm"] = {"best_iteration": bit}

    r, bit, _ = _gbm_r2(tr_ix, te_ix, FEATURES_IX)
    scores["gbm_interactions"] = r
    meta["gbm_interactions"] = {"best_iteration": bit}

    r, bit, m_ratio = _gbm_r2(tr_ix, te_ix, FEATURES_IX_RATIO)
    scores["gbm_ix_ratio"] = r
    meta["gbm_ix_ratio"] = {"best_iteration": bit}

    pred_gbm = predict_gbm(m_ratio, te_ix[FEATURES_IX_RATIO])
    r_et, et = _extratrees_r2(tr_cl, te_cl)
    scores["extra_trees_classic"] = r_et
    meta["extra_trees_classic"] = {}

    Xtr, _, rt = to_design_matrix(tr_cl)
    Xte, _, _ = to_design_matrix(te_cl, rt)
    pred_et = np.clip(et.predict(Xte), 0.0, 1.0)

    r_blend, w = _blend_r2(pred_gbm, pred_et, yte, np.linspace(0, 1, 21))
    scores["blend_ix_ratio_et"] = r_blend
    meta["blend_ix_ratio_et"] = {"w_gbm": round(w, 3)}

    print(f"\n--- {label} ---")
    for k, v in sorted(scores.items(), key=lambda t: -t[1]):
        print(f"  {k:22s}  R2={v:.4f}")
    return {"bracket": label, "scores": scores, "meta": meta}


def pick_winner(th_scores: dict, rd_scores: dict) -> str:
    keys = [k for k in th_scores if k != "extra_trees_classic"]
    return max(keys, key=lambda k: 0.6 * th_scores[k] + 0.4 * rd_scores[k])


def main():
    tr, te = load_raw()
    trc, _, _, _ = prepare(tr, te)
    d48 = trc[trc["day"] == 48].copy()
    ratio = build_ratio_g_table(trc)

    rng = np.random.RandomState(0)
    rmask = rng.rand(len(d48)) < 0.8
    tb = d48["minutes"].isin(TESTBAND).to_numpy()

    print("=== Research tournament (testhours-primary) ===")
    r_th = evaluate_bracket(d48, trc, ratio, ~tb, "TESTHOURS")
    r_rd = evaluate_bracket(d48, trc, ratio, rmask, "RANDOM")

    winner = pick_winner(r_th["scores"], r_rd["scores"])
    th_r2 = r_th["scores"][winner]
    rd_r2 = r_rd["scores"][winner]

    print(f"\nWINNER: {winner}")
    print(f"  testhours R2={th_r2:.4f}  random R2={rd_r2:.4f}")
    print(f"  baseline reference={BASELINE_TH:.4f}  margin={MARGIN}")
    if th_r2 >= BASELINE_TH + MARGIN:
        print("  DECISION: KEEP — beats baseline on testhours by >= margin")
    else:
        print("  DECISION: marginal — submit for LB A/B but keep sub_gbm.csv as anchor")

    report = {
        "results": [r_th, r_rd],
        "winner": winner,
        "winner_testhours_R2": th_r2,
        "winner_random_R2": rd_r2,
        "baseline_testhours_R2": BASELINE_TH,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {OUT}")
    print("-> python submit_research.py")


if __name__ == "__main__":
    main()
