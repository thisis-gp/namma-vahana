"""ML-only feature engineering: Day-48 geohash profiles + interaction terms.

No lookup / hist_gt — only legitimate aggregates the model learns to use.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.pipeline import FEATURES, CAT_COLS

MORNING_MAX = 2 * 60          # 0:00-2:00
TESTHOURS_LO = 2 * 60 + 15    # 2:15
TESTHOURS_HI = 13 * 60 + 45   # 13:45

PROFILE_COLS = [
    "d48_std", "d48_max", "d48_min", "d48_range",
    "d48_morning", "d48_testhrs", "d48_amp", "d48_peak_min",
]
INTERACTION_COLS = [
    "ix_g_sin", "ix_g_cos", "ix_g_t", "ix_t_sin", "ix_g_rt",
]

FEATURES_V2 = FEATURES + PROFILE_COLS + INTERACTION_COLS
RESIDUAL_FEATURES = [f for f in FEATURES_V2 if f != "hist_g"]


def _geohash_stats(sub: pd.DataFrame) -> dict:
    d = sub["demand"]
    morn = sub.loc[sub["minutes"] <= MORNING_MAX, "demand"]
    test = sub.loc[
        (sub["minutes"] >= TESTHOURS_LO) & (sub["minutes"] <= TESTHOURS_HI), "demand"
    ]
    morn_m = float(morn.mean()) if len(morn) else float(d.mean())
    test_m = float(test.mean()) if len(test) else float(d.mean())
    peak_row = sub.loc[sub["demand"].idxmax()]
    return {
        "d48_std": float(d.std()) if len(d) > 1 else 0.0,
        "d48_max": float(d.max()),
        "d48_min": float(d.min()),
        "d48_range": float(d.max() - d.min()),
        "d48_morning": morn_m,
        "d48_testhrs": test_m,
        "d48_amp": test_m / max(morn_m, 1e-6),
        "d48_peak_min": float(peak_row["minutes"]),
    }


def build_geohash_profiles(d48: pd.DataFrame) -> dict:
    """Per-geohash Day-48 demand shape stats. Leak-free for inference when
    `d48` is the training fold only."""
    g_prof: dict[str, dict[str, float]] = {}
    for g, sub in d48.groupby("geohash"):
        g_prof[g] = _geohash_stats(sub)

    g5_prof: dict[str, dict[str, float]] = {}
    for g5, sub in d48.groupby("g5"):
        g5_prof[g5] = _geohash_stats(sub)

    global_prof = _geohash_stats(d48)
    return {"g": g_prof, "g5": g5_prof, "global": global_prof}


def add_profile_features(df: pd.DataFrame, profiles: dict) -> pd.DataFrame:
    df = df.copy()
    g_prof, g5_prof, global_prof = profiles["g"], profiles["g5"], profiles["global"]
    for col in PROFILE_COLS:
        s = df["geohash"].map({g: p[col] for g, p in g_prof.items()})
        s = s.fillna(df["g5"].map({g5: p[col] for g5, p in g5_prof.items()}))
        df[col] = s.fillna(global_prof[col])
    return df


def add_interactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ix_g_sin"] = df["hist_g"] * df["min_sin"]
    df["ix_g_cos"] = df["hist_g"] * df["min_cos"]
    df["ix_g_t"] = df["hist_g"] * df["hist_t"]
    df["ix_t_sin"] = df["hist_t"] * df["min_sin"]
    df["ix_g_rt"] = df["hist_g"] * df["RoadType"].astype(float)
    return df


def enrich_ml_features(
    df: pd.DataFrame,
    profiles: dict,
) -> pd.DataFrame:
    """Add profile + interaction columns after hist_* and hist_nb exist."""
    return add_interactions(add_profile_features(df, profiles))


def cat_idx_for(cols: list[str]) -> list[int]:
    return [cols.index(c) for c in CAT_COLS]
