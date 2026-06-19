"""Create conservative blends around the current leaderboard anchor.

Use when a standalone candidate underperforms the anchor but has slightly
different errors. These files are cheap A/B tests; they do not retrain models.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ANCHOR = "submissions/sub_gbm.csv"
CANDIDATES = [
    "submissions/sub_geog5_rtnorm_260.csv",
    "submissions/sub_geog5_rtnorm_300.csv",
    "submissions/sub_research_gbm_interactions.csv",
    "submissions/sub_research_gbm_ix_ratio.csv",
    "submissions/sub_research.csv",
    "submissions/sub_gbm_d49.csv",
]
WEIGHTS = [0.03, 0.05, 0.08, 0.10, 0.15]


def main() -> None:
    anchor = pd.read_csv(ANCHOR)
    a = anchor["demand"].to_numpy(dtype=float)

    for path in CANDIDATES:
        p = Path(path)
        if not p.exists():
            continue
        cand = pd.read_csv(p)
        assert (cand["Index"].to_numpy() == anchor["Index"].to_numpy()).all()
        c = cand["demand"].to_numpy(dtype=float)
        stem = p.stem.replace("sub_", "")

        for w in WEIGHTS:
            pred = np.clip((1.0 - w) * a + w * c, 0.0, 1.0)
            out = pd.DataFrame({"Index": anchor["Index"].to_numpy(), "demand": pred})
            out_path = f"submissions/sub_micro_{stem}_w{int(w * 100):02d}.csv"
            out.to_csv(out_path, index=False)
            print(
                f"wrote {out_path} mean={pred.mean():.5f} "
                f"delta_mae={np.mean(np.abs(pred - a)):.5f}"
            )


if __name__ == "__main__":
    main()
