"""Spatial neighbor averaging. Rescues sparse / unseen (geohash, time) cells.

Ladder inside neighbor_predict: nearest Day-48 neighbors at the SAME minute;
if none have a reading (data is ~58% sparse), widen to +/- `window` minutes.
Self is always excluded -> leak-free for Day-48 training rows too.
"""
from __future__ import annotations
import numpy as np
from sklearn.neighbors import KDTree
from src.pipeline import decode_latlon


def build_spatial_index(train_clean, k=12):
    """Index built from DAY 48 only (the reference day, same source as test)."""
    d48 = train_clean[train_clean["day"] == 48]
    geos = d48["geohash"].unique()
    coords = np.array([decode_latlon(g) for g in geos])
    tree = KDTree(coords)
    gt = d48.groupby(["geohash", "minutes"])["demand"].mean()
    gminutes, gdemand = {}, {}
    for g, sub in d48.groupby("geohash"):
        gminutes[g] = sub["minutes"].to_numpy()
        gdemand[g] = sub["demand"].to_numpy()
    return {"geos": geos, "coords": coords, "tree": tree, "gt": gt,
            "gminutes": gminutes, "gdemand": gdemand, "k": k}


def neighbor_predict(df, sp, window=45):
    """Per-row mean demand of the k nearest Day-48 geohashes (excluding self)
    at the same minute; widen to +/- window minutes if the exact minute is empty.
    Returns array with np.nan where even the window has no neighbor data."""
    k = sp["k"]
    geos = sp["geos"]; gt = sp["gt"]
    gmin = sp["gminutes"]; gdem = sp["gdemand"]
    ug = df["geohash"].unique()
    ucoords = np.array([decode_latlon(g) for g in ug])
    # query k+1 to allow dropping self
    _, idx = sp["tree"].query(ucoords, k=min(k + 1, len(geos)))
    nb_map = {}
    for i, g in enumerate(ug):
        cand = [geos[j] for j in idx[i] if geos[j] != g][:k]
        nb_map[g] = cand
    out = np.full(len(df), np.nan)
    gvals = df["geohash"].to_numpy(); mvals = df["minutes"].to_numpy()
    for r in range(len(df)):
        g = gvals[r]; m = int(mvals[r])
        nbs = nb_map.get(g, [])
        vals = [gt.get((nb, m), np.nan) for nb in nbs]
        vals = [v for v in vals if v == v]
        if not vals:
            for nb in nbs:
                mm = gmin.get(nb); 
                if mm is None:
                    continue
                sel = np.abs(mm - m) <= window
                if sel.any():
                    vals.append(float(gdem[nb][sel].mean()))
        if vals:
            out[r] = float(np.mean(vals))
    return out


def add_neighbor_feature(df, sp, agg, window=45):
    """Add hist_nb column; fill remaining gaps with hist_g then global mean."""
    df = df.copy()
    nb = neighbor_predict(df, sp, window=window)
    # use .to_numpy() (positional) to avoid pandas index-alignment footguns
    hist_g = df["hist_g"].to_numpy() if "hist_g" in df.columns else np.full(len(df), np.nan)
    nb = np.where(np.isnan(nb), hist_g, nb)
    df["hist_nb"] = np.where(np.isnan(nb), agg["global_mean"], nb)
    return df
