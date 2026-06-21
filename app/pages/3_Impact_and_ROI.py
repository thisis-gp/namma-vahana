import sys as _sys, pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break
import pandas as pd
import plotly.express as px
import streamlit as st
from app import data_loader as dl

st.set_page_config(page_title="Impact & ROI", layout="wide", page_icon="📈")
st.title("📈 Impact & ROI")

k = dl.kpis()
cis = dl.cis().sort_values("cis", ascending=False).reset_index(drop=True)
cis["cum_share"] = cis["cis"].cumsum() / cis["cis"].sum()
cis["rank_pct"] = (cis.index + 1) / len(cis)

st.metric("Top-20 hotspots capture", f"{k['top20_impact_share'] * 100:.0f}% of total impact",
          help="Targeting a handful of cells covers most congestion impact.")

fig = px.line(cis, x="rank_pct", y="cum_share",
              title="Pareto: cumulative congestion impact vs share of hotspots patrolled",
              labels={"rank_pct": "Share of hotspots (ranked)", "cum_share": "Cumulative impact"})
fig.add_hline(y=0.8, line_dash="dot")
st.plotly_chart(fig, width="stretch")

st.subheader("Outcome — backtested enforcement uplift (held-out days)")
if k.get("uplift_pp") is not None:
    c1, c2, c3 = st.columns(3)
    c1.metric(f"ParkPulse coverage (K={k['uplift_k']})", f"{k['parkpulse_coverage'] * 100:.0f}%")
    c2.metric("Reactive (chase-yesterday)", f"{k['reactive_coverage'] * 100:.0f}%")
    c3.metric("Uplift", f"+{k['uplift_pp']:.0f} pp",
              help="Extra share of next-day impact-weighted violations intercepted with the "
                   "same patrol budget, measured on held-out test days.")
    comp = pd.DataFrame({
        "Strategy": ["Reactive (chase yesterday)", "ParkPulse (forecast + impact)"],
        "High-impact coverage": [k["reactive_coverage"], k["parkpulse_coverage"]],
    })
    st.plotly_chart(px.bar(comp, x="Strategy", y="High-impact coverage", text_auto=".0%",
                           title=f"Share of next-day high-impact violations intercepted "
                                 f"(same {k['uplift_k']} patrols/shift)"),
                    width="stretch")
    st.caption("Backtest: on each held-out day-shift, both strategies pick the same number of "
               "cells; we measure the share of that period's *actual* impact-weighted violations "
               "(count × impact score) that fell inside the chosen cells. Reactive = patrol "
               "yesterday's busiest cells (the status quo named in the problem statement).")

st.caption("The **Congestion Impact Score is a proxy** built entirely from the provided "
           "dataset (volume, severity, vehicle footprint, road criticality from the "
           "`location` text, peak overlap) — not a direct speed/flow measurement, and no "
           "external data.")
if k.get("precision_at_20") is not None:
    lift = k["precision_at_20"] - (k.get("naive_precision_at_20") or 0)
    st.success(f"Next-shift hotspot forecast — **LightGBM Precision@20 = "
               f"{k['precision_at_20']:.2f}** vs seasonal-naive "
               f"{k.get('naive_precision_at_20', 0):.2f} (+{lift:.2f} lift). "
               "Of the top-20 cells flagged for the next shift, this share were truly in "
               "the actual top-20 on held-out test days.")
elif k.get("naive_precision_at_20") is not None:
    st.info(f"Next-shift forecast — seasonal-naive baseline Precision@20 = "
            f"{k['naive_precision_at_20']:.2f}.")
