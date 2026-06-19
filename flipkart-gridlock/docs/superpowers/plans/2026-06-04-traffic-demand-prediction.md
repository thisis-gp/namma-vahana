# Traffic Demand Prediction — Implementation Plan

> **For the implementing agent (Cursor):** Execute task-by-task, top to bottom. Each task lists exact files and complete code — paste it as written. After each task, run the listed command and confirm the expected output before moving on. This is a data-science pipeline, not a web app: "verification" means a printed R² / shape, not unit tests.

**Goal:** Predict day-49 traffic `demand` per `(geohash, timestamp)` and produce a 41,778-row submission that maximizes R².

**Architecture:** Blend two predictors. (1) A **historical lookup** — copy Day-48's value for the same location+time, falling back through coarser averages (geohash → g5 prefix → time-of-day → global) when it's missing. A spatial **nearest-neighbor** estimate is kept as a *separate, opt-in candidate* (not forced into the ladder — it measured slightly worse on this data), and is also fed to the model as a `hist_nb` prior. (2) A **LightGBM "structure" model** trained on Day 48's full 24 hours that learns demand as a function of location (lat/lon), time-of-day, road type, weather, plus the neighbor prior. All historical features come from Day 48 only, with leave-one-out for Day-48 training rows to prevent leakage. Validation trains on Day 48 and scores on Day-49 labels; a separate **honesty-check** holds out the real test hours (2:15–13:45) from Day 48 to measure how much to trust that (Day-49 labels are morning-only).

**Tech Stack:** Python 3.14, pandas, numpy, scikit-learn (KDTree, r2_score), lightgbm, pygeohash.

---

## Key dataset facts (verified — sanity-check, don't re-derive)

- `dataset/train.csv`: 77,299 rows. `day ∈ {48, 49}`. Day 48 = 69,427 rows (full day, all 96 fifteen-minute slots). Day 49 = 7,872 rows (9 **morning** slots only: `0:0`–`2:0`).
- `dataset/test.csv`: 41,778 rows, `day = 49` only, 47 timestamps. **No timestamp overlap** with Day-49 train. **All test timestamps exist in Day 48.**
- 37,136 / 41,778 test rows (**89%**) have an exact `(geohash, timestamp)` match in Day 48. The other 11% need the spatial ladder / model.
- **Data is SPARSE:** Day 48 has 69,427 rows but a full grid (1,241 geohashes × 96 timestamps) would be 119,136 — only ~58% of cells exist. Neighbor lookups must use a **time window**, not just the exact minute.
- `geohash`: 6 chars, decodable to lat/lon. Train 1,249 unique, test 1,190; **10 geohashes appear only in test** (no Day-48 data at all).
- Target `demand` ∈ (0, 1], right-skewed (mean 0.094, median 0.048, max 1.0).
- Nulls: `Temperature` 2,495, `Weather` 797, `RoadType` 600. `LargeVehicles`, `Landmarks`: none.
- Categories: `RoadType` ∈ {Residential, Street, Highway}; `LargeVehicles` ∈ {Allowed, Not Allowed}; `Landmarks` ∈ {Yes, No}; `Weather` ∈ {Sunny, Rainy, Foggy, Snowy}; `NumberofLanes` ∈ {1..5}.
- **Benchmark to beat:** Day-48 lookup ladder on the full Day-49 (morning) holdout = R² ≈ **0.52** (Codex measured 0.5226 plain; the neighbor-in-ladder variant was slightly worse at 0.5140). The plain ladder is the anchor.

**Evaluation:** `score = max(0, 100 × R²)`. We track plain R² locally.

---

## File structure

```
flipkart-gridlock/
├── dataset/                  # given (read-only)
├── src/
│   ├── __init__.py
│   ├── pipeline.py           # load, clean, geohash decode, Day-48 aggregates, hist features, lookup ladder
│   ├── spatial.py            # KDTree neighbor index + neighbor predictor + neighbor feature
│   └── model.py              # LightGBM train + predict
├── validate.py               # train Day48 -> score Day49: R2 for lookup / GBM / blend
├── validate_midday.py        # honesty-check: model skill on midday vs morning (within Day 48)
├── submit.py                 # train final -> write submission CSVs
├── export_notebook.py        # bundle pipeline into solution.ipynb for upload
├── submissions/              # output CSVs (runtime)
└── docs/superpowers/plans/2026-06-04-traffic-demand-prediction.md
```

Single source of truth: `pipeline.py` defines `FEATURES` and `CAT_COLS`; every other file imports them so train/val/submit can never drift.

---

## Task 0: Environment setup

**Files:** none.

- [ ] **Step 1: Install dependencies**

Run:
```bash
pip install -q pandas numpy scikit-learn lightgbm pygeohash nbformat
```

- [ ] **Step 2: Verify imports + decoder**

Run:
```bash
python -c "import pandas, numpy, sklearn, lightgbm, pygeohash as pgh; from sklearn.neighbors import KDTree; print(pgh.decode('qp02z1'))"
```
Expected: prints `LatLong(latitude=-5.48492431640625, longitude=90.6646728515625)`, no import errors.

- [ ] **Step 3: Create folders**

Run:
```bash
python -c "import os; [os.makedirs(p, exist_ok=True) for p in ['src','submissions']]; open('src/__init__.py','a').close()"
```

---

## Task 1: Data pipeline (`src/pipeline.py`)

**Files:** Create `src/pipeline.py`.

Loads data, parses timestamps to minutes, decodes geohashes (cached), imputes nulls, builds **Day-48 aggregates**, exposes **hist features** (with leave-one-out) and the **lookup ladder**.

- [ ] **Step 1: Write `src/pipeline.py`**

```python
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
```

- [ ] **Step 2: Smoke-test**

Run:
```bash
python -c "from src.pipeline import *; tr,te=load_raw(); trc,tec,agg,tm=prepare(tr,te); print('train',trc.shape,'test',tec.shape,'temp_median',round(tm,3)); print('lookup head', lookup_pred(tec,agg)[:3])"
```
Expected: `train (77299, ...) test (41778, ...)`, a finite temp_median, 3 finite lookup values ~0–0.3.

---

## Task 2: Spatial neighbor module (`src/spatial.py`)

**Files:** Create `src/spatial.py`.

Builds a KDTree over geohash coordinates and computes, for each row, the **average demand of its nearest Day-48 neighbors at the same time** (with a time-window fallback because the data is sparse). Self is always excluded, so the result is a leak-free "what are nearby streets doing" prior — used as the **optional** neighbor lookup candidate (`sub_lookup_nb`, not the default ladder) and as the model feature `hist_nb`.

- [ ] **Step 1: Write `src/spatial.py`**

```python
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
```

- [ ] **Step 2: Smoke-test the neighbor predictor**

Run:
```bash
python -c "
from src.pipeline import load_raw, prepare, add_hist_features
from src.spatial import build_spatial_index, add_neighbor_feature, neighbor_predict
tr,te=load_raw(); trc,tec,agg,tm=prepare(tr,te)
sp=build_spatial_index(trc, k=12)
tec2=add_hist_features(tec, agg, is_day48_train=False)
tec2=add_neighbor_feature(tec2, sp, agg)
import numpy as np
print('hist_nb nulls:', int(tec2.hist_nb.isna().sum()), 'mean:', round(float(tec2.hist_nb.mean()),4))
# the 10 test-only geohashes must now get a non-null neighbor prediction
only=sorted(set(te.geohash)-set(tr.geohash))
sub=tec2[tec2.geohash.isin(only)]
print('test-only rows:', len(sub), 'with finite hist_nb:', int(sub.hist_nb.notna().sum()))
"
```
Expected: `hist_nb nulls: 0`; all test-only rows have a finite `hist_nb` (no blind guesses). Runtime up to ~20s (the window loop) is fine.

---

## Task 3: LightGBM model (`src/model.py`)

**Files:** Create `src/model.py`.

- [ ] **Step 1: Write `src/model.py`**

```python
"""LightGBM training + prediction with optional log1p target transform."""
from __future__ import annotations
import numpy as np
import lightgbm as lgb

PARAMS = dict(
    objective="regression",
    metric="rmse",
    learning_rate=0.03,
    num_leaves=63,
    min_child_samples=40,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    lambda_l2=1.0,
    verbose=-1,
)


def train_gbm(X, y, cat_idx, eval_X=None, eval_y=None,
              use_log=True, num_boost_round=3000):
    """Train LightGBM. With an eval set: early-stop and return best_iteration;
    else train full num_boost_round. Returns (booster, best_iteration)."""
    yt = np.log1p(y) if use_log else y
    dtrain = lgb.Dataset(X, label=yt, categorical_feature=cat_idx)
    callbacks = [lgb.log_evaluation(period=0)]
    valid_sets = None
    if eval_X is not None:
        eyt = np.log1p(eval_y) if use_log else eval_y
        dvalid = lgb.Dataset(eval_X, label=eyt, categorical_feature=cat_idx,
                             reference=dtrain)
        valid_sets = [dvalid]
        callbacks.append(lgb.early_stopping(stopping_rounds=100, verbose=False))
    booster = lgb.train(PARAMS, dtrain, num_boost_round=num_boost_round,
                        valid_sets=valid_sets, callbacks=callbacks)
    best_iter = booster.best_iteration or num_boost_round
    return booster, best_iter


def predict_gbm(booster, X, use_log=True):
    raw = booster.predict(X, num_iteration=booster.best_iteration or None)
    pred = np.expm1(raw) if use_log else raw
    return np.clip(pred, 0.0, 1.0)
```

- [ ] **Step 2: Verify it trains**

Run:
```bash
python -c "import numpy as np; from src.model import train_gbm, predict_gbm; X=np.random.rand(500,15); y=np.random.rand(500)*0.3; b,it=train_gbm(X,y,[7,8,9,10],num_boost_round=50); p=predict_gbm(b,X); print('ok', p.shape, 'iters', it)"
```
Expected: `ok (500,) iters 50`, no errors. (15 cols matches `len(FEATURES)`; dummy cat_idx.)

---

## Task 4: Day-49 validation (`validate.py`)

**Files:** Create `validate.py`.

Trains the GBM on Day 48, predicts Day 49, reports R² for lookup / GBM / blend and the best blend weight + best_iteration to reuse in `submit.py`.

- [ ] **Step 1: Write `validate.py`**

```python
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
```

- [ ] **Step 2: Run validation**

Run:
```bash
python validate.py
```
Expected: `R2 lookup (plain)` ≈ 0.52; `R2 lookup (+neighbor)` ≈ 0.51 (slightly worse — that's the point). `R2 best blend` ≥ `max(lookup, GBM)`. The `train-valid gap` line should read `healthy fit` — if `OVERFIT`, raise `min_child_samples` / lower `num_leaves` in `model.py`; if `UNDERFIT`, add features / raise `num_leaves`. **Record `w_lookup`, `best_iteration`, and the `lookup=` winner** (set `submit.py`'s `USE_NEIGHBOR_LOOKUP_FOR_BLEND=True` only if it printed `lookup=+neighbor`). If the blend is worse than both components, stop and report — feature misalignment.

---

## Task 5: Midday honesty-check (`validate_midday.py`)

**Files:** Create `validate_midday.py`.

Day-49 labels are morning-only (0:00–2:00), but the real test is the contiguous band **2:15–13:45** (47 slots). So `validate.py` scores on hours *adjacent to but different from* the test. Day 48 has all hours — so we measure the model's skill on the **morning** band vs the **true test-hours** band by holding each out of Day 48 (rebuilding all aggregates from the kept rows so nothing leaks). If test-hours R² ≪ morning R², discount `validate.py`'s number.

- [ ] **Step 1: Write `validate_midday.py`**

```python
"""Honesty-check: is the model as good on the real TEST hours (2:15-13:45) as
on the morning hours validate.py scores on (0:00-2:00)?

Within Day 48: hold out a band of hours, REBUILD all aggregates from the kept
rows only (no leak), train on the rest, predict the band. Compare the two bands'
R2. A big gap means validate.py (morning-only) is optimistic vs the leaderboard.
"""
import numpy as np
from sklearn.metrics import r2_score
from src.pipeline import (load_raw, prepare, add_hist_features,
                          build_day48_aggregates, FEATURES, CAT_COLS)
from src.spatial import build_spatial_index, add_neighbor_feature
from src.model import train_gbm, predict_gbm

# Day-49 TRAIN labels are 0:00-2:00; the real TEST is the contiguous band
# 2:15-13:45 (47 slots) -- NOT just midday. Hold out the true test hours.
MORNING   = set(range(0, 2 * 60 + 1))               # 0:00-2:00  (matches Day-49 TRAIN)
TESTHOURS = set(range(2 * 60 + 15, 13 * 60 + 46))   # 2:15-13:45 (matches real TEST)


def run_band(d48, band, label):
    """Hold out `band` from Day 48; rebuild aggregates + spatial index from the
    KEPT rows ONLY, so held-out targets never leak through hist_* or neighbors
    (BLOCKER fix). Then predict the band as pure inference. This is a conservative
    lower bound on skill -- in reality Day-48 features for those hours DO exist."""
    hold = d48[d48["minutes"].isin(band)].copy()
    keep = d48[~d48["minutes"].isin(band)].copy()
    agg_k = build_day48_aggregates(keep)
    sp_k = build_spatial_index(keep, k=12)
    keep = add_neighbor_feature(add_hist_features(keep, agg_k, True), sp_k, agg_k)
    hold = add_neighbor_feature(add_hist_features(hold, agg_k, False), sp_k, agg_k)
    cat_idx = [FEATURES.index(c) for c in CAT_COLS]
    m, _ = train_gbm(keep[FEATURES], keep["demand"].to_numpy(), cat_idx,
                     use_log=True, num_boost_round=800)
    p = predict_gbm(m, hold[FEATURES], use_log=True)
    r2 = r2_score(hold["demand"].to_numpy(), p)
    print(f"{label:9s}: model R2 = {r2:.4f}  (n={len(hold)}, mean demand={hold['demand'].mean():.3f})")
    return r2


def main():
    tr, te = load_raw()
    trc, _tec, _agg, _tm = prepare(tr, te)
    d48 = trc[trc["day"] == 48].copy()
    r2_morn = run_band(d48, MORNING, "MORNING")
    r2_test = run_band(d48, TESTHOURS, "TESTHOURS")
    gap = r2_morn - r2_test
    print(f"\nGap (morning - testhours) = {gap:+.4f}")
    if gap > 0.05:
        print("WARNING: weaker on test-like hours -> trust validate.py (morning) LESS;"
              " expect leaderboard below the Day-49 number.")
    else:
        print("OK: test-hours skill ~ morning skill -> validate.py is a fair proxy.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the honesty-check**

Run:
```bash
python validate_midday.py
```
Expected: two R² lines (`MORNING`, `TESTHOURS`) + a gap verdict. These are **conservative** (features rebuilt from kept rows only), so absolute values will look lower than `validate.py` — what matters is the *gap* between the two bands. A large positive gap means real-leaderboard R² will likely sit below the Day-49 number. This does **not** block submission — it calibrates expectations.

---

## Task 6: Submission generation (`submit.py`)

**Files:** Create `submit.py`.

Trains the final GBM on **Day 48 only by default** (`TRAIN_ON_DAY49=False`; flip to `True` to also add the morning-only Day-49 rows), predicts test, blends with the lookup variant selected by `validate.py`, writes CSVs. Uses `BEST_ITER` / `W_LOOKUP` (and `USE_NEIGHBOR_LOOKUP_FOR_BLEND`) from `validate.py`.

- [ ] **Step 1: Write `submit.py`**

```python
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
BEST_ITER = 1500        # replace with printed best_iteration
W_LOOKUP = 0.6          # replace with printed w_lookup
USE_LOG = True
USE_NEIGHBOR_LOOKUP_FOR_BLEND = False  # set True only if validate.py prints lookup=+neighbor
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
```

- [ ] **Step 2: Run it**

Run:
```bash
python submit.py
```
Expected: four `wrote submissions/...csv` lines (`sub_lookup`, `sub_lookup_nb`, `sub_gbm`, `sub_blend`), each `mean` ≈ 0.08–0.11, `min ≥ 0`, `max ≤ 1.0`, no assertion errors.

- [ ] **Step 3: Validate format against the sample**

Run:
```bash
python -c "import pandas as pd; s=pd.read_csv('submissions/sub_blend.csv'); ss=pd.read_csv('dataset/sample_submission.csv'); te=pd.read_csv('dataset/test.csv'); print('cols', list(s.columns)==list(ss.columns)); print('rows', len(s)==41778); print('index match', (s['Index'].values==te['Index'].values).all()); print('any NaN', bool(s['demand'].isna().any()))"
```
Expected: `cols True`, `rows True`, `index match True`, `any NaN False`.

---

## Task 7: Notebook export (`export_notebook.py`)

The platform requires a `.ipynb` source file.

**Files:** Create `export_notebook.py`.

- [ ] **Step 1: Write `export_notebook.py`**

```python
"""Generate solution.ipynb that reproduces the submission end-to-end."""
import nbformat as nbf

intro = ("# Traffic Demand Prediction\n"
         "# Blend of Day-48 lookup ladder (with spatial neighbor fallback)\n"
         "# and a LightGBM structure model.")
imports = ("import numpy as np, pandas as pd, pygeohash as pgh, lightgbm as lgb\n"
           "from sklearn.neighbors import KDTree\n"
           "from sklearn.metrics import r2_score")

def strip_src(code):
    # drop intra-package imports so the notebook runs as flat cells;
    # handles multi-line `from src.x import (...)` by skipping continuation lines
    out, skipping, depth = [], False, 0
    for line in code.splitlines():
        if skipping:
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                skipping = False
            continue
        if line.strip().startswith("from src."):
            depth = line.count("(") - line.count(")")
            skipping = depth > 0
            continue
        out.append(line)
    return "\n".join(out)

cells = [
    intro,
    imports,
    strip_src(open("src/pipeline.py").read()),
    strip_src(open("src/spatial.py").read()),
    strip_src(open("src/model.py").read()),
    strip_src(open("submit.py").read()).replace(
        'if __name__ == "__main__":\n    main()', "main()"),
]

nb = nbf.v4.new_notebook()
nb.cells = [nbf.v4.new_code_cell(c) for c in cells]
with open("solution.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("wrote solution.ipynb")
```

- [ ] **Step 2: Generate**

Run:
```bash
python export_notebook.py
```
Expected: `wrote solution.ipynb`.

> Note: the notebook concatenates modules into flat cells (src imports stripped). `decode_latlon` uses `functools.lru_cache` which still works at module top level. If a name-resolution error appears when *running* the notebook, reorder cells so definitions precede use; the `.py` pipeline remains the source of truth for scoring.

---

## Task 8: Iteration loop (manual, submission-disciplined)

After Task 6 works:

- [ ] **Submission 1 — `sub_lookup.csv`.** Upload. Record leaderboard R². Compare to local lookup R² to learn the local↔leaderboard gap (informed by `validate_midday.py`).
- [ ] **Submission 2 — `sub_blend.csv`** with tuned `W_LOOKUP`/`BEST_ITER`. Should beat #1.
- [ ] **Submission 3 — improved GBM** (only if local R² rises): toggle `USE_LOG`; add features (`hour = minutes//60`, per-geohash demand std, finer `(g5, timestamp)` prior); sweep `num_leaves ∈ {31,63,127}`, `min_child_samples ∈ {20,40,80}`.
- [ ] **Submission 4 — re-blend** with the improved GBM (re-run `validate.py` for the new `w_lookup`).
- [ ] **Submission 5 (optional) — cross-day matched model.** The pipeline has **no `hist_gt` column** — add this leak-free helper (Day-48 exact value, used only for Day-49/test rows, never as a Day-48 self-feature):
  ```python
  def add_hist_gt(df, agg):
      gt = agg["gt"]; gm = agg["global_mean"]
      keys = list(zip(df["geohash"], df["timestamp"]))
      df = df.copy()
      df["hist_gt"] = pd.Series([gt.get(k, np.nan) for k in keys],
                                index=df.index).fillna(gm)
      return df
  ```
  Train a 2nd GBM on **Day-49 rows** with `FEATURES + ["hist_gt"]` (target = Day 49, feature = Day 48 → cross-day, leak-free). Apply it only to the 37,136 test rows that have an exact match; use the main blend for the rest. Validate on a Day-49 split first, and confirm with `validate_midday.py` before trusting it — Day-49 is morning-only.
- [ ] **Submission 6 — final ensemble:** average the best 2–3 distinct submissions if it lifts local R².

> **Independent fallback-order tuning:** the lookup is the strongest single component, so small fallback mistakes are expensive under R². When adding/reordering fallbacks (e.g. a `(g5, timestamp)` prior — likely better than the plain geohash mean for sparse misses), evaluate **only on the rows that miss an exact Day-48 match**, not on all rows (where exact matches mask the difference).

**Rule:** every submission must be justified by a local R² ≥ the best already submitted. Keep a running table: config → local R² → midday-gap → leaderboard R².

---

## Self-review checklist (run before handing off)

- [ ] Every test row gets a finite prediction in [0, 1] (Task 6 Step 3).
- [ ] Submission is exactly 41,778 × 2, columns `Index, demand`, matching index order.
- [ ] Historical features come only from Day 48; Day-48 training rows use LOO (`is_day48_train=True`); Day-49/test use plain means.
- [ ] `hist_nb` is computed (Task 2) **before** `FEATURES` is selected in validate/midday/submit; self is always excluded → leak-free.
- [ ] All 10 test-only geohashes get a finite `hist_nb` and lookup value (Task 2 Step 2).
- [ ] `FEATURES` / `CAT_COLS` imported from `pipeline.py` everywhere (no drift).
- [ ] `BEST_ITER` / `W_LOOKUP` / `USE_NEIGHBOR_LOOKUP_FOR_BLEND` in `submit.py` updated from `validate.py` output, not left at defaults; the blended lookup variant matches the one `validate.py` selected.
- [ ] Local blend R² ≥ both components; if not, investigate before submitting.
- [ ] `validate_midday.py` rebuilds aggregates/spatial index from `keep` only (no held-out leak) and holds out the true test band (2:15–13:45); gap reviewed.
- [ ] Lookup ladder is **plain by default**; the neighbor variant is a separate A/B candidate (`sub_lookup_nb`), not forced into the ladder.
- [ ] Final GBM trains on **Day 48 only** (`TRAIN_ON_DAY49=False`) unless leaderboard feedback justifies adding morning-only Day-49 rows.
- [ ] `add_hist_gt` helper exists if the optional Submission 5 cross-day model is attempted (no undefined `hist_gt`).
```
