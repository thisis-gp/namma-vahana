"""Compare ML-only variants on three brackets:
  - testhours (2:15-13:45 holdout on Day 48) — primary selector
  - random 80/20 on Day 48
  - day49 morning (reference only)
No lookup in any variant."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import r2_score

from src.pipeline import (
    load_raw, prepare, add_hist_features, build_day48_aggregates, FEATURES, CAT_COLS,
)
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import (
    train_gbm, predict_gbm, train_residual_gbm, predict_residual_gbm, PARAMS,
)
from src.ml_features import (
    FEATURES_V2, RESIDUAL_FEATURES,
    build_geohash_profiles, enrich_ml_features, cat_idx_for,
)

TESTBAND = set(range(2 * 60 + 15, 13 * 60 + 46))


def _prep_fold(d48_raw, train_mask):
    """Build features for a Day-48 fold; agg/sp/profiles from train rows only."""
    train_rows = d48_raw[train_mask].copy()
    hold_rows = d48_raw[~train_mask].copy()
    agg = build_day48_aggregates(train_rows)
    sp = build_spatial_index(train_rows, k=12)
    prof = build_geohash_profiles(train_rows)
    tr = enrich_ml_features(
        add_neighbor_feature(add_hist_features(train_rows, agg, True), sp, agg),
        prof,
    )
    te = enrich_ml_features(
        add_neighbor_feature(add_hist_features(hold_rows, agg, False), sp, agg),
        prof,
    )
    return tr, te


def _score_gbm(cols, tr, te, cat, params=None):
    Xtr, ytr = tr[cols], tr["demand"].to_numpy()
    Xte, yte = te[cols], te["demand"].to_numpy()
    m, bit = train_gbm(Xtr, ytr, cat, eval_X=Xte, eval_y=yte, use_log=True, params=params)
    return r2_score(yte, predict_gbm(m, Xte)), bit


def _score_residual(tr, te, cat, params=None):
    Xtr, ytr = tr[RESIDUAL_FEATURES], tr["demand"].to_numpy()
    btr = tr["hist_g"].to_numpy()
    Xte, yte = te[RESIDUAL_FEATURES], te["demand"].to_numpy()
    bte = te["hist_g"].to_numpy()
    m, bit = train_residual_gbm(
        Xtr, ytr, btr, cat,
        eval_X=Xte, eval_y=yte, eval_baseline=bte,
        params=params,
    )
    return r2_score(yte, predict_residual_gbm(m, Xte, bte)), bit


def run_bracket(name, tr, te):
    cat_v2 = cat_idx_for(FEATURES_V2)
    cat_res = cat_idx_for(RESIDUAL_FEATURES)
    cat_base = [FEATURES.index(c) for c in CAT_COLS]

    r_base, it_base = _score_gbm(FEATURES, tr, te, cat_base)
    r_v2, it_v2 = _score_gbm(FEATURES_V2, tr, te, cat_v2)
    r_res, it_res = _score_residual(tr, te, cat_res)
    print(f"  {name:12s}  baseline={r_base:.4f} (iter={it_base})"
          f"  v2={r_v2:.4f} (iter={it_v2})"
          f"  residual={r_res:.4f} (iter={it_res})")
    return {
        "baseline": (r_base, it_base),
        "v2": (r_v2, it_v2),
        "residual": (r_res, it_res),
    }


def main():
    tr, te = load_raw()
    trc, _tec, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = trc[trc["day"] == 48].copy()
    d49 = trc[trc["day"] == 49].copy()

    rng = np.random.RandomState(0)
    rmask = rng.rand(len(d48)) < 0.8
    tb = d48["minutes"].isin(TESTBAND).to_numpy()

    print("=== ML-only model comparison (no lookup) ===\n")

    # testhours: train outside band, predict band
    tr_th, te_th = _prep_fold(d48, ~tb)
    res_th = run_bracket("TESTHOURS", tr_th, te_th)

    # random 80/20
    tr_rd, te_rd = _prep_fold(d48, rmask)
    res_rd = run_bracket("RANDOM", tr_rd, te_rd)

    # day49 morning (reference)
    prof_full = build_geohash_profiles(d48)
    tr49 = enrich_ml_features(
        add_neighbor_feature(add_hist_features(d49, agg, False), sp, agg),
        prof_full,
    )
    tr48_full = enrich_ml_features(
        add_neighbor_feature(add_hist_features(d48, agg, True), sp, agg),
        prof_full,
    )
    cat_v2 = cat_idx_for(FEATURES_V2)
    cat_res = cat_idx_for(RESIDUAL_FEATURES)
    cat_base = [FEATURES.index(c) for c in CAT_COLS]

    def morning_scores():
        y = tr49["demand"].to_numpy()
        mb, ib = train_gbm(tr48_full[FEATURES], tr48_full["demand"].to_numpy(), cat_base,
                           eval_X=tr49[FEATURES], eval_y=y, use_log=True)
        mv, iv = train_gbm(tr48_full[FEATURES_V2], tr48_full["demand"].to_numpy(), cat_v2,
                           eval_X=tr49[FEATURES_V2], eval_y=y, use_log=True)
        mr, ir = train_residual_gbm(
            tr48_full[RESIDUAL_FEATURES], tr48_full["demand"].to_numpy(),
            tr48_full["hist_g"].to_numpy(), cat_res,
            eval_X=tr49[RESIDUAL_FEATURES], eval_y=y,
            eval_baseline=tr49["hist_g"].to_numpy(),
        )
        rb = r2_score(y, predict_gbm(mb, tr49[FEATURES]))
        rv = r2_score(y, predict_gbm(mv, tr49[FEATURES_V2]))
        rr = r2_score(y, predict_residual_gbm(mr, tr49[RESIDUAL_FEATURES],
                                              tr49["hist_g"].to_numpy()))
        print(f"  {'D49_MORN':12s}  baseline={rb:.4f} (iter={ib})"
              f"  v2={rv:.4f} (iter={iv})"
              f"  residual={rr:.4f} (iter={ir})")
        return {"baseline": (rb, ib), "v2": (rv, iv), "residual": (rr, ir)}

    res_m = morning_scores()

    # pick winner by testhours R2
    winner = max(res_th, key=lambda k: res_th[k][0])
    w_r2, w_iter = res_th[winner]
    print(f"\nWINNER (by TESTHOURS R2): {winner}  R2={w_r2:.4f}  iter={w_iter}")
    print(f"  random R2={res_rd[winner][0]:.4f}  morning R2={res_m[winner][0]:.4f}")
    print(f"  -> set submit_ml.py MODEL={winner!r}  BEST_ITER={w_iter}")


if __name__ == "__main__":
    main()
