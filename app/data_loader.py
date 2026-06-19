import json
from pathlib import Path
import pandas as pd
import streamlit as st

ART = Path(__file__).resolve().parents[1] / "artifacts"


@st.cache_data
def cis():
    return pd.read_parquet(ART / "cis_scores.parquet")


@st.cache_data
def hotspots():
    return pd.read_parquet(ART / "hotspot_cells.parquet")


@st.cache_data
def hourly():
    return pd.read_parquet(ART / "hourly_heat.parquet")


@st.cache_data
def forecast():
    return pd.read_parquet(ART / "forecast.parquet")


@st.cache_data
def patrol():
    return pd.read_parquet(ART / "patrol_plan.parquet")


@st.cache_data
def kpis():
    return json.load(open(ART / "kpis.json"))
