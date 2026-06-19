import streamlit as st


def render(k):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Violations analyzed", f"{k['total_violations']:,}")
    c2.metric("Top-20 hotspots = impact share", f"{k['top20_impact_share'] * 100:.0f}%")
    c3.metric("Evening-peak enforcement", f"{k['evening_enforcement_share'] * 100:.1f}%",
              help="Share of violations logged in the 17:00-22:00 shift — the un-enforced peak")
    c4.metric("Chronic repeat offenders", f"{k['repeat_offenders']:,}")
