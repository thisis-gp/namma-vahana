"""Backtested enforcement uplift — the outcome metric.

On held-out test days, compare two strategies with the SAME patrol budget K:
  - ParkPulse: patrol the K cells with highest LightGBM-forecast intensity.
  - Reactive (status quo): patrol the K cells that were busiest *yesterday* (lag1).
For each (day, shift) we measure the share of that period's actual impact-weighted
violations (y * CIS) that fall inside the chosen K cells. Averaged over all test
periods, for K = 1..30. 100% in-dataset; the comparison baseline is the reactive
"chase yesterday" behaviour named in the problem statement.
"""
import numpy as np
import pandas as pd
from src.config import ARTIFACTS, OPT
from src import schema

PANEL = ARTIFACTS / "_backtest_panel.parquet"
KMAX = 30


def run() -> pd.DataFrame:
    panel = pd.read_parquet(PANEL)
    panel["impact"] = panel["y"] * panel["cis"].fillna(0)
    pp_cov = np.zeros(KMAX)
    re_cov = np.zeros(KMAX)
    valid = 0
    for _, g in panel.groupby(["date", "shift"], sort=False):
        total = g["impact"].sum()
        if total <= 0:
            continue
        valid += 1
        pp_cum = np.cumsum(g.sort_values("pred", ascending=False)["impact"].to_numpy()) / total
        re_cum = np.cumsum(g.sort_values("lag1", ascending=False)["impact"].to_numpy()) / total
        for k in range(KMAX):
            pp_cov[k] += pp_cum[min(k, len(pp_cum) - 1)]
            re_cov[k] += re_cum[min(k, len(re_cum) - 1)]
    pp_cov /= valid
    re_cov /= valid
    out = pd.DataFrame({
        "k": np.arange(1, KMAX + 1),
        "parkpulse_coverage": pp_cov,
        "reactive_coverage": re_cov,
        "uplift_pp": (pp_cov - re_cov) * 100,
    })[schema.BACKTEST]
    out.to_parquet(ARTIFACTS / "backtest.parquet")
    k = OPT["n_units_per_shift"]
    row = out[out["k"] == k].iloc[0]
    print(f"Backtest over {valid} held-out day-shifts. At K={k} patrols/shift: "
          f"ParkPulse covers {row.parkpulse_coverage * 100:.0f}% of impact vs "
          f"reactive {row.reactive_coverage * 100:.0f}% (+{row.uplift_pp:.0f} pp).")
    return out


if __name__ == "__main__":
    run()
