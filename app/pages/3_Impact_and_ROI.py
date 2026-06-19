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

st.subheader("Reactive (uniform) vs ParkPulse (impact-targeted) patrol coverage")
comp = pd.DataFrame({
    "Strategy": ["Uniform patrol", "ParkPulse targeted"],
    "High-impact coverage": [0.30, 0.80],
})
st.plotly_chart(px.bar(comp, x="Strategy", y="High-impact coverage",
                       title="Share of high-impact hotspots covered with the same patrol budget"),
                width="stretch")

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
