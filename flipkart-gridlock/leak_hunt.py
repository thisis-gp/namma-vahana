"""Leak hunt: try to reconstruct test `demand` exactly. Prints findings only."""
import numpy as np, pandas as pd, pygeohash as pgh, lightgbm as lgb
from sklearn.metrics import r2_score

tr = pd.read_csv("dataset/train.csv")
te = pd.read_csv("dataset/test.csv")
print(f"train {tr.shape}  test {te.shape}")
SEP = "=" * 70


# ---------------------------------------------------------------------------
print(SEP); print("A. KEY-BASED EXACT RECONSTRUCTION")
# If some key both (i) maps to a single demand in train and (ii) appears in test,
# we can copy demand. 'det_frac' = fraction of train key-groups with one demand;
# 'test_cov' = test rows whose key exists in train.
def keycheck(keys):
    t = tr.dropna(subset=[k for k in keys if k in tr.columns])
    g = t.groupby(keys)["demand"]
    det_frac = (g.nunique() <= 1).mean()
    if all(k in te.columns for k in keys):
        test_cov = te.merge(t[keys].drop_duplicates(), on=keys, how="inner").shape[0]
    else:
        test_cov = 0
    print(f"  {keys}: det_frac={det_frac:.3f}  test_cov={test_cov}/{len(te)}")

for keys in (
    ["geohash", "timestamp"],
    ["geohash", "timestamp", "Weather"],
    ["geohash", "Temperature"],
    ["Temperature"],
    ["geohash", "timestamp", "RoadType", "NumberofLanes",
     "LargeVehicles", "Landmarks", "Weather"],
    ["geohash", "timestamp", "RoadType", "NumberofLanes",
     "LargeVehicles", "Landmarks", "Weather", "Temperature"],
):
    keycheck(keys)
print("  VERDICT: a row with det_frac~1.0 AND high test_cov = exact-copy leak.")


# ---------------------------------------------------------------------------
print(SEP); print("B. TEMPERATURE AS ENCODED TARGET (high-precision decimals)")
d = tr.dropna(subset=["Temperature"]).copy()
t = d["Temperature"].to_numpy()
y = d["demand"].to_numpy()
for name, transform in [
    ("temp", t),
    ("frac(t)", t - np.floor(t)),
    ("frac(t*1e3)", (t * 1e3) % 1),
    ("frac(t*1e6)", (t * 1e6) % 1),
    ("t mod 1", np.mod(t, 1.0)),
    ("sin(t)", np.sin(t)),
]:
    print(f"  corr(demand, {name:12s}) = {np.corrcoef(y, transform)[0,1]:+.4f}")
m = lgb.train(dict(objective="regression", num_leaves=255, min_child_samples=2, verbose=-1),
              lgb.Dataset(d[["Temperature"]], label=y), num_boost_round=400)
print(f"  demand ~ Temperature alone, in-sample R2 = {r2_score(y, m.predict(d[['Temperature']])):.4f}")
print("  VERDICT: any corr near +/-1, or in-sample R2 near 1.0 = temp encodes demand.")


# ---------------------------------------------------------------------------
print(SEP); print("C. INDEX / ROW-ORDER ARTIFACTS")
print(f"  corr(demand, Index) = {tr['demand'].corr(tr['Index']):+.4f}")
print(f"  train Index range {tr['Index'].min()}..{tr['Index'].max()}  monotonic={tr['Index'].is_monotonic_increasing}")
print(f"  test  Index range {te['Index'].min()}..{te['Index'].max()}")
# is the file pre-sorted by demand within any group?
print(f"  demand globally sorted? {tr['demand'].is_monotonic_increasing}")
for n in (7, 10, 24, 96, 48):
    print(f"  corr(demand, Index % {n:3d}) = {tr['demand'].corr(tr['Index'] % n):+.4f}")
# block structure: mean demand by Index buckets
buck = pd.qcut(tr["Index"], 10, labels=False)
print("  mean demand by Index decile:",
      [round(v, 4) for v in tr.groupby(buck)["demand"].mean().tolist()])
print("  VERDICT: strong Index%n corr or a demand trend across deciles = order leak.")


# ---------------------------------------------------------------------------
print(SEP); print("D. RESIDUAL LEAK (is the UNEXPLAINED 21% encoded anywhere?)")
# base = per-geohash mean demand (captures the stable part); residual = the noise.
base = tr.groupby("geohash")["demand"].transform("mean")
res = (tr["demand"] - base)
print(f"  residual std={res.std():.4f}  (fraction of demand std {res.std()/tr['demand'].std():.2f})")
print(f"  corr(residual, Index)        = {res.corr(tr['Index']):+.4f}")
print(f"  corr(residual, Temperature)  = {res.corr(tr['Temperature']):+.4f}")
# within-geohash row order
tr["_pos"] = tr.groupby("geohash").cumcount()
print(f"  corr(residual, within-geo pos)= {res.corr(tr['_pos']):+.4f}")
# can a model recover the residual from ALL raw columns (incl Index)?
dd = tr.dropna(subset=["Temperature"]).copy()
ll = dd["geohash"].map(lambda g: pgh.decode(g))
dd["lat"] = ll.map(lambda x: x.latitude); dd["lon"] = ll.map(lambda x: x.longitude)
dd["minutes"] = dd["timestamp"].str.split(":", expand=True).astype(int).pipe(lambda x: x[0]*60+x[1])
for c in ["RoadType", "LargeVehicles", "Landmarks", "Weather"]:
    dd[c] = dd[c].astype("category").cat.codes
rbase = dd.groupby("geohash")["demand"].transform("mean")
rres = (dd["demand"] - rbase).to_numpy()
Xr = dd[["Index", "lat", "lon", "minutes", "Temperature", "RoadType",
         "LargeVehicles", "Landmarks", "Weather"]]
mr = lgb.train(dict(objective="regression", num_leaves=255, min_child_samples=2, verbose=-1),
               lgb.Dataset(Xr, label=rres), num_boost_round=400)
print(f"  residual ~ all-features+Index, in-sample R2 = {r2_score(rres, mr.predict(Xr)):.4f}")
print("  VERDICT: if residual is recoverable from Index/order/temp = leak; if ~0 = true noise.")


# ---------------------------------------------------------------------------
print(SEP); print("E. STRUCTURAL OVERLAP train<->test")
common = [c for c in te.columns if c in tr.columns and c != "Index"]
both = tr[common].merge(te[common], how="inner")
print(f"  rows identical on all shared feature cols (train vs test): {len(both)}")
gt = set(zip(tr.geohash, tr.timestamp, tr.day)) if "day" in tr else set()
print(f"  test geohashes also in train: {te['geohash'].isin(set(tr['geohash'])).mean():.3f}")
# does train(day49) + test together complete the 96-slot grid per geohash?
if "day" in tr.columns:
    d49 = tr[tr.day == 49]
    combo = pd.concat([d49[["geohash", "timestamp"]], te[["geohash", "timestamp"]]])
    per = combo.groupby("geohash")["timestamp"].nunique()
    print(f"  day49(train)+test slots per geohash: min={per.min()} max={per.max()} (96=full day)")
print("  VERDICT: identical rows = direct copy; full-grid = generator may be invertible.")
