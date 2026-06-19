"""Train final model and write submission CSVs.
Trains on Day 48 by default; optionally adds Day 49 if TRAIN_ON_DAY49=True.
Set BEST_ITER / W_LOOKUP / USE_NEIGHBOR_LOOKUP_FOR_BLEND from validate.py first.
"""
import numpy as np
import pandas as pd
from src.pipeline import (load_raw, prepare, add_hist_features, lookup_pred,
                          FEATURES, CAT_COLS)
from src.spatial import build_spatial_index, add_neighbor_feature, neighbor_predict
from src.model import train_gbm, predict_gbm

# --- set these from validate.py output ---
BEST_ITER = 245         # solution.ipynb — LB ~90 (morning holdout ~0.77, same as reg_A3)
W_LOOKUP = 0.0          # from validate.py w_lookup
USE_LOG = True
USE_NEIGHBOR_LOOKUP_FOR_BLEND = False  # validate.py printed lookup=plain
TRAIN_ON_DAY49 = False  # IMPORTANT: Day-49 rows are morning-only and `day` is
#   not a feature, so adding them biases the model toward 0:00-2:00 and can hurt
#   the 2:15-13:45 test window. Keep False unless leaderboard feedback says otherwise.


def main():
    tr, te = load_raw()
    trc, tec, agg, _tm = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)

    d48 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 48].copy(), agg, True), sp, agg)
    test = add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg)
    if TRAIN_ON_DAY49:
        d49 = add_neighbor_feature(add_hist_features(trc[trc["day"] == 49].copy(), agg, False), sp, agg)
        train_df = pd.concat([d48, d49], ignore_index=True)
    else:
        train_df = d48

    cat_idx = [FEATURES.index(c) for c in CAT_COLS]
    booster, _ = train_gbm(train_df[FEATURES], train_df["demand"].to_numpy(),
                           cat_idx, use_log=USE_LOG, num_boost_round=BEST_ITER)

    pred_gbm = predict_gbm(booster, test[FEATURES], use_log=USE_LOG)
    pred_lookup = lookup_pred(test, agg)                      # plain ladder (primary)
    nb_test = neighbor_predict(test, sp)
    pred_lookup_nb = lookup_pred(test, agg, neighbor=nb_test) # alt candidate
    # blend with the SAME lookup variant validate.py selected (see flag above)
    lookup_for_blend = pred_lookup_nb if USE_NEIGHBOR_LOOKUP_FOR_BLEND else pred_lookup
    pred_blend = np.clip(W_LOOKUP * lookup_for_blend + (1 - W_LOOKUP) * pred_gbm, 0.0, 1.0)

    def write(name, preds):
        preds = np.asarray(preds, dtype=float)
        out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": preds})
        assert out.shape == (41778, 2), f"bad shape {out.shape}"
        assert list(out.columns) == ["Index", "demand"], "bad column names"
        assert np.isfinite(out["demand"]).all(), "non-finite predictions"
        assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all(), "demand out of [0,1]"
        assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all(), "index order mismatch"
        path = f"submissions/{name}.csv"
        out.to_csv(path, index=False)
        print(f"wrote {path}  mean={preds.mean():.4f} min={preds.min():.4f} max={preds.max():.4f}")

    write("sub_lookup", pred_lookup)            # primary baseline candidate
    write("sub_lookup_nb", pred_lookup_nb)      # neighbor-fallback variant (A/B vs sub_lookup)
    write("sub_gbm", pred_gbm)
    write("sub_blend", pred_blend)


if __name__ == "__main__":
    main()
