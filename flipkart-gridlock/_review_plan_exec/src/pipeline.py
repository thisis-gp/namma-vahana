"""Data loading, cleaning, geohash decoding, Day-48 aggregates, hist features, lookup ladder.

All historical features come from DAY 48 only. Day-48 training rows get
leave-one-out (LOO) aggregates; Day-49 and test rows get plain Day-48 means
from the identical source, so training mirrors inference.
"""
from __future__ import annotations
import functools
import numpy as np
import pandas as pd
import pygeohash as pgh

DATA_DIR = "dataset"

CAT_COLS = ["RoadType", "LargeVehicles", "Landmarks", "Weather"]
CAT_MAPS = {
    "RoadType":      {"Residential": 0, "Street": 1, "Highway": 2, "Unknown": 3},
    "LargeVehicles": {"Not Allowed": 0, "Allowed": 1, "Unknown": 2},
    "Landmarks":     {"No": 0, "Yes": 1, "Unknown": 2},
    "Weather":       {"Sunny": 0, "Rainy": 1, "Foggy": 2, "Snowy": 3, "Unknown": 4},
}

# hist_nb (neighbor prior) is added by src.spatial; it is part of FEATURES so
# validate/submit must call spatial.add_neighbor_feature before selecting FEATURES.
FEATURES = [
    "lat", "lon", "minutes", "min_sin", "min_cos",
    "NumberofLanes", "Temperature",
    "RoadType", "LargeVehicles", "Landmarks", "Weather",
    "hist_g", "hist_t", "hist_g5", "hist_nb",
]
# hist_gt (exact self lookup) is NOT a GBM feature (LOO undefined for Day-48
# rows). It is used only by the lookup ladder, leak-free for Day-49/test.


@functools.lru_cache(maxsize=None)
def decode_latlon(gh: str):
    ll = pgh.decode(gh)
    return ll.latitude, ll.longitude


def _parse_minutes(ts: pd.Series) -> pd.Series:
    parts = ts.str.split(":", expand=True).astype(int)
    return parts[0] * 60 + parts[1]


def load_raw():
    train = pd.read_csv(f"{DATA_DIR}/train.csv")
    test = pd.read_csv(f"{DATA_DIR}/test.csv")
    return train, test


def basic_clean(df: pd.DataFrame, temp_median: float) -> pd.DataFrame:
    """Add minutes/cyclical/geo features, impute, encode categoricals.
    temp_median is computed once from TRAIN and reused for test."""
    df = df.copy()
    df["minutes"] = _parse_minutes(df["timestamp"])
    df["min_sin"] = np.sin(2 * np.pi * df["minutes"] / 1440.0)
    df["min_cos"] = np.cos(2 * np.pi * df["minutes"] / 1440.0)
    df["g5"] = df["geohash"].str[:5]
    latlon = df["geohash"].map(decode_latlon)
    df["lat"] = latlon.map(lambda t: t[0]).astype(float)
    df["lon"] = latlon.map(lambda t: t[1]).astype(float)
    df["Temperature"] = df["Temperature"].fillna(temp_median)
    df["NumberofLanes"] = df["NumberofLanes"].fillna(0).astype(int)
    for c in CAT_COLS:
        # unseen categories -> Unknown code (never NaN, so .astype(int) is safe)
        df[c] = (df[c].fillna("Unknown").map(CAT_MAPS[c])
                 .fillna(CAT_MAPS[c]["Unknown"]).astype(int))
    return df


def build_day48_aggregates(train_clean: pd.DataFrame) -> dict:
    """Sum/count tables from DAY 48 only, for hist features + LOO + lookup."""
    d48 = train_clean[train_clean["day"] == 48]
    agg = {
        "global_mean": float(d48["demand"].mean()),
        "gt": d48.groupby(["geohash", "timestamp"])["demand"].mean(),
        "g_sum": d48.groupby("geohash")["demand"].sum(),
        "g_cnt": d48.groupby("geohash")["demand"].count(),
        "t_sum": d48.groupby("timestamp")["demand"].sum(),
        "t_cnt": d48.groupby("timestamp")["demand"].count(),
        "g5_sum": d48.groupby("g5")["demand"].sum(),
        "g5_cnt": d48.groupby("g5")["demand"].count(),
    }
    agg["g_mean"] = agg["g_sum"] / agg["g_cnt"]
    agg["t_mean"] = agg["t_sum"] / agg["t_cnt"]
    agg["g5_mean"] = agg["g5_sum"] / agg["g5_cnt"]
    return agg


def _loo_mean(keys, demand, key_sum, key_cnt, fallback):
    s = key_sum.reindex(keys).to_numpy()
    c = key_cnt.reindex(keys).to_numpy()
    out = np.where(c > 1, (s - demand) / np.maximum(c - 1, 1), np.nan)
    return pd.Series(out).fillna(fallback).to_numpy()


def add_hist_features(df: pd.DataFrame, agg: dict, is_day48_train: bool) -> pd.DataFrame:
    """Attach hist_g, hist_t, hist_g5. LOO for Day-48 training rows; plain
    Day-48 means for Day-49/test rows."""
    df = df.copy()
    gm = agg["global_mean"]
    if is_day48_train:
        d = df["demand"].to_numpy()
        df["hist_g"]  = _loo_mean(df["geohash"], d, agg["g_sum"],  agg["g_cnt"],  gm)
        df["hist_t"]  = _loo_mean(df["timestamp"], d, agg["t_sum"], agg["t_cnt"], gm)
        df["hist_g5"] = _loo_mean(df["g5"], d, agg["g5_sum"], agg["g5_cnt"], gm)
    else:
        df["hist_g"]  = df["geohash"].map(agg["g_mean"]).fillna(
                        df["g5"].map(agg["g5_mean"])).fillna(gm)
        df["hist_t"]  = df["timestamp"].map(agg["t_mean"]).fillna(gm)
        df["hist_g5"] = df["g5"].map(agg["g5_mean"]).fillna(gm)
    return df


def lookup_pred(df: pd.DataFrame, agg: dict, neighbor=None) -> np.ndarray:
    """Lookup ladder:
      1. exact (geohash, timestamp) Day-48 demand
      2. neighbor mean at that time (if `neighbor` array supplied by src.spatial)
      3. geohash daily mean -> 4. g5 prefix mean -> 5. time mean -> 6. global mean
    Leak-free for Day-49/test rows."""
    gm = agg["global_mean"]
    gt = agg["gt"]
    keys = list(zip(df["geohash"], df["timestamp"]))
    p = pd.Series([gt.get(k, np.nan) for k in keys], index=df.index)
    if neighbor is not None:
        p = p.fillna(pd.Series(neighbor, index=df.index))
    p = p.fillna(df["geohash"].map(agg["g_mean"]))
    p = p.fillna(df["g5"].map(agg["g5_mean"]))
    p = p.fillna(df["timestamp"].map(agg["t_mean"]))
    p = p.fillna(gm)
    return np.clip(p.to_numpy(), 0.0, 1.0)


def prepare(train_raw: pd.DataFrame, test_raw: pd.DataFrame):
    """Full prep: returns (train_clean, test_clean, agg, temp_median)."""
    temp_median = float(train_raw["Temperature"].median())
    train_clean = basic_clean(train_raw, temp_median)
    test_clean = basic_clean(test_raw, temp_median)
    agg = build_day48_aggregates(train_clean)
    return train_clean, test_clean, agg, temp_median