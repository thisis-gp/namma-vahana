## Learned User Preferences

- Prioritize a stunning, attention-grabbing hero/landing animation — avoid cluttered or static visuals.
- Prefer real Bengaluru geography on the hero map (MapLibre/deck.gl), with Google Maps–style motion (patrol routes, parking, traffic) when it stays readable.
- Favor modern, minimal, elegant UI/UX suited to a hackathon demo — user repeatedly rejects busy or unclear interfaces.
- Homepage should surface features with clear dual entry paths: one flow for police/officers and one for citizens/residents.
- Product branding is **Namma Vahana** (not ParkPulse); keep name, logo, and copy consistent.

## Learned Workspace Facts

- **Namma Vahana** — Flipkart Gridlock 2.0 hackathon prototype for Bengaluru parking congestion (PS1); tagline “Smart parking for Namma Bengaluru”.
- Monorepo layout: Next.js 16 app in `web/`, FastAPI API in `backend/`, batch pipeline in `src/`; officer map uses MapLibre + deck.gl.
- GitHub canonical repo: https://github.com/thisis-gp/namma-vahana (excludes local `data/`, `*.db`, `*.csv`, `cache/`, `web/node_modules/`, `web/.next/` per `.gitignore`).
- Hero/landing map components live under `web/components/landing/` (e.g. `CityMap`, `HeroMapDeck`, deck.gl layers).
- Brand constants centralized in `web/lib/brand.ts` (`Logo`, storage keys, tagline).
- Python pipeline writes artifacts consumed by backend; `.\run.ps1 pipeline` then `.\run.ps1 backend` for API; Next.js frontend via `cd web && npm run dev`.
