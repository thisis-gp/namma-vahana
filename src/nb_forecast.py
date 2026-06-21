"""Station-level Negative Binomial forecast (overdispersion-correct, explainable).

Violation counts are heavily overdispersed (variance >> mean), so Poisson would
understate uncertainty. NB2 is the textbook model; output is a per-station next-week
baseline with a 95% interval. 100% in-dataset.
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from src.config import INTERIM, ARTIFACTS
from src import schema  # noqa: F401


def run() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    d = pd.to_datetime(df["date"])
    week = ((d - d.min()).dt.days // 7).astype(int)
    panel = (df.assign(week=week).groupby(["police_station", "week"])["id"]
             .count().rename("y").reset_index())
    overdisp = float(panel["y"].var() / panel["y"].mean())

    pseudo_r2, alpha = None, None
    try:
        import statsmodels.formula.api as smf
        m = smf.negativebinomial("y ~ C(police_station)", data=panel).fit(disp=0, maxiter=200)
        pseudo_r2 = float(getattr(m, "prsquared", np.nan))
        alpha = float(m.params.get("alpha", np.nan))
        pred = panel.drop_duplicates("police_station")[["police_station"]].copy()
        pred["mu"] = m.predict(pred)
    except Exception as e:  # graceful fallback to per-station mean
        print(f"NB fit fell back to means ({e})")
        pred = panel.groupby("police_station")["y"].mean().rename("mu").reset_index()
        alpha = max(overdisp - 1, 0.1) / max(pred["mu"].mean(), 1)

    rows = []
    a = alpha if alpha and alpha > 0 else 0.5
    for _, r in pred.iterrows():
        mu = max(float(r["mu"]), 0.01)
        n = 1.0 / a
        p = n / (n + mu)
        lo, hi = stats.nbinom.ppf([0.025, 0.975], n, p)
        rows.append([r["police_station"], int(round(mu)), int(lo), int(hi)])
    out = pd.DataFrame(rows, columns=["police_station", "forecast_next_week",
                                      "lower_95", "upper_95"])
    out.to_parquet(ARTIFACTS / "nb_forecast.parquet")
    json.dump({"overdispersion": round(overdisp, 1),
               "pseudo_r2": round(pseudo_r2, 3) if pseudo_r2 and not np.isnan(pseudo_r2) else None},
              open(ARTIFACTS / "_nb_meta.json", "w"))
    print(f"NB forecast: {len(out)} stations. overdispersion var/mean={overdisp:.1f}, "
          f"pseudo-R2={pseudo_r2}")
    return out


if __name__ == "__main__":
    run()
