import sys as _sys, pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break
import plotly.graph_objects as go
import streamlit as st
from app import data_loader as dl

st.set_page_config(page_title="What-If Simulator", layout="wide", page_icon="🎛️")
st.title("🎛️ What-If: how many patrols do you need?")
st.caption("Drag the patrol budget and see how much next-day congestion impact ParkPulse "
           "intercepts vs reactive (chase-yesterday) patrol — measured on held-out days.")

bt = dl.backtest()
kmax = int(bt["k"].max())
k = st.slider("Patrol units per shift", 1, kmax, 6)

row = bt[bt["k"] == k].iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("ParkPulse coverage", f"{row.parkpulse_coverage * 100:.0f}%")
c2.metric("Reactive coverage", f"{row.reactive_coverage * 100:.0f}%")
c3.metric("Uplift", f"+{row.uplift_pp:.0f} pp")

fig = go.Figure()
fig.add_scatter(x=bt["k"], y=bt["parkpulse_coverage"] * 100, name="ParkPulse (forecast + impact)",
                mode="lines+markers", line=dict(color="#FF5A1F", width=3))
fig.add_scatter(x=bt["k"], y=bt["reactive_coverage"] * 100, name="Reactive (chase yesterday)",
                mode="lines+markers", line=dict(color="#7f8c8d", width=2, dash="dot"))
fig.add_vline(x=k, line_dash="dash", line_color="#FFFFFF", opacity=0.4)
fig.update_layout(title="Impact coverage vs patrol budget",
                  xaxis_title="Patrol units per shift (K)",
                  yaxis_title="% of next-day high-impact violations intercepted",
                  legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, width="stretch")

st.info(f"With **{k} patrols per shift**, ParkPulse intercepts "
        f"**{row.parkpulse_coverage * 100:.0f}%** of next-day high-impact violations — "
        f"**+{row.uplift_pp:.0f} percentage points** more than reactive patrol, at zero extra cost. "
        "The curve also shows the *marginal* value of each additional patrol, so BTP can size "
        "the team to a target coverage.")
st.caption("Outcome is backtested on held-out test days (forecast never sees them); "
           "100% from the provided dataset — no external data.")
