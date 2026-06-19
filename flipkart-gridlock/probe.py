"""Feature-relationship probe. Reports only -- does not change any model.
Detects non-linear feature->demand dependence (mutual information),
multicollinearity (feature-feature correlation), and what the model uses."""
import numpy as np
from sklearn.feature_selection import mutual_info_regression
from sklearn.metrics import r2_score
from src.pipeline import load_raw, prepare, add_hist_features, FEATURES, CAT_COLS
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm


def main():
    tr, te = load_raw()
    trc, _te, agg, _ = prepare(tr, te)
    sp = build_spatial_index(trc, k=12)
    d48 = add_neighbor_feature(add_hist_features(trc[trc.day == 48].copy(), agg, True), sp, agg)
    d49 = add_neighbor_feature(add_hist_features(trc[trc.day == 49].copy(), agg, False), sp, agg)
    X = d48[FEATURES].fillna(0.0)
    y = d48["demand"].to_numpy()
    disc = [f in CAT_COLS for f in FEATURES]  # mark categoricals as discrete

    print("== Mutual information (non-linear dependence) feature -> demand ==")
    mi = mutual_info_regression(X, y, discrete_features=disc, random_state=0)
    for f, v in sorted(zip(FEATURES, mi), key=lambda t: -t[1]):
        print(f"  {f:14s} MI={v:.4f}")

    print("\n== Pearson corr feature <-> demand (linear only) ==")
    for f in FEATURES:
        print(f"  {f:14s} r={np.corrcoef(X[f], y)[0,1]:+.4f}")

    print("\n== Feature-feature |corr| > 0.8 (multicollinearity) ==")
    C = X.corr().abs()
    hits = 0
    for i, a in enumerate(FEATURES):
        for b in FEATURES[i + 1:]:
            if C.loc[a, b] > 0.8:
                print(f"  {a} ~ {b}: {C.loc[a, b]:.3f}"); hits += 1
    if not hits:
        print("  (none > 0.8)")

    print("\n== LightGBM gain importance (train day48, valid day49 morning) ==")
    cat = [FEATURES.index(c) for c in CAT_COLS]
    m, bit = train_gbm(d48[FEATURES], y, cat, eval_X=d49[FEATURES],
                       eval_y=d49["demand"].to_numpy(), use_log=True)
    imp = m.feature_importance(importance_type="gain"); tot = imp.sum()
    for f, v in sorted(zip(FEATURES, imp), key=lambda t: -t[1]):
        print(f"  {f:14s} gain={100*v/tot:5.1f}%")
    r2 = r2_score(d49["demand"].to_numpy(), predict_gbm(m, d49[FEATURES]))
    print(f"  morning valid R2={r2:.4f}  best_iter={bit}")
    print("\nINTERPRET: a feature with HIGH MI but LOW gain% is underused -> a hidden")
    print("relationship worth a transform/interaction. Multicollinearity doesn't hurt")
    print("tree prediction, but a |corr|~1.0 pair means one feature is redundant.")


if __name__ == "__main__":
    main()
