import sys as _sys, pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break
import streamlit as st
from app import data_loader as dl
from app.components import map_layer

st.set_page_config(page_title="Deployment Plan", layout="wide", page_icon="🚓")
st.title("🚓 Patrol Deployment Plan")
st.caption("Forecast-driven, impact-weighted roster — exportable for field teams.")

plan = dl.patrol()
shift = st.selectbox("Shift (IST)", sorted(plan["shift"].unique()))
view = plan[plan["shift"] == shift].sort_values("rank")

st.dataframe(
    view[["rank", "assigned_unit", "junction_name", "police_station",
          "expected_violations", "dominant_vehicle", "dominant_violation", "cis"]],
    width="stretch", hide_index=True,
    column_config={"cis": st.column_config.NumberColumn("Impact (proxy)", format="%.3f")})

st.download_button("⬇️ Download full enforcement plan (CSV)",
                   plan.to_csv(index=False).encode("utf-8"),
                   file_name="parkpulse_patrol_plan.csv", mime="text/csv")

st.subheader(f"Assigned beats — {shift}")
st.pydeck_chart(map_layer.deck(view.assign(cis_hour=view["cis"]), "cis_hour", zoom=12),
                width="stretch")
