# ParkPulse — Concept Note

**Flipkart Gridlock 2.0 · Round 2 · Problem Statement 1 (Parking-Induced Congestion)**

## The problem
On-street illegal parking chokes Bengaluru's carriageways and junctions. The Traffic Police logged **298,443 parking violations in ~5 months** — but enforcement is **reactive and patrol-based**: there's no view of which illegal parking actually hurts traffic flow, and no way to prioritise where limited patrols should go. Effort is spread thin; the real chokepoints stay jammed.

## Our solution
**ParkPulse** turns the raw violation log into an operating tool that tells officers **where and when to patrol next**, and **proves** the plan beats today's approach.

1. **Detect** — cluster all violations into H3 map cells (~174 m) with a DBSCAN cross-check → 2,532 active hotspots.
2. **Score impact (proxy)** — rank each hotspot by a **Congestion Impact Score**: violation volume + severity (violation type × vehicle footprint) + road criticality (parsed from the address text) + rush-hour overlap. *It is an honest proxy from enforcement data — not a measured speed/flow figure.*
3. **Correct timing bias** — raw timestamps are ~86% "night" on the UTC clock (a recording artifact). A **Location Quotient** correction surfaces each hotspot's genuine peak window.
4. **Forecast** — a cell-level **LightGBM** model predicts the next shift's worst hotspots (**Precision@20 = 0.85 vs 0.75 naive**, held-out); a station-level **Negative Binomial** model gives explainable next-week baselines with 95% intervals (counts are heavily overdispersed, so NB not Poisson).
5. **Deploy** — a greedy optimiser turns the forecast into a downloadable **patrol roster** (where, when, how many units), grouped by station.
6. **Prove (the outcome)** — backtested on held-out days: with the **same patrol budget**, ParkPulse covers **~23% of next-day congestion impact vs ~10% for reactive "chase-yesterday" patrol — +13 percentage points.**

## Two audiences
- **Police** — station-scoped dashboards: priority map, hotspot detail (with plain-language summary, severity, intervention type, confidence flag), forecast + live event surge overlay, deployment roster, repeat-offender watchlist.
- **Citizen** — a public "parking risk guide": where and when enforcement is concentrated, in plain language.

## Why it's defensible (and honest)
- **No external data** — every signal is derived from the provided CSV (road type from the `location` text, not OSM), per the rules.
- **Proxy, not measurement** — the impact score is labelled a proxy everywhere; we never claim to measure traffic speed.
- **Stated caveats** — logging-time bias (corrected via LQ), 100%-null closure timestamps (no response-time claims), `device_id` is a coverage proxy not headcount, and hotspots with high data-correction rates are flagged ⚠️ lower-confidence.
- **Repeat-offender ratio** distinguishes spots needing *targeted enforcement* (chronic offenders) from those needing an *infrastructure/signage fix*.

## Impact & scalability
Same officers, smarter placement → more congestion cleared per patrol-hour, proactively. The pipeline is a nightly batch that writes small artifacts the dashboard serves instantly; it extends to any city with geocoded violation data — zero retraining of the workflow.

## Key numbers (from the real data)
298,443 records · 54 stations · 2,532 hotspots · top-20 hotspots ≈ 34% of total impact · 711 chronic repeat offenders · forecast Precision@20 0.85 · **+13 pp enforcement uplift**.
