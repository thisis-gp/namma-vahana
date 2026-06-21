# ParkPulse — Pitch Deck (slide-by-slide)

Build these as 10 slides (Google Slides / PowerPoint). Each slide = the heading + the bullets/visual noted. Keep ~15 words per bullet. Dark theme, orange accent (#FF5A1F).

---

### Slide 1 — Title
**🅿️ ParkPulse**
*Where & when to patrol tomorrow to clear the most traffic-choking illegal parking.*
Flipkart Gridlock 2.0 · Round 2 · PS1 · [team name]
Visual: the 3D hotspot map screenshot.

### Slide 2 — The problem
- 298,443 illegal-parking violations in ~5 months in Bengaluru.
- Enforcement is **reactive** (chase yesterday) and patrol-based.
- No view of **which** illegal parking actually chokes traffic.
- Limited patrols spread thin → real chokepoints stay jammed.

### Slide 3 — Our idea (one line)
**Detect hotspots → score traffic impact → forecast tomorrow → deploy patrols → prove it works.**
Visual: the 5-step flow.

### Slide 4 — The data (real, in-dataset only)
- 298K geocoded Bengaluru Police records · 54 stations · Nov 2023–Apr 2024.
- **No external data** — every signal from the provided CSV (rules-compliant).
- Honest prep: UTC→IST, JSON violation parsing, validation tiers.

### Slide 5 — Congestion Impact Score (proxy)
- `0.25·Volume + 0.30·Severity + 0.30·RoadCriticality + 0.15·PeakOverlap`.
- Severity = violation type × vehicle footprint; road type parsed from address text.
- **Honest framing:** a proxy from enforcement data — not measured speed/flow.
- Policy-tunable weights.

### Slide 6 — Hidden timing, corrected (Location Quotient)
- Raw timestamps look ~86% "night" — a recording artifact, not real timing.
- Location Quotient reveals each hotspot's **genuine** peak window.
- Visual: before/after hourly profile.

### Slide 7 — Forecast (proactive, not reactive)
- Cell-level **LightGBM**: **Precision@20 = 0.85 vs 0.75 naive** (held-out).
- Station-level **Negative Binomial** baseline + 95% interval (overdispersion-correct).
- Live **event surge** overlay for known rallies/matches.

### Slide 8 — THE OUTCOME (hero slide)
**Same patrols, smarter placement:**
- ParkPulse covers **~23%** of next-day congestion impact vs **~10%** reactive.
- **+13 percentage points — more than double — backtested on held-out days.**
- What-if slider: marginal value of each extra patrol.
Visual: the coverage-vs-budget curve.

### Slide 9 — The product (Police + Citizen)
- **Police:** station dashboard, priority map, deployment roster (CSV), repeat-offender watchlist.
- **Citizen:** public parking-risk guide (where/when), plain language.
- Visual: two screenshots side by side.

### Slide 10 — Why we win + scale
- **Defensible:** no external data, proxy stated, caveats shown, confidence flags.
- **Proven:** outcome backtested vs the status quo — not just a heatmap.
- **Scalable:** nightly batch; any city with geocoded violations.
- Ask: pilot with one BTP division.

---

**Speaker note for Slide 8:** This is the slide that wins. Most teams stop at a heatmap of the past; we *prove* our plan beats how BTP works today, with the same headcount.
