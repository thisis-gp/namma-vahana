"""ParkPulse — Bengaluru parking-congestion intelligence (role-based app).

Police (station-scoped) + Citizen (public risk guide), reading only precomputed
artifacts. 100% from the provided dataset — no external data.
"""
import sys as _sys
import pathlib as _pl
for _c in _pl.Path(__file__).resolve().parents:
    if (_c / "src").exists() and (_c / "artifacts").exists():
        _sys.path.insert(0, str(_c)) if str(_c) not in _sys.path else None
        break

from datetime import date, timedelta
import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go

from app import data_loader as dl
from src import events_store as EV
from src import config as CFG

st.set_page_config(page_title="ParkPulse — Bengaluru Parking Intelligence",
                   page_icon="🅿️", layout="wide", initial_sidebar_state="collapsed")

if not dl.has_data():
    st.error("No cached data. Run `python -m src.run_pipeline` first, then reload.")
    st.stop()

K = dl.kpis()
HOT = dl.hotspots()
POLICE_ACCENT, CITIZEN_ACCENT = "#FF5A1F", "#0e7c66"

ss = st.session_state
ss.setdefault("role", None)
ss.setdefault("station", None)
ss.setdefault("citywide", False)
ss.setdefault("show_method", False)


def css(accent):
    st.markdown(f"""<style>
      .role-band {{background:linear-gradient(90deg,{accent},{accent}cc);color:#fff;
        padding:14px 22px;border-radius:10px;margin-bottom:12px;}}
      .role-band h2 {{margin:0;font-size:1.25rem;}} .role-band p {{margin:2px 0 0;opacity:.85;font-size:.85rem;}}
      .nlsum {{background:#1a1d27;border-left:4px solid {accent};padding:10px 14px;
        border-radius:6px;font-size:1.02rem;line-height:1.5;margin:6px 0 10px;}}
      div.stButton > button {{border-radius:10px;font-weight:600;}}
      .hero {{text-align:center;padding:3.2vh 0 1vh;}}
      .hero h1 {{font-size:3.1rem;margin:0;letter-spacing:-1px;}}
      .hero .tag {{font-size:1.15rem;color:#cfd3dc;margin-top:6px;}}
      .pill {{display:inline-block;background:{accent}22;color:{accent};border:1px solid {accent}55;
        padding:4px 12px;border-radius:999px;font-size:.8rem;font-weight:600;margin-top:10px;}}
      .step {{background:#15171f;border:1px solid #262a36;border-radius:12px;padding:14px 16px;height:100%;}}
      .step b {{color:{accent};}}
      [data-testid="stMetric"] {{background:#15171f;border:1px solid #262a36;
        border-radius:12px;padding:10px 14px;}}
      [data-testid="stMetricValue"] {{font-size:1.7rem;}}
    </style>""", unsafe_allow_html=True)


def reset():
    ss.role = None; ss.station = None; ss.citywide = False; ss.show_method = False


def method_link():
    if st.button("Methodology / About", key=f"m_{ss.role}_{ss.station}"):
        ss.show_method = True; st.rerun()


# ----------------------------------------------------------------- map + card
def priority_map(df, accent, center=None):
    f = df.head(150).copy()
    f["elev"] = f["priority_score"] / f["priority_score"].max() * 1000
    f["color"] = f["priority_pct"].apply(
        lambda p: [255, int(170 * (1 - min(p, 100) / 100)) + 30, 40, 200])
    clat, clon, zoom = center if center else (12.972, 77.594, 11)
    layer = pdk.Layer("ColumnLayer", data=f, id="hs",
                      get_position=["lon", "lat"], get_elevation="elev",
                      radius=70, get_fill_color="color", pickable=True, auto_highlight=True)
    tip = {"html": "<b>#{rank} {junction_name}</b><br/>Violations: {violation_count}<br/>"
                   "Priority: {priority_pct}<br/>Road: {road_class}<br/>Action: {intervention_type}",
           "style": {"backgroundColor": accent, "color": "white"}}
    deck = pdk.Deck(layers=[layer], map_style="dark",
                    initial_view_state=pdk.ViewState(latitude=clat, longitude=clon,
                                                     zoom=zoom, pitch=50, bearing=10),
                    tooltip=tip)
    return st.pydeck_chart(deck, width="stretch", height=440,
                           on_select="rerun", selection_mode="single-object")


def hotspot_card(r):
    st.markdown(f"<div class='nlsum'>📝 {r['nl_summary']}</div>", unsafe_allow_html=True)
    c = st.columns(4)
    c[0].metric("Priority", f"{r['priority_pct']:.0f}/100",
                help="Congestion Impact Score (proxy) + under-enforcement boost.")
    c[1].metric("Violations", f"{int(r['violation_count']):,}")
    c[2].metric("Severity", f"{int(r['severity_10'])}/10",
                help="From violation type + road class (in-dataset).")
    c[3].metric("Units rec.", int(r["units_recommended"]))
    c = st.columns(3)
    c[0].markdown(f"**Road (in-data):** {r['road_class']}")
    c[1].markdown(f"**Action:** {r['intervention_type']}  \n_repeat share {r['repeat_offender_ratio']:.0%}_")
    c[2].markdown(f"**Peak risk:** {r['peak_hours']}")
    flags = []
    if r["blocks_bus"]: flags.append("🚌 near bus stop")
    if r["near_school"]: flags.append("🏫 near school")
    if r["near_hospital"]: flags.append("🏥 near hospital")
    if flags: st.caption("Context (from address text): " + " · ".join(flags))
    if r["confidence_flag"] == "lower":
        st.warning(f"⚠️ Lower confidence: records here corrected at {r['correction_rate']:.0%} "
                   "(above dataset average) — treat the score as approximate.")


# ----------------------------------------------------------------- landing
def landing():
    css(POLICE_ACCENT)
    st.markdown("<div class='hero'><h1>🅿️ ParkPulse</h1>"
                "<div class='tag'>Tells Bengaluru Traffic Police <b>where & when</b> to patrol "
                "tomorrow to clear the most traffic-choking illegal parking — and proves it "
                "beats how they work today.</div>"
                "<div class='pill'>100% on the provided dataset · no external data</div></div>",
                unsafe_allow_html=True)

    h = st.columns(4)
    h[0].metric("Violations analyzed", f"{K['total_violations'] / 1000:.0f}K")
    h[1].metric("Enforcement uplift", f"+{K['uplift_pp']:.0f} pp",
                help="vs today's reactive patrol, same budget, on held-out days")
    h[2].metric("Forecast Precision@20", f"{K['precision_at_20']:.2f}",
                help=f"vs seasonal-naive {K['naive_precision_at_20']:.2f}")
    h[3].metric("Hotspots mapped", f"{K['n_hotspots']:,}")

    st.write("")
    s = st.columns(3)
    s[0].markdown("<div class='step'><b>1 · Detect & score</b><br/>Cluster 298K violations into "
                  "hotspots and rank each by a Congestion Impact Score (proxy).</div>",
                  unsafe_allow_html=True)
    s[1].markdown("<div class='step'><b>2 · Forecast tomorrow</b><br/>Predict the next shift's "
                  "worst hotspots so patrols are proactive, not reactive.</div>",
                  unsafe_allow_html=True)
    s[2].markdown("<div class='step'><b>3 · Deploy & prove</b><br/>Output a patrol roster — and "
                  "backtest shows it more than doubles impact covered.</div>",
                  unsafe_allow_html=True)

    st.write("")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        a, b = st.columns(2)
        with a.container(border=True):
            st.markdown("#### 👮 Police")
            st.caption("Station dashboards, forecast, deployment roster & proven uplift.")
            st.text_input("Officer ID", placeholder="e.g. BLR-2287 (demo)")
            if st.button("Sign in as Police", type="primary", width="stretch"):
                ss.role = "police"; st.rerun()
        with b.container(border=True):
            st.markdown("#### 👤 Citizen")
            st.caption("Where & when illegal-parking enforcement is concentrated. No login.")
            st.write(""); st.write("")
            if st.button("Enter as Citizen", width="stretch"):
                ss.role = "citizen"; st.rerun()
    st.markdown("<div style='text-align:center;margin-top:2vh;color:#888;font-size:.8rem'>"
                f"Prototype · {K['total_violations']:,} Bengaluru Police records · "
                f"{K['n_stations']} stations · Nov 2023–Apr 2024</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------- police
def station_picker():
    css(POLICE_ACCENT)
    st.markdown("<div class='role-band'><h2>👮 Select your station</h2>"
                "<p>Scope the dashboard to your jurisdiction.</p></div>", unsafe_allow_html=True)
    stations = sorted(HOT["dominant_station"].dropna().unique().tolist())
    a, b = st.columns([3, 1])
    sel = a.selectbox("Search your station", ["— choose —"] + stations)
    b.write(""); b.write("")
    if b.button("🏙️ City-wide", width="stretch"):
        ss.citywide = True; ss.station = None; st.rerun()
    if sel != "— choose —":
        ss.station = sel; ss.citywide = False; st.rerun()
    if st.button("← Log out"):
        reset(); st.rerun()


def police_dashboard():
    css(POLICE_ACCENT)
    scope = "City-wide (all Bengaluru)" if ss.citywide else ss.station
    hs = HOT if ss.citywide else HOT[HOT["dominant_station"] == ss.station]
    hs = hs.sort_values("priority_score", ascending=False).reset_index(drop=True)
    band = st.columns([4, 1, 1])
    band[0].markdown(f"<div class='role-band'><h2>👮 {scope}</h2>"
                     f"<p>{len(hs)} hotspots</p></div>", unsafe_allow_html=True)
    band[1].write(""); band[2].write("")
    if band[1].button("🔄 Switch station", width="stretch"):
        ss.station = None; ss.citywide = False; st.rerun()
    if band[2].button("Log out", width="stretch"):
        reset(); st.rerun()
    if hs.empty:
        st.info("No hotspots for this station."); method_link(); return

    st.success(f"📊 **Proven outcome:** with the same patrol budget, ParkPulse covers "
               f"**{K['parkpulse_coverage'] * 100:.0f}%** of next-day congestion impact vs "
               f"**{K['reactive_coverage'] * 100:.0f}%** for today's reactive patrol — "
               f"**+{K['uplift_pp']:.0f} percentage points** (backtested on held-out days). "
               f"Forecast Precision@20 = {K['precision_at_20']:.2f}.")

    tabs = st.tabs(["🗺️ Hotspots", "📈 Forecast & Events", "🚓 Deployment & Outcome",
                    "🔁 Repeat Offenders"])

    # ---- TAB 1: hotspots ----
    with tabs[0]:
        k = st.columns(4)
        k[0].metric("Hotspots", len(hs))
        k[1].metric("Violations", f"{int(hs['violation_count'].sum()):,}")
        k[2].metric("Units rec.", int(hs["units_recommended"].sum()))
        if not ss.citywide:
            srow = dl.stations()
            srow = srow[srow["police_station"] == ss.station]
            if len(srow):
                g = srow.iloc[0]
                flag = " ⚠️" if g["gap_confidence"] == "lower" else ""
                k[3].metric("Enforcement gap", f"{g['enforcement_gap']:.1f}/10{flag}",
                            help="Violations per device, normalised. ⚠️ = lower confidence.")
        else:
            k[3].metric("Top-20 = impact", f"{K['top20_impact_share'] * 100:.0f}%")

        st.subheader("Hotspot map — height & colour = priority")
        center = None if ss.citywide else (hs["lat"].mean(), hs["lon"].mean(), 13)
        ev = priority_map(hs, POLICE_ACCENT, center)
        clicked = None
        try:
            objs = ev.selection["objects"].get("hs", []) if ev and ev.selection else []
            if objs: clicked = int(objs[0]["rank"])
        except Exception:
            clicked = None

        st.subheader("Hotspot detail")
        ranks = hs["rank"].tolist()
        idx = ranks.index(clicked) if clicked in ranks else 0
        sel = st.selectbox("Click a column on the map, or choose:", ranks, index=idx,
                           format_func=lambda r: f"#{r} — "
                           f"{HOT[HOT['rank'] == r]['junction_name'].iloc[0] or 'spot'}")
        hotspot_card(HOT[HOT["rank"] == sel].iloc[0])

        st.subheader("Priority ranking")
        cols = ["rank", "junction_name", "dominant_station", "violation_count",
                "priority_pct", "severity_10", "intervention_type", "road_class", "peak_hours"]
        disp = hs[cols].rename(columns={"rank": "#", "junction_name": "Location",
                "dominant_station": "Station", "violation_count": "Violations",
                "priority_pct": "Priority", "severity_10": "Sev",
                "intervention_type": "Action", "road_class": "Road", "peak_hours": "Peak"})
        st.dataframe(disp, width="stretch", height=320, hide_index=True,
                     column_config={"Priority": st.column_config.ProgressColumn(
                         "Priority", min_value=0, max_value=100, format="%.0f")})
        st.download_button("⬇ Download priority list (CSV)", disp.to_csv(index=False).encode(),
                           file_name=f"parkpulse_priority_{ss.station or 'citywide'}.csv")

    # ---- TAB 2: forecast & events ----
    with tabs[1]:
        nb = dl.nb_forecast()
        st.subheader("Next-week forecast — Negative Binomial (95% interval)")
        st.caption("Counts are overdispersed, so NB (not Poisson). Expected volume, not vehicles.")
        if ss.citywide:
            top = nb.sort_values("forecast_next_week", ascending=False).head(12)
            fig = go.Figure(go.Bar(x=top["police_station"], y=top["forecast_next_week"],
                            error_y=dict(type="data", symmetric=False,
                                array=top["upper_95"] - top["forecast_next_week"],
                                arrayminus=top["forecast_next_week"] - top["lower_95"]),
                            marker_color=POLICE_ACCENT))
            fig.update_layout(height=380, margin=dict(t=10))
            st.plotly_chart(fig, width="stretch")
        else:
            row = nb[nb["police_station"] == ss.station]
            if len(row):
                r = row.iloc[0]
                base = int(r["forecast_next_week"])
                mult, drivers = EV.station_multiplier(ss.station)
                m = st.columns(2)
                m[0].metric(f"{ss.station} — baseline next week", f"{base:,}",
                            help="NB model, history only.")
                m[0].caption(f"95% range {int(r['lower_95']):,}–{int(r['upper_95']):,}")
                if mult > 1.0:
                    adj = int(round(base * mult))
                    m[1].metric("⚡ Event-adjusted", f"{adj:,}", delta=f"+{adj - base:,}")
                    m[1].caption("Baseline × declared-event surge factor (officer assumption).")
            event_panel(ss.station)

    # ---- TAB 3: deployment & outcome ----
    with tabs[2]:
        st.subheader("Outcome — backtested enforcement uplift (held-out days)")
        o = st.columns(3)
        o[0].metric(f"ParkPulse coverage (K={K['uplift_k']})", f"{K['parkpulse_coverage'] * 100:.0f}%")
        o[1].metric("Reactive (chase-yesterday)", f"{K['reactive_coverage'] * 100:.0f}%")
        o[2].metric("Uplift", f"+{K['uplift_pp']:.0f} pp",
                    help="Extra share of next-day impact-weighted violations intercepted, "
                         "same patrol budget, on held-out test days.")
        bt = dl.backtest()
        kk = st.slider("What-if: patrol units per shift", 1, int(bt["k"].max()), int(K["uplift_k"]))
        rr = bt[bt["k"] == kk].iloc[0]
        fig = go.Figure()
        fig.add_scatter(x=bt["k"], y=bt["parkpulse_coverage"] * 100, name="ParkPulse",
                        line=dict(color=POLICE_ACCENT, width=3))
        fig.add_scatter(x=bt["k"], y=bt["reactive_coverage"] * 100, name="Reactive",
                        line=dict(color="#7f8c8d", dash="dot"))
        fig.add_vline(x=kk, line_dash="dash", line_color="#fff", opacity=0.4)
        fig.update_layout(height=320, xaxis_title="Patrol units / shift",
                          yaxis_title="% next-day impact intercepted",
                          legend=dict(orientation="h", y=-0.25), margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")
        st.info(f"With **{kk} patrols/shift**, ParkPulse intercepts **{rr.parkpulse_coverage * 100:.0f}%** "
                f"vs reactive **{rr.reactive_coverage * 100:.0f}%** (**+{rr.uplift_pp:.0f} pp**).")

        st.subheader("Patrol deployment roster")
        plan = dl.patrol()
        sh = st.selectbox("Shift (IST)", sorted(plan["shift"].unique()))
        pv = plan[plan["shift"] == sh].sort_values("rank")
        st.dataframe(pv[["rank", "assigned_unit", "junction_name", "police_station",
                         "expected_violations", "dominant_vehicle", "dominant_violation"]],
                     width="stretch", hide_index=True)
        st.download_button("⬇ Download full roster (CSV)", plan.to_csv(index=False).encode(),
                           file_name="parkpulse_patrol_roster.csv")

    # ---- TAB 4: repeat offenders ----
    with tabs[3]:
        wl = dl.watchlist()
        c = st.columns(3)
        c[0].metric("Chronic offenders (≥10)", f"{K['repeat_offenders']:,}")
        c[1].metric("Their share of violations", f"{K.get('repeat_offender_share', 0) * 100:.1f}%")
        c[2].metric("Worst vehicle", f"{int(wl['violations'].max())} violations")
        st.plotly_chart(px.bar(wl.head(20), x="vehicle_number", y="violations",
                        color="vehicle_type", title="Top 20 repeat offenders (anonymized IDs)"),
                        width="stretch")
        st.dataframe(wl[["vehicle_number", "vehicle_type", "violations", "distinct_cells",
                         "top_junction", "first_seen", "last_seen"]],
                     width="stretch", hide_index=True)
        st.download_button("⬇ Download watchlist (CSV)", wl.to_csv(index=False).encode(),
                           file_name="parkpulse_repeat_offenders.csv")

    st.divider(); method_link()


def event_panel(station):
    existing = EV.list_events(station=station, upcoming_only=True)
    with st.expander(f"⚡ Upcoming events affecting {station}"
                     + (f" · {len(existing)} active" if existing else ""), expanded=bool(existing)):
        st.caption("Declare a known event to surge this station's forecast (officer assumption).")
        with st.form(f"ev_{station}", clear_on_submit=True):
            c = st.columns(2)
            name = c[0].text_input("Event name", placeholder="e.g. CM inauguration")
            etype = c[1].selectbox("Type", CFG.EVENT_TYPES)
            c2 = st.columns(2)
            ev_date = c2[0].date_input("Date", value=date.today() + timedelta(days=2),
                                       min_value=date.today())
            impact = c2[1].selectbox("Expected impact", list(CFG.EVENT_IMPACT.keys()), index=1)
            if st.form_submit_button("➕ Add event (updates forecast)", type="primary"):
                EV.add_event(name, etype, station, ev_date, impact, "")
                st.success("Added — forecast updated."); st.rerun()
        for e in existing:
            cc = st.columns([5, 1])
            cc[0].markdown(f"**{e['name']}** · {e['type']} · {e['date']} · ×{e['multiplier']}")
            if cc[1].button("Remove", key=f"del_{e['id']}"):
                EV.delete_event(e["id"]); st.rerun()


# ----------------------------------------------------------------- citizen
def citizen_view():
    css(CITIZEN_ACCENT)
    head = st.columns([4, 1])
    head[0].markdown(f"<div class='role-band' style='background:linear-gradient(90deg,"
                     f"{CITIZEN_ACCENT},{CITIZEN_ACCENT}cc)'><h2>👤 Parking Risk Guide</h2>"
                     f"<p>Know where & when illegal-parking enforcement is concentrated.</p></div>",
                     unsafe_allow_html=True)
    head[1].write("")
    if head[1].button("Exit", width="stretch"):
        reset(); st.rerun()
    cz = dl.citizen()
    areas = sorted(cz["dominant_station"].dropna().unique().tolist())
    pick = st.selectbox("Your area", ["All areas"] + areas)
    view = (cz if pick == "All areas" else cz[cz["dominant_station"] == pick]).sort_values(
        "fine_risk", ascending=False)
    cmap = {"VERY HIGH": [215, 48, 39, 200], "HIGH": [252, 141, 89, 200],
            "MODERATE": [254, 224, 139, 200], "LOWER": [145, 207, 96, 200]}
    v = view.copy(); v["color"] = v["risk_band"].map(cmap)
    v["radius"] = (v["fine_risk"] * 4).clip(40, 400)
    clat, clon, zoom = (12.972, 77.594, 11) if pick == "All areas" else (
        v["lat"].mean(), v["lon"].mean(), 13)
    layer = pdk.Layer("ScatterplotLayer", data=v, get_position=["lon", "lat"],
                      get_fill_color="color", get_radius="radius", pickable=True, opacity=0.7)
    tip = {"html": "<b>{junction_name}</b><br/>Risk: {risk_band}<br/>When: {peak_hours}",
           "style": {"backgroundColor": CITIZEN_ACCENT, "color": "white"}}
    st.pydeck_chart(pdk.Deck(layers=[layer], map_style="dark",
                    initial_view_state=pdk.ViewState(latitude=clat, longitude=clon, zoom=zoom),
                    tooltip=tip), width="stretch", height=420)
    st.markdown("### Riskiest spots " + ("citywide" if pick == "All areas" else "here"))
    emoji = {"VERY HIGH": "🔴", "HIGH": "🟠", "MODERATE": "🟡", "LOWER": "🟢"}
    for _, r in view.head(8).iterrows():
        with st.container(border=True):
            name = r["junction_name"] or f"A spot in {r['dominant_station']}"
            st.markdown(f"**{emoji.get(r['risk_band'], '')} {name}** — {r['dominant_station']} · "
                        f"**{r['risk_band']} risk**")
            st.markdown(r["nl_summary"])
            st.caption(f"Riskiest time: {r['peak_hours']}")
    st.info("Informational guide. Risk reflects how concentrated illegal-parking enforcement is "
            "and when — corrected for patrol scheduling (Location Quotient). Not a guarantee of a fine.")
    st.divider(); method_link()


# ----------------------------------------------------------------- methodology
def methodology():
    accent = CITIZEN_ACCENT if ss.role == "citizen" else POLICE_ACCENT
    css(accent)
    st.markdown(f"<div class='role-band' style='background:linear-gradient(90deg,{accent},"
                f"{accent}cc)'><h2>Methodology & Transparency</h2>"
                f"<p>How every number is computed — and what to be careful about.</p></div>",
                unsafe_allow_html=True)
    if st.button("← Back"):
        ss.show_method = False; st.rerun()
    nm = dl.nb_meta()
    k = st.columns(4)
    k[0].metric("Hotspot cells (H3)", f"{K['n_hotspots']:,}")
    k[1].metric("Overdispersion", nm.get("overdispersion", "-"))
    k[2].metric("Forecast Precision@20", f"{K['precision_at_20']:.2f}")
    k[3].metric("Enforcement uplift", f"+{K['uplift_pp']:.0f} pp")
    st.markdown(f"""
#### How it works
1. **Hotspot detection** — ~298k violations → H3 hexagons (≈174 m) + DBSCAN cross-check.
2. **Congestion Impact Score (proxy)** — volume + severity + road criticality (from the
   address text) + peak overlap. A proxy from enforcement data — **not** measured speed/flow.
3. **Location Quotient** — corrects the logging-time bias so each hotspot's peak window
   reflects its genuine local pattern (raw timestamps are ~86% night on the UTC clock).
4. **Forecast** — cell-level LightGBM (Precision@20 = {K['precision_at_20']:.2f} vs naive
   {K['naive_precision_at_20']:.2f}); station-level Negative Binomial for explainable
   next-week baselines with 95% intervals.
5. **Outcome** — backtested on held-out days: ParkPulse covers {K['parkpulse_coverage'] * 100:.0f}%
   of next-day impact vs reactive {K['reactive_coverage'] * 100:.0f}% with the same patrols
   (**+{K['uplift_pp']:.0f} pp**).
6. **Repeat-offender ratio** → targeted enforcement vs infrastructure fix.

#### Data caveats (stated openly)
- **No external data** — every signal is from the provided CSV (road type parsed from the
  `location` text, not OSM).
- **Logging-time bias** — never read raw hourly counts as real violation timing; corrected via LQ.
- **No response-time data** — closure/action timestamps are null.
- **device_id** is an enforcement-coverage proxy, not officer headcount.
- **Lower-confidence hotspots** (high data-correction rate) are flagged ⚠️.
""")


# ----------------------------------------------------------------- router
if ss.show_method:
    methodology()
elif ss.role is None:
    landing()
elif ss.role == "citizen":
    citizen_view()
elif ss.citywide or ss.station:
    police_dashboard()
else:
    station_picker()
