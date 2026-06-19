# 🅿️ ParkPulse — Parking-Congestion Intelligence for Bengaluru Traffic Police

**Flipkart Gridlock 2.0 · Round 2 Prototype · Problem Statement PS1 (Parking-Induced Congestion)**

> Today BTP enforcement is reactive patrol on yesterday's map. **ParkPulse** detects illegal-parking
> hotspots, scores each by its **Congestion Impact (proxy)**, forecasts the next shift's hotspots, and
> hands officers an **optimized, exportable patrol roster** they can act on in the morning.

## What it does

1. **Hotspot detection** — buckets 298,443 real parking violations into H3 hexagons (res 9 ≈ 174 m) and cross-checks density with DBSCAN.
2. **Congestion Impact Score (proxy)** — ranks every cell by `0.25·Volume + 0.30·Severity + 0.30·RoadCriticality + 0.15·PeakOverlap`. Severity folds in violation type + vehicle footprint.
   *This is a proxy from enforcement data — not a direct speed/flow measurement. Road-speed (MapmyIndia/Google) calibration is an optional validation layer.*
3. **Next-shift forecast** — a seasonal-naive (weekday × shift) model predicts tomorrow's hotspot intensity per cell.
4. **Patrol optimizer** — greedily allocates N units per shift to the highest `intensity × impact` cells, exported as a CSV roster.
5. **Dashboard** — Streamlit + pydeck: animated 3D hotspot map, hotspot explorer, deployment plan, impact/ROI.

## Verified insights from the data

- **Top-20 hotspots ≈ 34.5%** of total congestion impact → "fix a handful of junctions, not 300."
- **Only ~0.2%** of enforcement happens in the 17:00–22:00 evening shift → the congestion peak is essentially un-enforced.
- **711 chronic repeat offenders** (≥10 violations each).
- Two-wheelers dominate counts; commercial vehicles dominate *impact* — the score re-ranks accordingly.

## Run it (3 steps)

```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# place the dataset at data/raw/violations.csv, then:
.\run.ps1 pipeline   # builds artifacts/ from the raw CSV
.\run.ps1 app        # launches the dashboard at http://localhost:8501
```

`.\run.ps1 test` runs the unit tests.

## Architecture

```
data/raw/violations.csv (298k rows)
   → src/etl.py        (UTC→IST, explode violation JSON, H3-tag, validation-tier)
   → src/hotspots.py   (H3 aggregation + DBSCAN cross-check)
   → src/scoring.py    (Congestion Impact Score proxy + hourly heat)
   → src/forecast.py   (seasonal-naive next-shift forecast + Precision@K)
   → src/optimizer.py  (greedy patrol allocation)
   → src/kpis.py       (headline numbers)
   → artifacts/*.parquet + kpis.json   (small serving layer)
   → app/ (Streamlit + pydeck reads only artifacts — zero heavy compute at demo time)
```

The batch pipeline writes tiny Parquet artifacts; the dashboard only reads them, so the live demo never lags. Re-run the pipeline nightly on new violation feeds — the same design scales to any city with geocoded violation data.

## Data

Bengaluru Traffic Police parking-violation records, Nov 2023 – Apr 2024 — 298,443 rows, 54 stations, fully geocoded. `data/` is gitignored.

## Tech stack

Python 3.14 · pandas · pyarrow · h3 · scikit-learn (DBSCAN) · Streamlit · pydeck (deck.gl) · plotly · pytest.
Stretch (not required for the MVP): LightGBM forecast, PuLP/ILP optimizer, OSMnx road class, MapmyIndia/Google speed calibration.

## Honest limitations

Enforcement data reflects *where police ticketed*, not all violations; the impact score is a proxy, not measured flow; the window is 5 months (no full-year seasonality). These are stated openly in the dashboard and concept note.

## Docs

- Problem statements & dataset profiles: `docs/HACKATHON.md`
- Full implementation plan: `docs/superpowers/plans/2026-06-18-parkpulse.md`
