"""Local validation: train on Day 48, score on Day-49 labels.
Prints R2 for lookup / GBM / blend, the best blend weight, and best_iteration.

Caveat: Day-49 labels are morning-only (0:0-2:0); the real test includes
midday. Treat these numbers as a DIRECTION, not an absolute. See validate_midday.py.
"""
import numpy as np
from sklearn.metrics import r2_score
from src.pipeline import (load_raw, prepare, add_hist_features, lookup_pred,
                          FEATURES, CAT_COLS)
from src.spatial import build_spatial_index, add_neighbor_feature, neighbor_predict
from src.model import train_gbm, predict_gbm


def main():
    tr, te = load_raw()
    trc, _tec, agg, _tm = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)

    d48 = trc[trc["day"] == 48].copy()
    d49 = trc[trc["day"] == 49].copy()
    d48 = add_neighbor_feature(add_hist_features(d48, agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(d49, agg, False), sp, agg)

    cat_idx = [FEATURES.index(c) for c in CAT_COLS]
    model, best_iter = train_gbm(
        d48[FEATURES], d48["demand"].to_numpy(), cat_idx,
        eval_X=d49[FEATURES], eval_y=d49["demand"].to_numpy(), use_log=True)

    pred_gbm = predict_gbm(model, d49[FEATURES], use_log=True)
    # Two lookup candidates. Codex measured that forcing the neighbor into the
    # ladder HURT on this data (0.5226 -> 0.5140), so the plain ladder is primary;
    # we report both and blend with whichever wins.
    nb49 = neighbor_predict(d49, sp)
    pred_lookup = lookup_pred(d49, agg)                   # plain ladder (primary)
    pred_lookup_nb = lookup_pred(d49, agg, neighbor=nb49)
    y = d49["demand"].to_numpy()

    # --- overfit/underfit detector: training R2 vs validation R2 ---
    pred_train = predict_gbm(model, d48[FEATURES], use_log=True)
    r2_train = r2_score(d48["demand"].to_numpy(), pred_train)

    r2_lookup = r2_score(y, pred_lookup)
    r2_lookup_nb = r2_score(y, pred_lookup_nb)
    lk_best, _r2lk = ((pred_lookup, r2_lookup) if r2_lookup >= r2_lookup_nb
                      else (pred_lookup_nb, r2_lookup_nb))
    r2_gbm = r2_score(y, pred_gbm)
    best_w, best_r2 = 0.0, -1e9
    for w in np.linspace(0, 1, 21):
        r2 = r2_score(y, w * lk_best + (1 - w) * pred_gbm)
        if r2 > best_r2:
            best_r2, best_w = r2, w

    print(f"R2 GBM train         : {r2_train:.4f}")
    print(f"R2 GBM valid (D49)   : {r2_gbm:.4f}")
    gap = r2_train - r2_gbm
    diag = ("OVERFIT (train >> valid) -> raise min_child_samples / lower num_leaves"
            if gap > 0.15 else
            "UNDERFIT (both low) -> add features / raise num_leaves"
            if r2_gbm < 0.30 and r2_train < 0.40 else
            "healthy fit")
    print(f"   train-valid gap   : {gap:+.4f}  -> {diag}")
    print(f"R2 lookup (plain)    : {r2_lookup:.4f}")
    print(f"R2 lookup (+neighbor): {r2_lookup_nb:.4f}")
    win = "plain" if r2_lookup >= r2_lookup_nb else "+neighbor"
    print(f"R2 best blend        : {best_r2:.4f}  (w_lookup={best_w:.2f}, lookup={win})")
    print(f"best_iteration       : {best_iter}")
    print("NOTE: best-blend R2 is tuned on these same D49-morning labels -> "
          "optimistic. Use validate_midday.py + the leaderboard for final calibration.")


if __name__ == "__main__":
    main()
