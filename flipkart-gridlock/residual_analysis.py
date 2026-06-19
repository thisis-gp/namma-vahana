"""Residual dashboard: where does the Day-48 GBM fail on testhours holdout?"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from src.pipeline import FEATURES, CAT_COLS, load_raw, prepare
from src.model import train_gbm, predict_gbm, PARAMS
from src.research_features import prepare_d48_frame, build_ratio_g_table

TESTBAND = set(range(2 * 60 + 15, 13 * 60 + 46))


def _r2(y, p):
    return float(r2_score(y, p))


def _bucket_report(name, y, p, groups):
    print(f"\n  [{name}]  overall R2={_r2(y, p):.4f}  n={len(y)}")
    for label, mask in groups:
        if mask.sum() < 50:
            continue
        print(f"    {label:28s}  n={int(mask.sum()):5d}  R2={_r2(y[mask], p[mask]):.4f}"
              f"  mean_y={y[mask].mean():.4f}  mean_p={p[mask].mean():.4f}")


def main():
    tr, te = load_raw()
    trc, _, _, _ = prepare(tr, te)
    d48 = trc[trc["day"] == 48].copy()
    ratio = build_ratio_g_table(trc)
    tb = d48["minutes"].isin(TESTBAND).to_numpy()

    tr, hold = prepare_d48_frame(d48, ~tb, ratio, with_ratio=False)
    cat = [FEATURES.index(c) for c in CAT_COLS]
    y = hold["demand"].to_numpy()
    m, bit = train_gbm(
        tr[FEATURES], tr["demand"].to_numpy(), cat,
        eval_X=hold[FEATURES], eval_y=y, use_log=True, params=PARAMS,
    )
    pred = predict_gbm(m, hold[FEATURES])
    resid = y - pred

    print("=== Residual dashboard (baseline GBM, testhours holdout) ===")
    print(f"best_iteration={bit}  overall R2={_r2(y, pred):.4f}")
    print(f"residual std={resid.std():.4f}  mean bias={resid.mean():+.4f}")

    # matched (geohash, timestamp) in train fold
    train_keys = set(zip(tr["geohash"], tr["timestamp"]))
    matched = np.array([
        (g, t) in train_keys for g, t in zip(hold["geohash"], hold["timestamp"])
    ])

    # hist_g deciles on holdout
    dec = pd.qcut(hold["hist_g"], 5, labels=False, duplicates="drop")

    _bucket_report(
        "RoadType",
        y, pred,
        [(f"RoadType={int(rt)}", (hold["RoadType"] == rt).to_numpy())
         for rt in sorted(hold["RoadType"].unique())],
    )
    _bucket_report(
        "hist_g decile",
        y, pred,
        [(f"decile {int(d)}", (dec == d).to_numpy()) for d in sorted(dec.unique())],
    )
    _bucket_report(
        "slot match in train fold",
        y, pred,
        [("matched (g,t)", matched), ("unmatched", ~matched)],
    )

    hours = (hold["minutes"] // 60).astype(int)
    _bucket_report(
        "hour band",
        y, pred,
        [(f"hour {h:02d}", (hours == h).to_numpy()) for h in sorted(hours.unique())],
    )

    print("\nTop |residual| rows share:")
    top = np.argsort(np.abs(resid))[-500:]
    print(f"  unmatched fraction in worst 500: {(~matched[top]).mean():.3f}")
    print(f"  mean hist_g in worst 500: {hold['hist_g'].to_numpy()[top].mean():.4f}")


if __name__ == "__main__":
    main()
