"""Generate geohash-categorical + RoadType-band-normalized submissions.

This is an experimental path for the score-100 chase. It keeps the current
anchor submissions intact and writes separate A/B CSVs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.pipeline import (
    CAT_COLS,
    FEATURES,
    add_hist_features,
    load_raw,
    prepare,
)
from src.spatial import add_neighbor_feature, build_spatial_index
from src.model import PARAMS, predict_gbm, train_gbm

ROAD_BOUNDS = {
    0: (0.0, 0.22),     # Residential
    1: (0.22, 0.35),   # Street
    2: (0.35, 1.0),    # Highway
    3: (0.0, 1.0),     # Unknown
}

ITERS_GEOCAT = [300, 380, 528]
ITERS_GEOG5 = [260, 300, 340]


def add_geohash_id(df: pd.DataFrame, geo_map: dict[str, int]) -> pd.DataFrame:
    df = df.copy()
    df["geohash_id"] = df["geohash"].map(geo_map).fillna(-1).astype(int)
    return df


def add_geo_ids(
    df: pd.DataFrame,
    geo_map: dict[str, int],
    g5_map: dict[str, int],
) -> pd.DataFrame:
    df = add_geohash_id(df, geo_map)
    df["g5_id"] = df["g5"].map(g5_map).fillna(-1).astype(int)
    return df


def normalize_by_roadtype(df: pd.DataFrame) -> np.ndarray:
    y = df["demand"].to_numpy(dtype=float).copy()
    rt = df["RoadType"].to_numpy()
    for code, (lo, hi) in ROAD_BOUNDS.items():
        mask = rt == code
        y[mask] = (y[mask] - lo) / max(hi - lo, 1e-12)
    return np.clip(y, 0.0, 1.0)


def inverse_by_roadtype(df: pd.DataFrame, pred_norm: np.ndarray) -> np.ndarray:
    pred = np.asarray(pred_norm, dtype=float).copy()
    rt = df["RoadType"].to_numpy()
    for code, (lo, hi) in ROAD_BOUNDS.items():
        mask = rt == code
        pred[mask] = lo + pred[mask] * (hi - lo)
    return np.clip(pred, 0.0, 1.0)


def write_submission(tec: pd.DataFrame, pred: np.ndarray, path: str) -> None:
    pred = np.asarray(pred, dtype=float)
    out = pd.DataFrame({"Index": tec["Index"].to_numpy(), "demand": pred})
    assert out.shape == (41778, 2), out.shape
    assert list(out.columns) == ["Index", "demand"]
    assert np.isfinite(out["demand"]).all()
    assert ((out["demand"] >= 0) & (out["demand"] <= 1)).all()
    assert (out["Index"].to_numpy() == tec["Index"].to_numpy()).all()
    out.to_csv(path, index=False)
    print(f"wrote {path} mean={pred.mean():.5f} min={pred.min():.5f} max={pred.max():.5f}")


def main() -> None:
    train_raw, test_raw = load_raw()
    trc, tec, agg, _ = prepare(train_raw, test_raw)
    sp = build_spatial_index(trc, k=12)

    geo_values = pd.Index(pd.concat([train_raw["geohash"], test_raw["geohash"]]).unique())
    geo_map = {g: i for i, g in enumerate(geo_values)}
    g5_values = pd.Index(pd.concat([train_raw["geohash"].str[:5], test_raw["geohash"].str[:5]]).unique())
    g5_map = {g: i for i, g in enumerate(g5_values)}

    d48 = trc[trc["day"] == 48].copy()
    train_df = add_geo_ids(
        add_neighbor_feature(add_hist_features(d48, agg, True), sp, agg),
        geo_map,
        g5_map,
    )
    test_df = add_geo_ids(
        add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg),
        geo_map,
        g5_map,
    )

    y_norm = normalize_by_roadtype(train_df)
    variants = [
        ("geocat", FEATURES + ["geohash_id"], ["NumberofLanes", "geohash_id"], ITERS_GEOCAT),
        ("geog5", FEATURES + ["geohash_id", "g5_id"], ["NumberofLanes", "geohash_id", "g5_id"], ITERS_GEOG5),
    ]

    for name, cols, extra_cats, iters in variants:
        cat_idx = [cols.index(c) for c in CAT_COLS] + [cols.index(c) for c in extra_cats]
        for n_iter in iters:
            model, _ = train_gbm(
                train_df[cols],
                y_norm,
                cat_idx,
                use_log=False,
                num_boost_round=n_iter,
                params=PARAMS,
            )
            pred_norm = predict_gbm(model, test_df[cols], use_log=False)
            pred = inverse_by_roadtype(test_df, pred_norm)
            write_submission(tec, pred, f"submissions/sub_{name}_rtnorm_{n_iter}.csv")


if __name__ == "__main__":
    main()
