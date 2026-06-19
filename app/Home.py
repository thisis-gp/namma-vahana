import sys as _sys, pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break
import streamlit as st
from app import data_loader as dl
from app.components import map_layer, kpi_cards

st.set_page_config(page_title="ParkPulse — BTP Parking Intelligence",
                   layout="wide", page_icon="🅿️")
st.title("🅿️ ParkPulse")
st.caption("Bengaluru Traffic Police · AI parking-congestion intelligence · "
           "Data: Nov 2023 – Apr 2024 · 298,443 records · 54 stations")

k = dl.kpis()
kpi_cards.render(k)

heat = dl.hourly()
col_map, col_ctrl = st.columns([4, 1])
with col_ctrl:
    hour = st.slider("Hour of day (IST)", 0, 23, 9)
    weekend = st.toggle("Weekend", value=False)
view = heat[(heat["hour"] == hour) & (heat["is_weekend"] == weekend)]
view = view.nlargest(800, "cis_hour")
with col_map:
    st.pydeck_chart(map_layer.deck(view, "cis_hour"), width="stretch")

st.markdown("**Drag the hour slider from 9 AM to 6 PM** — watch hotspots surge at peak. "
            "Congestion isn't static; our plan is time-aware.")
st.caption("Hotspot height/colour = **Congestion Impact Score (proxy)** — derived from "
           "violation volume, severity, vehicle footprint, road criticality and peak-time "
           "overlap. It is an enforcement-data proxy, not a direct speed/flow measurement.")
