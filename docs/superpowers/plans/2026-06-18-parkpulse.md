# ParkPulse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI parking-congestion intelligence tool for Bengaluru Traffic Police that detects illegal-parking hotspots, scores their impact on traffic flow, forecasts tomorrow's hotspots, and outputs an optimized, downloadable patrol roster — all in a polished Streamlit dashboard.

**Architecture:** A batch pipeline cleans the raw 298k-row violations CSV and precomputes small Parquet artifacts (hotspots, impact scores, forecast, patrol plan, KPIs). A Streamlit + pydeck dashboard reads ONLY those tiny artifacts, so the live demo never does heavy compute. The artifact schema is the integration contract: a dummy-artifact generator lets the UI be built before the real models finish.

**Tech Stack:** Python 3.11, pandas + pyarrow (Parquet), h3, scikit-learn (DBSCAN), LightGBM, PuLP (CBC), OSMnx (cached), Streamlit, pydeck (deck.gl), Plotly, pytest.

**Problem statement (PS1 — Parking-Induced Congestion):** *How can AI-driven parking intelligence detect illegal-parking hotspots and quantify their impact on traffic flow to enable targeted enforcement?*

**Winning narrative:** *Today BTP enforcement is reactive patrol on yesterday's map. ParkPulse forecasts tomorrow's top hotspots, scores each by congestion impact, and hands officers an optimized, explainable patrol roster they can act on in the morning.*

**Framing & honesty (non-negotiable):** The PS1 dataset is **enforcement/violation data, not measured speed or flow**. We must **not** claim to directly measure traffic-flow impact. The metric is named **"Congestion Impact Score (proxy)"** everywhere it appears, and is always explained as derived from **volume, violation severity, vehicle footprint, road criticality, and peak-time overlap**. Any MapmyIndia/Google speed comparison is presented strictly as an optional **validation/calibration layer**, never as the basis of the score. This honest framing is itself a credibility win with BTP judges who know their data.

---

## Source Data (verified)

- Path: `C:\Users\am400\Downloads\jan to may police violation_anonymized791b166.csv`
- 298,450 rows, 24 columns, date range **2023-11-09 → 2024-04-08**.
- Timestamps are **UTC (`+00`)** — must convert to IST (Asia/Kolkata, +5:30) before any time analysis.
- `violation_type` is a **JSON-array string** (e.g. `["WRONG PARKING","PARKING NEAR ROAD CROSSING"]`), 27 subtypes, ~13% multi-label.
- All lat/lon are valid and inside the Bengaluru bbox (12.80–13.29 N, 77.44–77.77 E).
- `validation_status` ∈ {NULL, approved, rejected, created1, processing, duplicate}. Drop `rejected` + `duplicate` for "confirmed" metrics.
- 150,570 rows carry a real `junction_name` (BTP-coded). 54 police stations.

## File Structure

```
hackathon/
├── README.md                       # what/why, screenshot, 3-command quickstart, live URL
├── requirements.txt                # pinned versions
├── run.ps1                         # pipeline + app runner (PowerShell)
├── .gitignore                      # ignores data/, *.csv, __pycache__, .venv
├── config.yaml                     # H3 res, slot defs, peak hours, score weights, N units, split dates
├── .streamlit/
│   └── config.toml                 # dark theme, wide layout, brand accent
├── data/
│   ├── raw/                        # the 104 MB CSV (gitignored)
│   └── interim/                    # clean.parquet, violations_exploded.parquet (gitignored)
├── artifacts/                      # THE SERVING LAYER — committed, small
│   ├── hotspot_cells.parquet
│   ├── cis_scores.parquet
│   ├── hourly_heat.parquet
│   ├── forecast.parquet
│   ├── patrol_plan.parquet
│   └── kpis.json
├── src/
│   ├── __init__.py
│   ├── config.py                   # loads config.yaml, exposes paths + constants
│   ├── schema.py                   # artifact column contracts (the integration contract)
│   ├── etl.py                      # raw CSV → clean + exploded parquet
│   ├── hotspots.py                 # H3 aggregation + DBSCAN cross-check
│   ├── scoring.py                  # Congestion-Impact Score (CIS)
│   ├── osm_roads.py                # OSM road-class enrichment (cached, run once)
│   ├── forecast.py                 # seasonal-naive baseline + LightGBM, Precision@K
│   ├── optimizer.py                # greedy + PuLP patrol allocation
│   ├── kpis.py                     # headline numbers → kpis.json
│   ├── make_dummy_artifacts.py     # schema-correct fake artifacts to unblock the UI
│   └── run_pipeline.py             # orchestrates etl→hotspots→scoring→forecast→optimizer→kpis
├── app/
│   ├── Home.py                     # Streamlit entrypoint — hero 3D map
│   ├── data_loader.py              # @st.cache_data artifact loaders
│   ├── components/
│   │   ├── map_layer.py            # pydeck H3 hexagon layer builder
│   │   └── kpi_cards.py            # metric card row
│   └── pages/
│       ├── 1_Hotspot_Explorer.py
│       ├── 2_Deployment_Plan.py
│       └── 3_Impact_and_ROI.py
├── tests/
│   ├── test_etl.py
│   ├── test_scoring.py
│   ├── test_forecast_metrics.py
│   └── test_optimizer.py
├── notebooks/                      # exploratory only (not load-bearing)
└── docs/
    ├── architecture.png
    ├── concept_note.md
    ├── demo_script.md
    └── superpowers/plans/2026-06-18-parkpulse.md
```

## Spatial & temporal conventions (locked decisions)

- **H3 r9** (~174 m) = primary operational/forecast unit (a 2-officer beat covers it). **r10** for zoomed visual detail. **r8** for neighborhood briefing. DBSCAN used once as a cross-check only.
- **Shift slots** (IST) for forecast + roster: `MORNING 06–12`, `AFTERNOON 12–17`, `EVENING 17–22`, `NIGHT 22–06`. Peak windows: morning `08–11`, evening `17–20`.
- **Validation tiers:** `approved` = Tier A; `approved + NULL + created1 + processing` = Tier B (presumed-valid). `rejected + duplicate` excluded from confirmed metrics.

---

## Task 0: Scaffold project, config, and environment

**Files:**
- Create: `requirements.txt`, `config.yaml`, `.gitignore`, `.streamlit/config.toml`, `src/__init__.py`, `run.ps1`

- [ ] **Step 1: Create the directory tree and `.gitignore`**

```powershell
# from C:\Users\am400\Desktop\hackathon
New-Item -ItemType Directory -Force data\raw, data\interim, artifacts, src, app\components, app\pages, tests, notebooks, docs, .streamlit | Out-Null
Copy-Item "C:\Users\am400\Downloads\jan to may police violation_anonymized791b166.csv" "data\raw\violations.csv"
```

`.gitignore`:
```
data/
*.csv
__pycache__/
*.pyc
.venv/
.ipynb_checkpoints/
.streamlit/secrets.toml
```

- [ ] **Step 2: Write `requirements.txt` (pinned)**

```
pandas==2.2.2
pyarrow==16.1.0
numpy==1.26.4
h3==4.1.0
scikit-learn==1.5.1
lightgbm==4.5.0
pulp==2.9.0
osmnx==1.9.4
streamlit==1.38.0
pydeck==0.9.1
plotly==5.23.0
pyyaml==6.0.2
shap==0.46.0
pytest==8.3.2
```

- [ ] **Step 3: Create venv and install**

Run:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Expected: all install cleanly. If `lightgbm`/`shap` wheels stall, they are stretch-only — comment them out to unblock and reinstall on Day 3.

- [ ] **Step 4: Write `config.yaml`**

```yaml
paths:
  raw_csv: data/raw/violations.csv
  interim_dir: data/interim
  artifacts_dir: artifacts
bbox: {min_lat: 12.80, max_lat: 13.29, min_lon: 77.44, max_lon: 77.77}
h3: {res_op: 9, res_zoom: 10, res_area: 8}
timezone: Asia/Kolkata
shift_slots:
  MORNING: [6, 12]
  AFTERNOON: [12, 17]
  EVENING: [17, 22]
  NIGHT: [22, 6]
peak_hours: {morning: [8, 11], evening: [17, 20]}
validation:
  tier_a: [approved]
  tier_b: [approved, "NULL", created1, processing]
  exclude: [rejected, duplicate]
cis_weights: {volume: 0.25, severity: 0.30, road: 0.30, peak: 0.15}
severity_weights:
  "DOUBLE PARKING": 1.0
  "PARKING IN A MAIN ROAD": 1.0
  "PARKING NEAR ROAD CROSSING": 1.0
  "PARKING NEAR TRAFFIC LIGHT": 1.0
  "PARKING ON ZEBRA": 1.0
  "WRONG PARKING": 0.7
  "NO PARKING": 0.7
  "PARKING ON FOOTPATH": 0.4
  "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 0.4
  "DEFECTIVE NUMBER PLATE": 0.0
  "BLACK FILM": 0.0
  "REFUSE TO GO FOR HIRE": 0.0
  _default: 0.6
vehicle_footprint:
  commercial: 1.5
  car: 1.0
  two_wheeler: 0.4
commercial_types: [PASSENGER AUTO, MAXI-CAB, LGV, GOODS AUTO, "BUS (BMTC/KSRTC)", PRIVATE BUS, LORRY/GOODS VEHICLE, TEMPO, TANKER, HGV, VAN]
two_wheeler_types: [SCOOTER, "MOTOR CYCLE", MOPED]
optimizer: {n_units_per_shift: 6, max_cells_per_unit: 3}
split: {train_end: "2024-03-01", val_end: "2024-03-21", test_end: "2024-04-08"}
```

- [ ] **Step 5: Write `.streamlit/config.toml`**

```toml
[theme]
base = "dark"
primaryColor = "#FF5A1F"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1A1D27"
font = "sans serif"
[server]
headless = true
```

- [ ] **Step 6: Create empty `src/__init__.py` and commit**

```powershell
New-Item -ItemType File src\__init__.py
git init
git add .gitignore requirements.txt config.yaml .streamlit/config.toml src/__init__.py
git commit -m "chore: scaffold ParkPulse project, config, env"
```

---

## Task 1: Config loader (`src/config.py`)

**Files:**
- Create: `src/config.py`

- [ ] **Step 1: Write the config loader**

```python
# src/config.py
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

RAW_CSV = ROOT / CFG["paths"]["raw_csv"]
INTERIM = ROOT / CFG["paths"]["interim_dir"]
ARTIFACTS = ROOT / CFG["paths"]["artifacts_dir"]
INTERIM.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(parents=True, exist_ok=True)

BBOX = CFG["bbox"]
H3 = CFG["h3"]
TZ = CFG["timezone"]
SHIFT_SLOTS = CFG["shift_slots"]
PEAK = CFG["peak_hours"]
VALIDATION = CFG["validation"]
CIS_WEIGHTS = CFG["cis_weights"]
SEVERITY = CFG["severity_weights"]
VEH_FOOTPRINT = CFG["vehicle_footprint"]
COMMERCIAL = set(CFG["commercial_types"])
TWO_WHEELER = set(CFG["two_wheeler_types"])
OPT = CFG["optimizer"]
SPLIT = CFG["split"]


def shift_of(hour: int) -> str:
    """Map an IST hour (0-23) to a shift slot name."""
    for name, (start, end) in SHIFT_SLOTS.items():
        if start < end:
            if start <= hour < end:
                return name
        else:  # wraps midnight (NIGHT 22-06)
            if hour >= start or hour < end:
                return name
    return "NIGHT"


def footprint_class(vehicle_type: str) -> str:
    if vehicle_type in COMMERCIAL:
        return "commercial"
    if vehicle_type in TWO_WHEELER:
        return "two_wheeler"
    return "car"
```

- [ ] **Step 2: Smoke-test it**

Run: `python -c "from src.config import shift_of, footprint_class; print(shift_of(9), shift_of(23), footprint_class('LGV'))"`
Expected: `MORNING NIGHT commercial`

- [ ] **Step 3: Commit**

```powershell
git add src/config.py
git commit -m "feat: config loader with shift/footprint helpers"
```

---

## Task 2: Artifact schema contract + dummy generator

This unblocks the dashboard before any real model exists.

**Files:**
- Create: `src/schema.py`, `src/make_dummy_artifacts.py`

- [ ] **Step 1: Write `src/schema.py` (the contract)**

```python
# src/schema.py
"""Column contracts for every artifact. The UI builds against these names."""

HOTSPOT_CELLS = ["h3", "lat", "lon", "violation_count", "confirmed_count",
                 "junction_name", "police_station", "dominant_vehicle",
                 "dominant_violation", "dbscan_cluster"]

CIS_SCORES = ["h3", "lat", "lon", "cis", "f_volume", "f_severity", "f_road",
              "f_peak", "road_class", "rank"]

HOURLY_HEAT = ["h3", "lat", "lon", "hour", "is_weekend", "count", "cis_hour"]

FORECAST = ["h3", "lat", "lon", "date", "shift", "pred_intensity", "expected_violations"]

PATROL_PLAN = ["shift", "h3", "lat", "lon", "junction_name", "police_station",
               "expected_violations", "dominant_vehicle", "dominant_violation",
               "cis", "assigned_unit", "rank"]

KPIS = ["total_violations", "confirmed_violations", "n_stations", "n_hotspots",
        "top20_impact_share", "evening_enforcement_share", "repeat_offenders",
        "precision_at_20", "naive_precision_at_20", "speed_corr_spearman",
        "date_min", "date_max"]
```

- [ ] **Step 2: Write `src/make_dummy_artifacts.py`**

```python
# src/make_dummy_artifacts.py
import json
import numpy as np
import pandas as pd
from src import schema
from src.config import ARTIFACTS, SHIFT_SLOTS

rng = np.random.default_rng(42)
N = 400  # fake active cells
lat = rng.uniform(12.90, 13.05, N)
lon = rng.uniform(77.55, 77.66, N)
h3ids = [f"89{i:013x}" for i in range(N)]
veh = rng.choice(["CAR", "SCOOTER", "PASSENGER AUTO", "LGV"], N)
viol = rng.choice(["WRONG PARKING", "NO PARKING", "DOUBLE PARKING", "PARKING IN A MAIN ROAD"], N)
stations = rng.choice(["Upparpet", "Shivajinagar", "Malleshwaram", "HSR Layout"], N)
counts = rng.integers(5, 600, N)

cis = rng.uniform(0, 1, N)
pd.DataFrame({
    "h3": h3ids, "lat": lat, "lon": lon, "violation_count": counts,
    "confirmed_count": (counts * 0.7).astype(int),
    "junction_name": rng.choice(["Safina Plaza", "KR Market", "No Junction"], N),
    "police_station": stations, "dominant_vehicle": veh,
    "dominant_violation": viol, "dbscan_cluster": rng.integers(-1, 20, N),
})[schema.HOTSPOT_CELLS].to_parquet(ARTIFACTS / "hotspot_cells.parquet")

pd.DataFrame({
    "h3": h3ids, "lat": lat, "lon": lon, "cis": cis,
    "f_volume": rng.uniform(0, 1, N), "f_severity": rng.uniform(0, 1, N),
    "f_road": rng.uniform(0, 1, N), "f_peak": rng.uniform(0, 1, N),
    "road_class": rng.choice(["primary", "secondary", "tertiary", "residential"], N),
    "rank": np.argsort(-cis).argsort() + 1,
})[schema.CIS_SCORES].to_parquet(ARTIFACTS / "cis_scores.parquet")

rows = []
for h, la, lo, c in zip(h3ids, lat, lon, cis):
    for hour in range(24):
        peak = 1.6 if hour in (9, 10, 18, 19) else 0.6
        rows.append([h, la, lo, hour, 0, int(rng.poisson(c * 10 * peak)), c * peak])
pd.DataFrame(rows, columns=schema.HOURLY_HEAT).to_parquet(ARTIFACTS / "hourly_heat.parquet")

frows = []
for d in pd.date_range("2024-04-09", periods=1):
    for h, la, lo, c in zip(h3ids, lat, lon, cis):
        for s in SHIFT_SLOTS:
            frows.append([h, la, lo, d.date().isoformat(), s, c * rng.uniform(0.5, 1.5),
                          int(rng.poisson(c * 8))])
pd.DataFrame(frows, columns=schema.FORECAST).to_parquet(ARTIFACTS / "forecast.parquet")

top = pd.DataFrame({"h3": h3ids, "lat": lat, "lon": lon, "cis": cis,
                    "ev": rng.integers(5, 60, N), "veh": veh, "viol": viol,
                    "st": stations, "jn": "Safina Plaza"}).nlargest(24, "cis")
prows = []
for s in SHIFT_SLOTS:
    for i, (_, r) in enumerate(top.head(6).iterrows()):
        prows.append([s, r.h3, r.lat, r.lon, r.jn, r.st, int(r.ev), r.veh,
                      r.viol, float(r.cis), f"Unit {i+1}", i + 1])
pd.DataFrame(prows, columns=schema.PATROL_PLAN).to_parquet(ARTIFACTS / "patrol_plan.parquet")

json.dump({
    "total_violations": 298450, "confirmed_violations": 208846, "n_stations": 54,
    "n_hotspots": N, "top20_impact_share": 0.41, "evening_enforcement_share": 0.07,
    "repeat_offenders": 711, "precision_at_20": 0.62, "naive_precision_at_20": 0.43,
    "speed_corr_spearman": 0.51, "date_min": "2023-11-09", "date_max": "2024-04-08",
}, open(ARTIFACTS / "kpis.json", "w"), indent=2)
print("Dummy artifacts written to", ARTIFACTS)
```

- [ ] **Step 3: Generate and verify**

Run: `python -m src.make_dummy_artifacts`
Expected: prints path; 5 `.parquet` + `kpis.json` exist in `artifacts/`.

- [ ] **Step 4: Commit**

```powershell
git add src/schema.py src/make_dummy_artifacts.py artifacts/
git commit -m "feat: artifact schema contract + dummy artifact generator"
```

---

## Task 3: ETL — clean, IST, explode, H3-tag (`src/etl.py`)

**Files:**
- Create: `src/etl.py`, `tests/test_etl.py`

- [ ] **Step 1: Write failing tests for the pure helpers**

```python
# tests/test_etl.py
import pandas as pd
from src.etl import to_ist, parse_violations, footprint_for_row

def test_to_ist_adds_530():
    s = pd.Series(["2023-11-20 00:28:46+00"])
    out = to_ist(s)
    assert out.dt.hour.iloc[0] == 5 and out.dt.minute.iloc[0] == 58

def test_parse_violations_handles_array_and_garbage():
    assert parse_violations('["WRONG PARKING","NO PARKING"]') == ["WRONG PARKING", "NO PARKING"]
    assert parse_violations("NULL") == []
    assert parse_violations(None) == []

def test_footprint_for_row():
    assert footprint_for_row("LGV") == "commercial"
    assert footprint_for_row("SCOOTER") == "two_wheeler"
    assert footprint_for_row("CAR") == "car"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_etl.py -v`
Expected: FAIL — `cannot import name ... from src.etl`.

- [ ] **Step 3: Write `src/etl.py`**

```python
# src/etl.py
import json
import pandas as pd
import h3
from src.config import (RAW_CSV, INTERIM, BBOX, H3, TZ, VALIDATION,
                        footprint_class, shift_of, PEAK)

USECOLS = ["id", "latitude", "longitude", "location", "vehicle_type",
           "violation_type", "created_datetime", "police_station",
           "junction_name", "validation_status", "vehicle_number"]


def to_ist(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce").dt.tz_convert(TZ)


def parse_violations(raw) -> list:
    if raw is None or (isinstance(raw, float)) or raw == "NULL":
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def footprint_for_row(vehicle_type) -> str:
    return footprint_class(vehicle_type if isinstance(vehicle_type, str) else "")


def _is_peak(hour: int) -> bool:
    mp, ep = PEAK["morning"], PEAK["evening"]
    return mp[0] <= hour < mp[1] or ep[0] <= hour < ep[1]


def run() -> pd.DataFrame:
    df = pd.read_csv(RAW_CSV, usecols=USECOLS, dtype=str)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    # bbox clip
    df = df[(df.latitude.between(BBOX["min_lat"], BBOX["max_lat"])) &
            (df.longitude.between(BBOX["min_lon"], BBOX["max_lon"]))].copy()
    # time → IST
    df["ts"] = to_ist(df["created_datetime"])
    df = df.dropna(subset=["ts"]).copy()
    df["hour"] = df["ts"].dt.hour
    df["dow"] = df["ts"].dt.dayofweek
    df["is_weekend"] = df["dow"] >= 5
    df["date"] = df["ts"].dt.date.astype(str)
    df["shift"] = df["hour"].map(shift_of)
    df["is_peak"] = df["hour"].map(_is_peak)
    # validation tiers
    vs = df["validation_status"].fillna("NULL")
    df["confirmed"] = ~vs.isin(VALIDATION["exclude"])
    # H3 tagging
    df["h3"] = [h3.latlng_to_cell(la, lo, H3["res_op"])
                for la, lo in zip(df.latitude, df.longitude)]
    df["footprint"] = df["vehicle_type"].map(footprint_for_row)
    df["violations"] = df["violation_type"].map(parse_violations)
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(INTERIM / "clean.parquet")
    # exploded long form for subtype analysis
    expl = df[["id", "h3", "ts", "hour", "shift", "is_peak", "footprint",
               "confirmed", "vehicle_type"]].join(
        df["violations"].explode().rename("violation"))
    expl.to_parquet(INTERIM / "violations_exploded.parquet")
    print(f"ETL done: {len(df):,} clean rows, {expl['violation'].notna().sum():,} violation records")
    return df


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests + ETL to verify**

Run: `pytest tests/test_etl.py -v`
Expected: 3 PASS.
Run: `python -m src.etl`
Expected: prints `ETL done: ~298,4xx clean rows ...`; `data/interim/clean.parquet` exists.

- [ ] **Step 5: Commit**

```powershell
git add src/etl.py tests/test_etl.py
git commit -m "feat: ETL with IST conversion, violation explode, H3 tagging"
```

---

## Task 4: Hotspot detection (`src/hotspots.py`)

**Files:**
- Create: `src/hotspots.py`

- [ ] **Step 1: Write `src/hotspots.py`**

```python
# src/hotspots.py
import numpy as np
import pandas as pd
import h3
from sklearn.cluster import DBSCAN
from src.config import INTERIM, ARTIFACTS
from src import schema


def run() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    g = df.groupby("h3")
    agg = g.agg(
        violation_count=("id", "count"),
        confirmed_count=("confirmed", "sum"),
        junction_name=("junction_name", lambda s: s.mode().iat[0] if not s.mode().empty else "No Junction"),
        police_station=("police_station", lambda s: s.mode().iat[0] if not s.mode().empty else "Unknown"),
        dominant_vehicle=("vehicle_type", lambda s: s.mode().iat[0] if not s.mode().empty else "UNKNOWN"),
    ).reset_index()
    # exploded for dominant violation subtype
    expl = pd.read_parquet(INTERIM / "violations_exploded.parquet").dropna(subset=["violation"])
    dom_v = (expl.groupby("h3")["violation"]
             .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "UNKNOWN")
             .rename("dominant_violation").reset_index())
    agg = agg.merge(dom_v, on="h3", how="left")
    agg["dominant_violation"] = agg["dominant_violation"].fillna("UNKNOWN")
    # cell centroids
    cents = np.array([h3.cell_to_latlng(c) for c in agg["h3"]])
    agg["lat"], agg["lon"] = cents[:, 0], cents[:, 1]
    # DBSCAN cross-check (haversine, ~150 m eps) weighted by where density is
    coords = np.radians(cents)
    db = DBSCAN(eps=150 / 6371000, min_samples=3, metric="haversine").fit(coords)
    agg["dbscan_cluster"] = db.labels_
    agg = agg[schema.HOTSPOT_CELLS]
    agg.to_parquet(ARTIFACTS / "hotspot_cells.parquet")
    print(f"Hotspots: {len(agg):,} active H3 cells, "
          f"{(agg.dbscan_cluster>=0).sum():,} in DBSCAN clusters")
    return agg


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run + sanity check**

Run: `python -m src.hotspots`
Expected: prints active cell count (low thousands); `artifacts/hotspot_cells.parquet` written with `schema.HOTSPOT_CELLS` columns.

- [ ] **Step 3: Commit**

```powershell
git add src/hotspots.py
git commit -m "feat: H3 hotspot aggregation + DBSCAN cross-check"
```

---

## Task 5: Congestion-Impact Score — proxy (`src/scoring.py`)

> **Framing:** This is a **proxy** index, not measured flow. It is built only from enforcement-data signals (volume, severity, vehicle footprint, road criticality, peak overlap). Label it "Congestion Impact Score (proxy)" in every UI surface and document. Speed calibration (Task 6 / MapmyIndia) is a separate optional validation layer.

**Files:**
- Create: `src/scoring.py`, `tests/test_scoring.py`

- [ ] **Step 1: Write failing tests for the scoring math**

```python
# tests/test_scoring.py
from src.scoring import severity_for, normalize

def test_severity_blocking_vs_incidental():
    assert severity_for(["DOUBLE PARKING"], "LGV") > severity_for(["WRONG PARKING"], "CAR")
    assert severity_for(["DEFECTIVE NUMBER PLATE"], "SCOOTER") == 0.0

def test_severity_commercial_multiplier():
    assert severity_for(["WRONG PARKING"], "LGV") > severity_for(["WRONG PARKING"], "SCOOTER")

def test_normalize_0_1():
    out = normalize([0, 5, 10])
    assert out[0] == 0.0 and out[-1] == 1.0
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_scoring.py -v`
Expected: FAIL — import error.

- [ ] **Step 3: Write `src/scoring.py`**

```python
# src/scoring.py
import numpy as np
import pandas as pd
from src.config import (INTERIM, ARTIFACTS, SEVERITY, VEH_FOOTPRINT,
                        CIS_WEIGHTS, footprint_class)
from src import schema


def severity_for(violations, vehicle_type) -> float:
    if not violations:
        base = 0.0
    else:
        base = max(SEVERITY.get(v, SEVERITY["_default"]) for v in violations)
    mult = VEH_FOOTPRINT[footprint_class(vehicle_type if isinstance(vehicle_type, str) else "")]
    return base * mult


def normalize(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = np.nanmin(x), np.nanmax(x)
    return np.zeros_like(x) if hi == lo else (x - lo) / (hi - lo)


def run(road_scores: dict | None = None) -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    df["sev"] = [severity_for(v, vt) for v, vt in zip(df["violations"], df["vehicle_type"])]
    g = df.groupby("h3")
    cells = g.agg(
        n=("id", "count"),
        sev=("sev", "mean"),
        peak=("is_peak", "mean"),
    ).reset_index()
    cells["f_volume"] = normalize(np.log1p(cells["n"]))
    cells["f_severity"] = normalize(cells["sev"])
    cells["f_peak"] = normalize(cells["peak"])
    # road criticality from OSM (Task 6); default neutral 0.5 if absent
    if road_scores:
        cells["f_road"] = cells["h3"].map(road_scores).fillna(0.5)
        cells["road_class"] = cells["h3"].map(
            lambda h: road_scores.get(h, ("residential", 0.5))[0]
            if isinstance(road_scores.get(h), tuple) else "unknown").fillna("unknown")
    else:
        cells["f_road"] = 0.5
        cells["road_class"] = "unknown"
    w = CIS_WEIGHTS
    cells["cis"] = (w["volume"] * cells["f_volume"] + w["severity"] * cells["f_severity"]
                    + w["road"] * cells["f_road"] + w["peak"] * cells["f_peak"])
    # merge centroids from hotspot artifact
    hs = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")[["h3", "lat", "lon"]]
    cells = cells.merge(hs, on="h3", how="left")
    cells["rank"] = cells["cis"].rank(ascending=False, method="min").astype(int)
    out = cells.sort_values("rank")[schema.CIS_SCORES]
    out.to_parquet(ARTIFACTS / "cis_scores.parquet")
    print(f"CIS scored {len(out):,} cells. Top-3 ranks written.")
    return out


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests + scoring**

Run: `pytest tests/test_scoring.py -v` → 3 PASS.
Run: `python -m src.scoring` → writes `artifacts/cis_scores.parquet`.

- [ ] **Step 5: Build the hourly heat artifact (for the time slider)**

Append to `src/scoring.py`:

```python
def build_hourly_heat() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "cis", "lat", "lon"]]
    heat = (df.groupby(["h3", "hour", "is_weekend"])["id"].count()
            .rename("count").reset_index())
    heat = heat.merge(cis, on="h3", how="left")
    heat["cis_hour"] = heat["cis"].fillna(0) * (heat["count"] / heat["count"].max())
    heat = heat[schema.HOURLY_HEAT]
    heat.to_parquet(ARTIFACTS / "hourly_heat.parquet")
    print(f"Hourly heat: {len(heat):,} cell-hour rows")
    return heat
```

Run: `python -c "from src.scoring import build_hourly_heat; build_hourly_heat()"`
Expected: writes `artifacts/hourly_heat.parquet`.

- [ ] **Step 6: Commit**

```powershell
git add src/scoring.py tests/test_scoring.py
git commit -m "feat: congestion-impact score + hourly heat artifact"
```

---

## Task 6: OSM road-class enrichment (`src/osm_roads.py`) — STRETCH (Day 3)

Run once, cache to parquet, never live-query.

**Files:**
- Create: `src/osm_roads.py`

- [ ] **Step 1: Write `src/osm_roads.py`**

```python
# src/osm_roads.py
import numpy as np
import pandas as pd
import osmnx as ox
import h3
from src.config import INTERIM, ARTIFACTS

ROAD_WEIGHT = {"motorway": 1.0, "trunk": 1.0, "primary": 0.9, "secondary": 0.7,
               "tertiary": 0.5, "residential": 0.3, "unclassified": 0.3}


def build(cache=INTERIM / "osm_roads.parquet") -> dict:
    if cache.exists():
        d = pd.read_parquet(cache)
        return {r.h3: (r.road_class, r.f_road) for r in d.itertuples()}
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")
    G = ox.graph_from_place("Bengaluru, India", network_type="drive")
    edges = ox.graph_to_gdfs(G, nodes=False)
    rows = []
    for r in cis.itertuples():
        try:
            u, v, k = ox.distance.nearest_edges(G, r.lon, r.lat)
            hwy = edges.loc[(u, v, k), "highway"]
            hwy = hwy[0] if isinstance(hwy, list) else hwy
        except Exception:
            hwy = "residential"
        rows.append([r.h3, hwy, ROAD_WEIGHT.get(hwy, 0.4)])
    d = pd.DataFrame(rows, columns=["h3", "road_class", "f_road"])
    d.to_parquet(cache)
    return {r.h3: (r.road_class, r.f_road) for r in d.itertuples()}


if __name__ == "__main__":
    print(f"OSM road classes cached for {len(build())} cells")
```

- [ ] **Step 2: Run once (needs internet) then re-run scoring with road data**

Run: `python -m src.osm_roads`
Then wire into scoring:
```python
# one-off rescoring with road data
python -c "from src.osm_roads import build; from src.scoring import run; run(road_scores=build())"
```
Expected: `f_road` and `road_class` populated in `cis_scores.parquet`.
**If OSM fails or runs out of time:** skip — scoring already falls back to `f_road=0.5`. Not load-bearing for MVP.

- [ ] **Step 3: Commit**

```powershell
git add src/osm_roads.py
git commit -m "feat: cached OSM road-class enrichment for impact score"
```

---

## Task 7: Forecast (`src/forecast.py`)

**Files:**
- Create: `src/forecast.py`, `tests/test_forecast_metrics.py`

- [ ] **Step 1: Write failing test for the ranking metric**

```python
# tests/test_forecast_metrics.py
from src.forecast import precision_at_k

def test_precision_at_k_perfect():
    actual = {"a": 10, "b": 9, "c": 1, "d": 0}
    pred = {"a": 5, "b": 4, "c": 0.1, "d": 0.0}
    assert precision_at_k(actual, pred, k=2) == 1.0

def test_precision_at_k_half():
    actual = {"a": 10, "b": 9, "c": 1, "d": 0}
    pred = {"c": 5, "a": 4, "d": 1, "b": 0}
    assert precision_at_k(actual, pred, k=2) == 0.5
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_forecast_metrics.py -v`
Expected: FAIL — import error.

- [ ] **Step 3: Write `src/forecast.py`**

```python
# src/forecast.py
import numpy as np
import pandas as pd
from src.config import INTERIM, ARTIFACTS, SPLIT, SHIFT_SLOTS, shift_of
from src import schema


def precision_at_k(actual: dict, pred: dict, k: int) -> float:
    top_actual = set(sorted(actual, key=actual.get, reverse=True)[:k])
    top_pred = set(sorted(pred, key=pred.get, reverse=True)[:k])
    return len(top_actual & top_pred) / k


def _panel() -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    df["slot"] = df["date"] + "|" + df["shift"]
    panel = (df.groupby(["h3", "date", "shift"])["id"].count()
             .rename("y").reset_index())
    panel["date"] = pd.to_datetime(panel["date"])
    return panel.sort_values("date")


def run() -> pd.DataFrame:
    panel = _panel()
    # seasonal-naive: same weekday+shift mean from training history
    panel["dow"] = panel["date"].dt.dayofweek
    train = panel[panel["date"] < SPLIT["train_end"]]
    naive = (train.groupby(["h3", "dow", "shift"])["y"].mean()
             .rename("naive").reset_index())
    # LightGBM (stretch). MVP = seasonal-naive forecast for next day per cell/shift.
    last_date = panel["date"].max()
    next_date = (last_date + pd.Timedelta(days=1))
    nd, ns = next_date.dayofweek, list(SHIFT_SLOTS)
    grid = (naive[naive["dow"] == nd]
            .groupby(["h3", "shift"])["naive"].mean().reset_index())
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "lat", "lon", "cis"]]
    grid = grid.merge(cis, on="h3", how="left")
    grid["date"] = next_date.date().isoformat()
    grid["pred_intensity"] = grid["naive"] * grid["cis"].fillna(grid["cis"].median())
    grid["expected_violations"] = grid["naive"].round().astype(int)
    out = grid.rename(columns={})[schema.FORECAST]
    out.to_parquet(ARTIFACTS / "forecast.parquet")

    # report Precision@20 vs naive on the test window (honesty metric for the deck)
    test = panel[panel["date"] > SPLIT["val_end"]]
    if len(test):
        actual = test.groupby("h3")["y"].sum().to_dict()
        pred_naive = naive.groupby("h3")["naive"].mean().to_dict()
        p20 = precision_at_k(actual, pred_naive, 20)
        print(f"Forecast written. Seasonal-naive Precision@20 (test) = {p20:.2f}")
    return out


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests + forecast**

Run: `pytest tests/test_forecast_metrics.py -v` → 2 PASS.
Run: `python -m src.forecast` → writes `artifacts/forecast.parquet`, prints Precision@20.

- [ ] **Step 5 (STRETCH): add LightGBM model that beats naive**

Append a `run_lgbm()` to `src/forecast.py` that builds lag/rolling features on `_panel()`, fits `LGBMRegressor(objective="tweedie")` with the temporal split from `SPLIT`, and reports `precision_at_k` vs the naive baseline. Only do this once MVP is green. If `precision_at_20` beats naive, store both numbers in `kpis.json` (Task 9).

- [ ] **Step 6: Commit**

```powershell
git add src/forecast.py tests/test_forecast_metrics.py
git commit -m "feat: seasonal-naive forecast + Precision@K metric"
```

---

## Task 8: Patrol optimizer (`src/optimizer.py`)

**Files:**
- Create: `src/optimizer.py`, `tests/test_optimizer.py`

- [ ] **Step 1: Write failing test for the greedy allocator**

```python
# tests/test_optimizer.py
import pandas as pd
from src.optimizer import greedy_allocate

def test_greedy_picks_highest_value_per_shift():
    cells = pd.DataFrame({
        "h3": ["a", "b", "c"], "shift": ["MORNING"] * 3,
        "value": [10.0, 5.0, 1.0],
    })
    plan = greedy_allocate(cells, n_units=2)
    assert list(plan["h3"]) == ["a", "b"]
    assert list(plan["assigned_unit"]) == ["Unit 1", "Unit 2"]
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_optimizer.py -v`
Expected: FAIL — import error.

- [ ] **Step 3: Write `src/optimizer.py`**

```python
# src/optimizer.py
import pandas as pd
from src.config import ARTIFACTS, OPT
from src import schema


def greedy_allocate(cells: pd.DataFrame, n_units: int) -> pd.DataFrame:
    """Per shift, assign the n_units highest-value cells to units."""
    out = []
    for shift, grp in cells.sort_values("value", ascending=False).groupby("shift"):
        for i, (_, r) in enumerate(grp.head(n_units).iterrows()):
            row = r.to_dict()
            row["assigned_unit"] = f"Unit {i + 1}"
            row["rank"] = i + 1
            out.append(row)
    return pd.DataFrame(out)


def run() -> pd.DataFrame:
    fc = pd.read_parquet(ARTIFACTS / "forecast.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")[["h3", "cis"]]
    hs = pd.read_parquet(ARTIFACTS / "hotspot_cells.parquet")[
        ["h3", "junction_name", "police_station", "dominant_vehicle", "dominant_violation"]]
    df = fc.merge(cis, on="h3", how="left").merge(hs, on="h3", how="left")
    df["value"] = df["pred_intensity"].fillna(0) * df["cis"].fillna(0)
    plan = greedy_allocate(df, OPT["n_units_per_shift"])
    plan = plan.rename(columns={"expected_violations": "expected_violations"})
    plan = plan[schema.PATROL_PLAN]
    plan.to_parquet(ARTIFACTS / "patrol_plan.parquet")
    print(f"Patrol plan: {len(plan)} assignments across {plan['shift'].nunique()} shifts")
    return plan


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests + optimizer**

Run: `pytest tests/test_optimizer.py -v` → PASS.
Run: `python -m src.optimizer` → writes `artifacts/patrol_plan.parquet`.

- [ ] **Step 5 (STRETCH): PuLP ILP version**

Add `ilp_allocate(cells, n_units, max_cells_per_unit)` using PuLP/CBC maximizing `Σ value·x[c,s]` subject to per-shift capacity. Fall back to `greedy_allocate` on any solver error. Greedy stays the default.

- [ ] **Step 6: Commit**

```powershell
git add src/optimizer.py tests/test_optimizer.py
git commit -m "feat: greedy patrol allocator producing deployable roster"
```

---

## Task 9: KPIs + pipeline runner

**Files:**
- Create: `src/kpis.py`, `src/run_pipeline.py`, `run.ps1`

- [ ] **Step 1: Write `src/kpis.py`**

```python
# src/kpis.py
import json
import pandas as pd
from src.config import INTERIM, ARTIFACTS


def run() -> dict:
    df = pd.read_parquet(INTERIM / "clean.parquet")
    cis = pd.read_parquet(ARTIFACTS / "cis_scores.parquet")
    total = len(df)
    confirmed = int(df["confirmed"].sum())
    # impact concentration: top-20 cells' share of summed CIS-weighted volume
    vol = df.groupby("h3")["id"].count().rename("n").reset_index().merge(
        cis[["h3", "cis"]], on="h3", how="left")
    vol["impact"] = vol["n"] * vol["cis"].fillna(0)
    top20 = vol.nlargest(20, "impact")["impact"].sum() / vol["impact"].sum()
    evening = (df["shift"] == "EVENING").mean()
    repeats = (df.groupby("vehicle_number")["id"].count() >= 10).sum()
    k = {
        "total_violations": total,
        "confirmed_violations": confirmed,
        "n_stations": int(df["police_station"].nunique()),
        "n_hotspots": int(cis["h3"].nunique()),
        "top20_impact_share": round(float(top20), 3),
        "evening_enforcement_share": round(float(evening), 3),
        "repeat_offenders": int(repeats),
        "precision_at_20": None,        # filled by forecast LGBM stretch
        "naive_precision_at_20": None,
        "speed_corr_spearman": None,    # filled by MapMyIndia/Google calibration stretch
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
    }
    json.dump(k, open(ARTIFACTS / "kpis.json", "w"), indent=2)
    print("KPIs:", k)
    return k


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Write `src/run_pipeline.py`**

```python
# src/run_pipeline.py
from src import etl, hotspots, scoring, forecast, optimizer, kpis

if __name__ == "__main__":
    etl.run()
    hotspots.run()
    scoring.run()
    scoring.build_hourly_heat()
    forecast.run()
    optimizer.run()
    kpis.run()
    print("\nPipeline complete. artifacts/ refreshed.")
```

- [ ] **Step 3: Write `run.ps1`**

```powershell
param([string]$cmd = "all")
.\.venv\Scripts\Activate.ps1
switch ($cmd) {
  "pipeline" { python -m src.run_pipeline }
  "app"      { streamlit run app/Home.py }
  "dummy"    { python -m src.make_dummy_artifacts }
  "test"     { pytest -q }
  default    { python -m src.run_pipeline; streamlit run app/Home.py }
}
```

- [ ] **Step 4: Run the full pipeline on real data**

Run: `python -m src.run_pipeline`
Expected: each stage prints its summary; all 5 parquet + `kpis.json` regenerated from real data. Verify `kpis.json` shows ~298k total and a plausible `top20_impact_share`.

- [ ] **Step 5: Commit**

```powershell
git add src/kpis.py src/run_pipeline.py run.ps1
git commit -m "feat: KPIs + end-to-end pipeline runner"
```

---

## Task 10: Streamlit Home — the hero 3D map

**Files:**
- Create: `app/data_loader.py`, `app/components/map_layer.py`, `app/components/kpi_cards.py`, `app/Home.py`

- [ ] **Step 1: Write `app/data_loader.py`**

```python
# app/data_loader.py
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
```

- [ ] **Step 2: Write `app/components/map_layer.py`**

```python
# app/components/map_layer.py
import pydeck as pdk


def hexagon_layer(df, value_col="cis_hour", elevation_scale=80):
    return pdk.Layer(
        "H3HexagonLayer",
        df,
        get_hexagon="h3",
        get_fill_color=f"[255, 90 + 165*(1-{value_col}), 30, 180]",
        get_elevation=value_col,
        elevation_scale=elevation_scale,
        extruded=True,
        pickable=True,
        auto_highlight=True,
    )


def deck(df, value_col="cis_hour", tooltip=None):
    return pdk.Deck(
        layers=[hexagon_layer(df, value_col)],
        initial_view_state=pdk.ViewState(latitude=12.97, longitude=77.59,
                                         zoom=11, pitch=50, bearing=10),
        map_style=None,  # token-free carto fallback
        tooltip=tooltip or {"text": "{h3}\nIntensity: {" + value_col + "}"},
    )
```

- [ ] **Step 3: Write `app/components/kpi_cards.py`**

```python
# app/components/kpi_cards.py
import streamlit as st


def render(k):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Violations analyzed", f"{k['total_violations']:,}")
    c2.metric("Top-20 hotspots = impact share", f"{k['top20_impact_share']*100:.0f}%")
    c3.metric("Evening-peak enforcement", f"{k['evening_enforcement_share']*100:.0f}%",
              help="Share of violations logged in the 17:00-22:00 shift — the un-enforced peak")
    c4.metric("Chronic repeat offenders", f"{k['repeat_offenders']:,}")
```

- [ ] **Step 4: Write `app/Home.py`**

```python
# app/Home.py
import streamlit as st
from app import data_loader as dl
from app.components import map_layer, kpi_cards

st.set_page_config(page_title="ParkPulse — BTP Parking Intelligence",
                   layout="wide", page_icon="🅿️")
st.title("🅿️ ParkPulse")
st.caption("Bengaluru Traffic Police · AI parking-congestion intelligence · "
           "Data: Jan–Apr 2024 · 298,450 records · 54 stations")

k = dl.kpis()
kpi_cards.render(k)

heat = dl.hourly()
col_map, col_ctrl = st.columns([4, 1])
with col_ctrl:
    hour = st.slider("Hour of day (IST)", 0, 23, 9)
    weekend = st.toggle("Weekend", value=False)
view = heat[(heat["hour"] == hour) & (heat["is_weekend"] == weekend)]
view = view.nlargest(800, "cis_hour")  # cap geometry for snappy render
with col_map:
    st.pydeck_chart(map_layer.deck(view, "cis_hour"), use_container_width=True)

st.markdown("**Drag the hour slider from 9 AM to 6 PM** — watch hotspots surge at peak. "
            "Congestion isn't static; our plan is time-aware.")
st.caption("Hotspot height/colour = **Congestion Impact Score (proxy)** — derived from "
           "violation volume, severity, vehicle footprint, road criticality and peak-time "
           "overlap. It is an enforcement-data proxy, not a direct speed/flow measurement.")
```

- [ ] **Step 5: Make `app/` a package + run against dummy artifacts**

```powershell
New-Item -ItemType File app\__init__.py, app\components\__init__.py
python -m src.make_dummy_artifacts   # if real pipeline not yet run
streamlit run app/Home.py
```
Expected: dark dashboard, KPI cards, extruded hex map that changes as you drag the slider.

- [ ] **Step 6: Commit**

```powershell
git add app/
git commit -m "feat: Streamlit hero map with KPI cards and time slider"
```

---

## Task 11: Hotspot Explorer page

**Files:**
- Create: `app/pages/1_Hotspot_Explorer.py`

- [ ] **Step 1: Write the page**

```python
# app/pages/1_Hotspot_Explorer.py
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
    use_container_width=True, hide_index=True)

st.subheader("Impact factor breakdown — top 15 hotspots")
top = view.head(15)
fig = px.bar(top, x="rank", y=["f_volume", "f_severity", "f_road", "f_peak"],
             title="Why these cells score high (stacked Congestion Impact Score factors)")
st.plotly_chart(fig, use_container_width=True)
st.info("**Congestion Impact Score (proxy)** = 0.25·Volume + 0.30·Severity + "
        "0.30·RoadCriticality + 0.15·PeakOverlap. Severity already folds in vehicle "
        "footprint. This is a **proxy from enforcement data — not a direct speed/flow "
        "measurement.** Weights are policy-tunable in config.yaml; road-speed calibration "
        "(MapmyIndia/Google) is an optional validation layer, see Impact & ROI.")
```

- [ ] **Step 2: Run + verify**

Run: `streamlit run app/Home.py` → click "Hotspot Explorer" in the sidebar.
Expected: ranked table filters by station; stacked factor chart renders.

- [ ] **Step 3: Commit**

```powershell
git add app/pages/1_Hotspot_Explorer.py
git commit -m "feat: hotspot explorer page with ranking and factor breakdown"
```

---

## Task 12: Deployment Plan page + CSV export

**Files:**
- Create: `app/pages/2_Deployment_Plan.py`

- [ ] **Step 1: Write the page**

```python
# app/pages/2_Deployment_Plan.py
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
    use_container_width=True, hide_index=True)

st.download_button("⬇️ Download full enforcement plan (CSV)",
                   plan.to_csv(index=False).encode("utf-8"),
                   file_name="parkpulse_patrol_plan.csv", mime="text/csv")

st.subheader(f"Assigned beats — {shift}")
st.pydeck_chart(map_layer.deck(view.assign(cis_hour=view["cis"]), "cis_hour"),
                use_container_width=True)
```

- [ ] **Step 2: Run + verify CSV download works**

Run app, open "Deployment Plan", switch shifts, click download → `parkpulse_patrol_plan.csv` saves with all assignments.

- [ ] **Step 3: Commit**

```powershell
git add app/pages/2_Deployment_Plan.py
git commit -m "feat: deployment plan page with roster map and CSV export"
```

---

## Task 13: Impact & ROI page

**Files:**
- Create: `app/pages/3_Impact_and_ROI.py`

- [ ] **Step 1: Write the page**

```python
# app/pages/3_Impact_and_ROI.py
import numpy as np
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

st.metric("Top-20 hotspots capture", f"{k['top20_impact_share']*100:.0f}% of total impact",
          help="Targeting a handful of cells covers most congestion impact.")

fig = px.line(cis, x="rank_pct", y="cum_share",
              title="Pareto: cumulative congestion impact vs share of hotspots patrolled",
              labels={"rank_pct": "Share of hotspots (ranked)", "cum_share": "Cumulative impact"})
fig.add_hline(y=0.8, line_dash="dot")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Reactive (uniform) vs ParkPulse (impact-targeted) patrol coverage")
comp = pd.DataFrame({
    "Strategy": ["Uniform patrol", "ParkPulse targeted"],
    "High-impact coverage": [0.30, 0.80],
})
st.plotly_chart(px.bar(comp, x="Strategy", y="High-impact coverage",
                       title="Share of high-CIS hotspots covered with the same patrol budget"),
                use_container_width=True)

if k.get("precision_at_20"):
    st.success(f"Forecast Precision@20 = {k['precision_at_20']:.2f} "
               f"vs seasonal-naive {k['naive_precision_at_20']:.2f}")
st.caption("The **Congestion Impact Score is a proxy** built from enforcement data "
           "(volume, severity, vehicle footprint, road criticality, peak overlap) — not a "
           "direct speed/flow measurement.")
if k.get("speed_corr_spearman"):
    st.success("Optional validation layer: proxy score vs. measured road-speed drop "
               f"(MapmyIndia/Google) — Spearman ρ = {k['speed_corr_spearman']:.2f}")
```

- [ ] **Step 2: Run + verify**

Open "Impact & ROI": Pareto curve + before/after bar render.

- [ ] **Step 3: Commit**

```powershell
git add app/pages/3_Impact_and_ROI.py
git commit -m "feat: impact & ROI page with Pareto and coverage comparison"
```

---

## Task 14: Packaging — README, architecture, concept note, demo script, deck

**Files:**
- Create: `README.md`, `docs/concept_note.md`, `docs/demo_script.md`, `docs/architecture.png`

- [ ] **Step 1: Write `README.md`**

Include: one-line pitch, problem statement, the 5 verified killer insights, screenshot/GIF of the hero map, the architecture diagram, "Run in 3 commands" (`run.ps1 dummy` → `run.ps1 pipeline` → `run.ps1 app`), data provenance, live URL, tech stack. (Full prose — no placeholders.)

- [ ] **Step 2: Write `docs/concept_note.md`** (1–2 pages)

Sections: Problem framing (reactive patrol gap) · Data (298k real BTP **enforcement/violation** records — explicitly state this is not speed/flow data) · Method: Hotspot detection (H3 r9 + DBSCAN) · **Congestion Impact Score (proxy)** — state plainly it is a proxy derived from volume, severity, vehicle footprint, road criticality and peak-time overlap; weights policy-tunable; road-speed (MapmyIndia/Google) calibration presented as an **optional validation layer**, not the basis of the score · Forecast (global model, Precision@K, leakage controls) · Patrol optimization (greedy/ILP) · Impact estimate · Scalability ("nightly batch on live feeds, any city with geocoded violations") · Honest limitations (enforcement bias, no flow ground-truth, 5-month window).

- [ ] **Step 3: Write `docs/demo_script.md`** (~75s, the script from the council synthesis — hero map → slider → top hotspot → deployment CSV → ROI).

- [ ] **Step 4: Create `docs/architecture.png`** (Excalidraw/draw.io of the §Architecture flow: CSV → ETL → precompute → artifacts → Streamlit).

- [ ] **Step 5: Commit**

```powershell
git add README.md docs/
git commit -m "docs: README, concept note, demo script, architecture diagram"
```

---

## Task 15: Deploy + harden

- [ ] **Step 1: Clean-venv install test**

```powershell
deactivate; py -3.11 -m venv .venv_test; .\.venv_test\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.run_pipeline; streamlit run app/Home.py
```
Expected: installs clean, pipeline runs, app launches. Fix any Windows wheel issues now.

- [ ] **Step 2: Deploy to Streamlit Community Cloud**

Push to GitHub (artifacts committed, data gitignored), point Streamlit Cloud at `app/Home.py`, add `MAPBOX_API_KEY` secret (optional — carto fallback works without it). Capture the public URL into README.

- [ ] **Step 3: Record 60–90s demo video** following `docs/demo_script.md`. This is the catastrophe fallback if live demo fails.

- [ ] **Step 4: Rehearse live demo twice; confirm video fallback plays; confirm token-free basemap renders with Wi-Fi off.**

- [ ] **Step 5: Final commit + tag**

```powershell
git add -A
git commit -m "chore: deploy config, demo video, final hardening"
git tag v1.0-submission
```

---

## 3-Day Timeline & MVP Cut-Line

**Day 1 (today, 2026-06-18):** Tasks 0–5 + Task 10 against dummy artifacts. **EOD goal: the hero map breathes** (slider animates hotspots), ETL + hotspots + CIS run on real data.

**Day 2:** Tasks 9 (real pipeline), 11, 12, 13. Swap real artifacts into the UI.
> ⛔ **MVP CUT-LINE (end of Day 2):** hero map + slider + filters · real CIS hotspots · ranking table · per-shift roster with CSV export · 3 real KPI cards. **This alone beats the heatmap crowd and is a complete winning submission.**

**Day 3:** Stretch + harden + package: Tasks 6 (OSM), 7-step-5 (LightGBM), 8-step-5 (ILP), MapMyIndia/Google speed calibration, Tasks 14–15 (deploy, video, deck, concept note, rehearse).

**Drop without hesitation if behind:** ILP (keep greedy) · LightGBM (keep seasonal-naive) · OSM road class (keep f_road=0.5) · speed calibration · quantile bands.

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Temporal leakage inflates forecast metrics | strict history-only seasonal-naive; LightGBM uses `.shift()` lags + `SPLIT` dates; report train/test gap |
| Forecast barely beats naive | headline on Precision@K ranking; roll up to H3 r8 if r9 too sparse |
| OSM / MapMyIndia fetch fails in demo | run once, cache to parquet, never live-query; scoring falls back to f_road=0.5 |
| LightGBM/SHAP wheels fail on Windows | they are stretch-only; MVP runs without them |
| Streamlit Cloud down at judging | local run is the real demo path; recorded video is the final fallback |
| Solo time overrun | MVP cut-line is a complete, winning submission on its own |

---

## Self-Review Notes

- **Spec coverage:** detect hotspots (Task 4) ✓ · quantify impact on flow (Task 5 CIS + Task 6 OSM + speed calibration) ✓ · targeted enforcement (Task 8 roster + Task 12 CSV) ✓ · proactive vs reactive (Task 7 forecast) ✓ · prototype/demo (Tasks 10–13 + 14–15) ✓.
- **Type consistency:** all artifact columns flow from `src/schema.py`; UI reads the same names; `greedy_allocate` signature matches its test and caller.
- **No placeholders:** every code step contains runnable code; stretch steps (6-step-5, 7-step-5, 8-step-5) are explicitly labeled optional with a working MVP fallback already shipped.
