"""Research features: cross-day ratio_g + GBM interaction terms."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.pipeline import (
    FEATURES, CAT_COLS, load_raw, prepare, add_hist_features, build_day48_aggregates,
)
from src.spatial import build_spatial_index, add_neighbor_feature

MORNING_MAX = 2 * 60
TESTHOURS_LO = 2 * 60 + 15
TESTHOURS_HI = 13 * 60 + 45

INTERACTION_COLS = ["ix_g_sin", "ix_g_rt", "ix_t_band"]
RATIO_COL = "ratio_g"

FEATURES_IX = FEATURES + INTERACTION_COLS
FEATURES_IX_RATIO = FEATURES_IX + [RATIO_COL]


def build_ratio_g_table(trc: pd.DataFrame) -> dict:
    """Per-geohash D49-morning / D48-morning demand ratio (scalar calibration)."""
    d48 = trc[trc["day"] == 48]
    d49 = trc[trc["day"] == 49]
    m48 = d48.loc[d48["minutes"] <= MORNING_MAX].groupby("geohash")["demand"].mean()
    m49 = d49.groupby("geohash")["demand"].mean()
    g_ratio = (m49 / m48.clip(lower=1e-6)).replace([np.inf, -np.inf], np.nan)

    d48m = d48.loc[d48["minutes"] <= MORNING_MAX]
    g5_48 = d48m.groupby("g5")["demand"].mean()
    g5_49 = d49.groupby("g5")["demand"].mean()
    g5_ratio = (g5_49 / g5_48.clip(lower=1e-6)).replace([np.inf, -np.inf], np.nan)

    global_ratio = float(d49["demand"].mean() / max(d48m["demand"].mean(), 1e-6))
    return {"g": g_ratio, "g5": g5_ratio, "global": global_ratio}


def add_ratio_g(df: pd.DataFrame, ratio: dict) -> pd.DataFrame:
    df = df.copy()
    s = df["geohash"].map(ratio["g"])
    s = s.fillna(df["g5"].map(ratio["g5"]))
    df[RATIO_COL] = s.fillna(ratio["global"]).clip(0.1, 10.0)
    return df


def add_gbm_interactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    in_band = (
        (df["minutes"] >= TESTHOURS_LO) & (df["minutes"] <= TESTHOURS_HI)
    ).astype(float)
    df["ix_g_sin"] = df["hist_g"] * df["min_sin"]
    df["ix_g_rt"] = df["hist_g"] * df["RoadType"].astype(float)
    df["ix_t_band"] = df["hist_t"] * in_band
    return df


def enrich_research(
    df: pd.DataFrame,
    ratio: dict,
    with_ratio: bool = True,
) -> pd.DataFrame:
    return add_ratio_g(add_gbm_interactions(df), ratio) if with_ratio else add_gbm_interactions(df)


def prepare_d48_frame(
    d48: pd.DataFrame,
    train_mask: np.ndarray,
    ratio: dict,
    with_ratio: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leak-safe Day-48 fold: agg/sp from train rows only."""
    train_rows = d48[train_mask].copy()
    hold_rows = d48[~train_mask].copy()
    agg = build_day48_aggregates(train_rows)
    sp = build_spatial_index(train_rows, k=12)
    tr = enrich_research(
        add_neighbor_feature(add_hist_features(train_rows, agg, True), sp, agg),
        ratio, with_ratio=with_ratio,
    )
    te = enrich_research(
        add_neighbor_feature(add_hist_features(hold_rows, agg, False), sp, agg),
        ratio, with_ratio=with_ratio,
    )
    return tr, te


def prepare_full_d48_test(
    trc: pd.DataFrame,
    tec: pd.DataFrame,
    ratio: dict,
    with_ratio: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    d48 = trc[trc["day"] == 48].copy()
    agg = build_day48_aggregates(d48)
    sp = build_spatial_index(d48, k=12)
    tr = enrich_research(
        add_neighbor_feature(add_hist_features(d48, agg, True), sp, agg),
        ratio, with_ratio=with_ratio,
    )
    te = enrich_research(
        add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg),
        ratio, with_ratio=with_ratio,
    )
    return tr, te


def cat_idx(cols: list[str]) -> list[int]:
    return [cols.index(c) for c in CAT_COLS]
