import sys as _sys, pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break
import streamlit as st
import plotly.express as px
from app import data_loader as dl

st.set_page_config(page_title="Hotspot Explorer", layout="wide", page_icon="🔥")
st.title("🔥 Hotspot Explorer")

cis = dl.cis()
hs = dl.hotspots()
tbl = cis.merge(hs[["h3", "junction_name", "police_station", "violation_count",
                    "dominant_vehicle", "dominant_violation"]], on="h3", how="left")
tbl = tbl.sort_values("rank")

stations = ["All"] + sorted(tbl["police_station"].dropna().unique().tolist())
sel = st.selectbox("Police station", stations)
view = tbl if sel == "All" else tbl[tbl["police_station"] == sel]

st.dataframe(
    view[["rank", "junction_name", "police_station", "cis", "violation_count",
          "dominant_vehicle", "dominant_violation"]].head(50),
    width="stretch", hide_index=True,
    column_config={"cis": st.column_config.NumberColumn("Impact (proxy)", format="%.3f")})

st.subheader("Impact factor breakdown — top 15 hotspots")
top = view.head(15)
fig = px.bar(top, x="rank", y=["f_volume", "f_severity", "f_road", "f_peak"],
             title="Why these cells score high (stacked Congestion Impact Score factors)")
st.plotly_chart(fig, width="stretch")
st.info("**Congestion Impact Score (proxy)** = 0.25·Volume + 0.30·Severity + "
        "0.30·RoadCriticality + 0.15·PeakOverlap. Severity folds in vehicle footprint; "
        "road criticality is parsed from the dataset's own `location` text. This is a "
        "**proxy from the provided enforcement data — not a direct speed/flow measurement, "
        "and no external data.** Weights are policy-tunable in config.yaml.")
