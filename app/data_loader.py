import json
from pathlib import Path
import pandas as pd
import streamlit as st

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _pq(name):
    return pd.read_parquet(ART / name)


@st.cache_data(show_spinner=False)
def hotspots():
    return _pq("hotspots.parquet")


@st.cache_data(show_spinner=False)
def stations():
    return _pq("stations.parquet")


@st.cache_data(show_spinner=False)
def citizen():
    return _pq("citizen.parquet")


@st.cache_data(show_spinner=False)
def hourly():
    return _pq("hourly_heat.parquet")


@st.cache_data(show_spinner=False)
def forecast():
    return _pq("forecast.parquet")


@st.cache_data(show_spinner=False)
def nb_forecast():
    return _pq("nb_forecast.parquet")


@st.cache_data(show_spinner=False)
def patrol():
    return _pq("patrol_plan.parquet")


@st.cache_data(show_spinner=False)
def backtest():
    return _pq("backtest.parquet")


@st.cache_data(show_spinner=False)
def watchlist():
    return _pq("watchlist.parquet")


@st.cache_data(show_spinner=False)
def kpis():
    return json.load(open(ART / "kpis.json"))


@st.cache_data(show_spinner=False)
def nb_meta():
    p = ART / "_nb_meta.json"
    return json.load(open(p)) if p.exists() else {}


def has_data():
    return (ART / "hotspots.parquet").exists()
