# Flipkart Gridlock 2.0 — Hackathon Reference

> Single source of truth for the hackathon: structure, all three Round-2 problem statements, datasets, judging criteria, and our chosen direction.

## Overview

- **Event:** Gridlock Hackathon 2.0 — Flipkart × Bengaluru Traffic Police (BTP), with MapmyIndia as a partner.
- **Theme:** Design AI models that classify congestion, detect violations, identify movement patterns, and support smarter mobility decisions — built on **real Bengaluru data, not simulations**.
- **Our status:** Passed Round 1; now in **Round 2 (Prototype phase)**.
- **Round 2 window:** **Jun 15–21, 2026** (online via HackerEarth). Team size: **1 (solo)**.
- **Links:**
  - HackerEarth Round 2: https://www.hackerearth.com/community/challenges/hackathon/gridlock-hackathon-20-round-2/
  - Official microsite: https://gridlock2point0.hackerearth.com/

## Phases

1. **Round 1 — Online ML challenge.** Regression: predict ride/passenger `demand` ∈ [0,1] per road segment per 15-min slot (geohash, day, timestamp, road type, lane counts, weather, landmarks; ~41,778 test rows; scored on R²). *(Completed.)*
2. **Round 2 — Prototype phase.** Pick **one of three** problem statements and build a working prototype on **real BTP data** + MapmyIndia resources.
3. **Finale — Onsite** at Flipkart HQ.

## Round 2 Constraints (rules)

- **No external data.** Solutions must be built **only on the provided dataset(s)** — no outside data sources (no OSM, no third-party APIs, no scraped data). ParkPulse complies: every signal, including the road-criticality factor, is derived from columns in the provided CSV (e.g. the `location` text and `junction_name`).
- Solo teams (1 person). Online submission via HackerEarth.

## Round 2 Judging Criteria

Expert panel (BTP + Flipkart). Evaluates:
- **Feasibility** — can it realistically be built/deployed?
- **Relevance to Bengaluru** — does it address the city's actual traffic reality?
- **Innovation** — novel, non-obvious approach.
- **Real-world impact** — measurable benefit to enforcement/mobility.
- **Scalability** — extends beyond the demo / to other zones or cities.
- **Prototype clarity** — is the demo clear and convincing?

Submission should include: a working prototype, plus (for idea-style statements) a **concept note / prototype proposal / solution framework**.

---

## The Three Round-2 Problem Statements

### PS1 — Poor Visibility on Parking-Induced Congestion ✅ (OUR CHOICE)

**Operational challenge:** On-street illegal parking and spillover parking near commercial areas, metro stations, and events choke carriageways and intersections.

**Why it's hard today:**
- Enforcement is patrol-based and reactive.
- No heatmap of parking violations vs. congestion impact.
- Difficult to prioritize enforcement zones.

**Problem statement direction:** *How can AI-driven parking intelligence detect illegal parking hotspots and quantify their impact on traffic flow to enable targeted enforcement?*

**Dataset:** `C:\Users\am400\Downloads\jan to may police violation_anonymized791b166.csv`

---

### PS2 — Event-Driven Congestion (Planned & Unplanned)

**Operational challenge:** Political rallies, festivals, sports events, construction, and sudden gatherings create localized traffic breakdowns.

**Why it's hard today:**
- Event impact is not quantified in advance.
- Resource deployment is experience-driven.
- No post-event learning system.

**Problem statement direction:** *How can historical and real-time data be used to forecast event-related traffic impact and recommend optimal manpower, barricading, and diversion plans?*

**Dataset:** `C:\Users\am400\Downloads\Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv`

---

### PS3 — Automated Photo Identification & Classification for Traffic Violations Using Computer Vision

**Overview:** Submit a unique, practical idea (concept note / prototype proposal / solution framework). With increasing traffic-camera deployment, manual inspection of violation images is labor-intensive and inconsistent. Build a CV system that processes traffic images, detects vehicles/road users, identifies and classifies violations, and generates annotated evidence — robust to varying environment, density, and image quality.

**Tasks:**
- **Image preprocessing** — enhance quality; handle low light, rain, shadows, motion blur.
- **Vehicle & road-user detection** — localize vehicles/riders/drivers/pedestrians; classify vehicle categories.
- **Violation detection** — helmet non-compliance, seatbelt non-compliance, triple riding, wrong-side driving, stop-line violation, red-light violation, illegal parking.
- **Violation classification** — categorize into predefined classes; assign confidence scores.
- **License-plate recognition** — detect plates; extract registration via OCR.
- **Evidence generation** — annotated images; store violation metadata + timestamps.
- **Analytics & reporting** — statistics, trends, searchable records, summaries.
- **Performance evaluation** — Accuracy, Precision, Recall, F1, mAP; computational efficiency & scalability.

**Expected outcome:** A scalable AI traffic-image analysis system that automatically identifies, classifies, and documents violations from photographic evidence.

**Dataset:** None provided (source public datasets).

---

## Dataset Profiles (verified against the files)

### PS1 dataset — Police parking violations
- **Path:** `C:\Users\am400\Downloads\jan to may police violation_anonymized791b166.csv`
- **Size/shape:** ~104 MB, **298,450 rows**, 24 columns.
- **Date range:** **2023-11-09 → 2024-04-08**.
- **Timestamps:** stored in **UTC (`+00`)** → must convert to IST (+5:30) for time-of-day analysis.
- **Content:** 100% parking violations. Every row geocoded (valid lat/lon inside Bengaluru bbox 12.80–13.29 N, 77.44–77.77 E).
- **Key columns:** `id, latitude, longitude, location, vehicle_number, vehicle_type, description (mostly NULL), violation_type (JSON-array string), offence_code, created_datetime, closed_datetime, modified_datetime, device_id, created_by_id, center_code, police_station, junction_name, validation_status, updated_vehicle_number, updated_vehicle_type, ...`
- **vehicle_type (top):** SCOOTER 94,856 · CAR 88,870 · MOTOR CYCLE 40,811 · PASSENGER AUTO 37,813 · MAXI-CAB 11,372 · LGV 8,255 ...
- **violation_type (top):** `["WRONG PARKING"]` 138,764 · `["NO PARKING"]` 119,576 · plus MAIN ROAD / FOOTPATH / NEAR BUSTOP / DOUBLE PARKING / NEAR ROAD CROSSING combos (27 subtypes, ~13% multi-label).
- **police_station (top):** Upparpet 34,468 · Shivajinagar 28,044 · Malleshwaram 22,200 · HAL Old Airport 20,819 · City Market 17,646 ... (54 stations total).
- **junction_name:** 150,570 rows carry a real BTP-coded junction (top: Safina Plaza 15,449 · KR Market 11,538 · Elite 10,718).
- **validation_status:** NULL 125,254 · approved 115,400 · rejected 49,754 · created1 7,044 · processing 678 · duplicate 320.

### PS2 dataset — Astram event data
- **Path:** `C:\Users\am400\Downloads\Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv`
- **Size/shape:** ~4.3 MB, **8,173 rows**, 45 columns.
- **Date range:** 2023-11-09 → 2024-04-08.
- **event_type:** unplanned 7,706 · planned 467.
- **event_cause (top):** vehicle_breakdown 4,896 · others 638 · pot_holes 537 · construction 480 · water_logging 458 · accident 365 · tree_fall 284 · ... · public_event 84 · procession 72 · vip_movement 20 · protest 15.
- **requires_road_closure:** FALSE 7,497 · TRUE 676.
- **status:** closed 7,095 · active 1,007 · resolved 71. **Only 490 rows have an end time** → durations mostly missing.
- **priority:** High 5,030 · Low 3,141.
- **Notes:** free-text descriptions partly in Kannada; many NULL columns. Weak fit for forecasting (planned events <3%, sparse labels).

---

## Decision & Rationale

**Chosen: PS1 (Parking-Induced Congestion).**

For a **solo participant with ~3 days**, PS1 wins on every practical axis:
- **Best data** — 298k rows, 100% relevant, fully geocoded, in BTP's own junction taxonomy.
- **Finishable** — clear, demoable artifact; lowest technical risk.
- **Undeniably about Bengaluru** — real BTP records (PS3 would use generic public data; PS2's data is sparse for what it asks).
- **Differentiation by execution depth** (beats the "everyone picks P1/P2" crowd):
  1. A defensible **Congestion Impact Score (proxy)** — honestly framed as derived from in-dataset signals (volume, severity, vehicle footprint, road criticality parsed from the `location` text, peak overlap), **not a direct speed/flow measurement**. Built only on the provided data (**no external data**, per rules). Naming it a proxy and stating the limitation is itself a credibility win with BTP judges.
  2. A **predictive/proactive** layer (forecast tomorrow's hotspots) — directly answers the "reactive patrol" pain point.
  3. **Quantified ROI** (targeted vs. random patrol coverage).

**Verified killer insights (pitch ammunition):**
1. A handful of junctions carry the load (Safina Plaza, KR Market, Elite) → "fix 15 junctions, not 300."
2. Enforcement collapses exactly when congestion peaks (logged 08:00–12:00 IST, craters at the 17:00–20:00 evening peak).
3. 711 chronic repeat offenders (≥10 violations; one vehicle 55 times).
4. Two-wheelers dominate counts; commercial vehicles dominate *impact* — the impact score re-ranks accordingly.
5. Data already uses BTP junction codes → zero-translation deployment.

**Product:** **ParkPulse** — detects hotspots (H3), scores congestion impact, forecasts tomorrow's hotspots, and outputs an optimized, downloadable patrol roster, in a polished Streamlit + pydeck dashboard.

**Implementation plan:** `docs/superpowers/plans/2026-06-18-parkpulse.md`
