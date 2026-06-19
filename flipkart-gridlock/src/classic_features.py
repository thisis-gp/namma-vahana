"""Feature engineering for classic (linear / tree) ML models.

Organised into interpretable groups for incremental variance (R²) analysis.
No lookup / hist_gt.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.pipeline import (
    load_raw, prepare, add_hist_features, build_day48_aggregates, CAT_COLS,
)
from src.spatial import build_spatial_index, add_neighbor_feature
from src.ml_features import build_geohash_profiles, add_profile_features, add_interactions

TESTHOURS_LO = 2 * 60 + 15
TESTHOURS_HI = 13 * 60 + 45

# Feature groups — order matters for incremental R² reporting
GROUP_LOCATION = [
    "lat", "lon", "hist_g", "hist_g5", "hist_nb",
    "d48_std", "d48_max", "d48_min", "d48_range",
    "d48_morning", "d48_testhrs", "d48_amp", "d48_peak_min",
    "log_hist_g",
]
GROUP_TIME = [
    "minutes", "min_sin", "min_cos", "hist_t",
    "dist_peak", "in_test_band",
]
GROUP_ROAD = ["NumberofLanes", "LargeVehicles", "Landmarks"]
GROUP_WEATHER = ["Temperature"]
GROUP_INTERACTIONS = [
    "ix_g_sin", "ix_g_cos", "ix_g_t", "ix_t_sin", "ix_g_rt",
    "ix_g_band", "ix_t_band",
]

FEATURE_GROUPS = {
    "location": GROUP_LOCATION,
    "time": GROUP_TIME,
    "road": GROUP_ROAD,
    "weather": GROUP_WEATHER,
    "interactions": GROUP_INTERACTIONS,
}
CAT_GROUP = "road_type"  # one-hot RoadType, kept separate

NUMERIC_COLS = (
    GROUP_LOCATION + GROUP_TIME + GROUP_ROAD + GROUP_WEATHER + GROUP_INTERACTIONS
)


def _extra_engineering(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["log_hist_g"] = np.log1p(df["hist_g"].clip(lower=0))
    df["dist_peak"] = (df["minutes"] - df["d48_peak_min"]).abs()
    df["in_test_band"] = (
        (df["minutes"] >= TESTHOURS_LO) & (df["minutes"] <= TESTHOURS_HI)
    ).astype(float)
    df["ix_g_band"] = df["hist_g"] * df["in_test_band"]
    df["ix_t_band"] = df["hist_t"] * df["in_test_band"]
    return df


def build_feature_frame(
    df: pd.DataFrame,
    profiles: dict,
) -> pd.DataFrame:
    """Full classic feature matrix (numeric + raw RoadType for one-hot)."""
    out = add_interactions(add_profile_features(df, profiles))
    return _extra_engineering(out)


def prepare_fold(d48: pd.DataFrame, train_mask: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leak-safe fold: agg / spatial / profiles from train rows only."""
    train_rows = d48[train_mask].copy()
    hold_rows = d48[~train_mask].copy()
    agg = build_day48_aggregates(train_rows)
    sp = build_spatial_index(train_rows, k=12)
    prof = build_geohash_profiles(train_rows)
    tr = build_feature_frame(
        add_neighbor_feature(add_hist_features(train_rows, agg, True), sp, agg),
        prof,
    )
    te = build_feature_frame(
        add_neighbor_feature(add_hist_features(hold_rows, agg, False), sp, agg),
        prof,
    )
    return tr, te


def prepare_full_day48_day49(trc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on all Day 48, features for Day 49 eval (morning reference)."""
    d48 = trc[trc["day"] == 48].copy()
    d49 = trc[trc["day"] == 49].copy()
    agg = build_day48_aggregates(d48)
    sp = build_spatial_index(d48, k=12)
    prof = build_geohash_profiles(d48)
    tr = build_feature_frame(
        add_neighbor_feature(add_hist_features(d48, agg, True), sp, agg),
        prof,
    )
    te = build_feature_frame(
        add_neighbor_feature(add_hist_features(d49, agg, False), sp, agg),
        prof,
    )
    return tr, te


def prepare_full_train_test(trc: pd.DataFrame, tec: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d48 = trc[trc["day"] == 48].copy()
    agg = build_day48_aggregates(d48)
    sp = build_spatial_index(d48, k=12)
    prof = build_geohash_profiles(d48)
    tr = build_feature_frame(
        add_neighbor_feature(add_hist_features(d48, agg, True), sp, agg),
        prof,
    )
    te = build_feature_frame(
        add_neighbor_feature(add_hist_features(tec.copy(), agg, False), sp, agg),
        prof,
    )
    return tr, te


ROADTYPE_CATS = [0, 1, 2, 3]  # Residential, Street, Highway, Unknown


def to_design_matrix(
    df: pd.DataFrame,
    rt_categories: list[int] | None = None,
    numeric_cols: list[str] | None = None,
    include_roadtype: bool = True,
):
    """Numeric matrix + optional one-hot RoadType. Returns (X ndarray, colnames, rt_categories)."""
    rt_cats = rt_categories if rt_categories is not None else ROADTYPE_CATS
    nums = numeric_cols if numeric_cols is not None else NUMERIC_COLS
    parts = [df[nums]]
    colnames = list(nums)
    if include_roadtype:
        for c in rt_cats:
            name = f"RoadType_{c}"
            parts.append((df["RoadType"].astype(int) == c).astype(float).rename(name))
            colnames.append(name)
    X = pd.concat(parts, axis=1)
    return X.to_numpy(dtype=float), colnames, rt_cats
