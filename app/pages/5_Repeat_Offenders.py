import sys as _sys, pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break
import plotly.express as px
import streamlit as st
from app import data_loader as dl

st.set_page_config(page_title="Repeat Offenders", layout="wide", page_icon="🔁")
st.title("🔁 Chronic Repeat-Offender Watchlist")
st.caption("Vehicles that park illegally again and again — a targeted, vehicle-level "
           "enforcement lever (escalating penalty) beyond zone patrols.")

k = dl.kpis()
wl = dl.watchlist()

c1, c2, c3 = st.columns(3)
c1.metric("Chronic offenders (≥10 violations)", f"{k['repeat_offenders']:,}")
c2.metric("Their share of all violations", f"{k.get('repeat_offender_share', 0) * 100:.1f}%")
c3.metric("Worst single vehicle", f"{int(wl['violations'].max())} violations")

st.subheader("Top 20 repeat offenders")
top = wl.head(20)
st.plotly_chart(
    px.bar(top, x="vehicle_number", y="violations", color="vehicle_type",
           title="Violations per chronic vehicle (anonymized IDs)"),
    width="stretch")

st.dataframe(
    wl[["vehicle_number", "vehicle_type", "violations", "distinct_cells",
        "top_junction", "top_location", "first_seen", "last_seen"]],
    width="stretch", hide_index=True)

st.download_button("⬇️ Download watchlist (CSV)",
                   wl.to_csv(index=False).encode("utf-8"),
                   file_name="parkpulse_repeat_offenders.csv", mime="text/csv")
st.caption("Derived from the dataset's anonymized but stable `vehicle_number` — no external data.")
