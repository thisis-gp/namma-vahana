"""Experiment B: daytime blend candidates for LEADERBOARD A/B testing.
Local (morning) validation chose w_lookup=0, but the real test is daytime
(2:15-13:45) where the exact-match lookup may matter more -- not measurable
locally. Produce a few lookup/GBM blends to compare on the board.
"""
import numpy as np
import pandas as pd

gbm = pd.read_csv("submissions/sub_gbm.csv")
lk = pd.read_csv("submissions/sub_lookup.csv")
assert (gbm["Index"].to_numpy() == lk["Index"].to_numpy()).all(), "index mismatch"

g = gbm["demand"].to_numpy()
l = lk["demand"].to_numpy()
for w in (0.20, 0.35, 0.50):
    d = np.clip(w * l + (1 - w) * g, 0.0, 1.0)
    out = pd.DataFrame({"Index": gbm["Index"].to_numpy(), "demand": d})
    assert out.shape == (41778, 2)
    path = f"submissions/sub_blend_w{int(w * 100):02d}.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path}  mean={d.mean():.4f} min={d.min():.4f} max={d.max():.4f}")
