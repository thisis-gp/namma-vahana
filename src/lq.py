"""Location Quotient — exposure correction for the logging-time bias.

Raw violation timestamps are dominated by the citywide patrol/recording schedule.
LQ compares each hotspot's hourly profile to the citywide profile, so a hotspot's
*relative* peak window reflects its genuine local pattern, not the global bias.
LQ[c,h] = (cell's share of hour h) / (citywide share of hour h).
100% in-dataset. Peak windows are constrained to actionable hours (6am-11pm IST).
"""
import numpy as np
import pandas as pd
from src.config import INTERIM, ARTIFACTS, ACTIONABLE_HOURS


def _fmt(h: int) -> str:
    ap = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{ap}"


def _peak_label(lq_by_hour: np.ndarray, share_actionable: float) -> str:
    lo, hi = ACTIONABLE_HOURS
    if share_actionable < 0.20:
        return "overnight (late night)"
    best_h, best_v = lo, -1.0
    for h in range(lo, hi - 1):  # 3-hour windows
        v = lq_by_hour[h] + lq_by_hour[h + 1] + lq_by_hour[h + 2]
        if v > best_v:
            best_v, best_h = v, h
    return f"{_fmt(best_h)}–{_fmt(best_h + 3)}"


def run() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    tot = len(df)
    city_h = df.groupby("hour")["id"].count().reindex(range(24), fill_value=0)
    city_share = np.array(city_h / tot, dtype=float)
    city_share[city_share == 0] = 1e-9
    rows = []
    lo, hi = ACTIONABLE_HOURS
    for h3id, g in df.groupby("h3"):
        c_h = g.groupby("hour")["id"].count().reindex(range(24), fill_value=0).to_numpy()
        n = c_h.sum()
        q = c_h / n
        lq = q / city_share
        share_actionable = c_h[lo:hi].sum() / n if n else 0.0
        peak = _peak_label(lq, share_actionable)
        rows.append([h3id, peak, float(lq[lo:hi].max() if n else 0.0)])
    out = pd.DataFrame(rows, columns=["h3", "peak_hours", "peak_lq"])
    out.to_parquet(ARTIFACTS / "lq_table.parquet")
    print(f"Location Quotient computed for {len(out):,} cells. "
          f"Sample peaks: {out['peak_hours'].value_counts().head(4).to_dict()}")
    return out


if __name__ == "__main__":
    run()
