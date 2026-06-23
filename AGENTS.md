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

## Cursor Cloud specific instructions

The startup update script already creates `.venv` and installs Python + web deps. `run.ps1` is PowerShell-only; on Linux run the underlying commands directly. Python deps live in the repo `.venv` (activate with `source .venv/bin/activate`, or call `.venv/bin/<tool>` directly).

Three services, brought up in this order:

1. **Build serving DB (required, run once before the backend):** `source .venv/bin/activate && PYTHONPATH=. python -m src.db_export`. This reads the committed `artifacts/*.parquet` and writes `data/parkpulse.db`. The backend's analytics endpoints (`/api/kpis`, `/api/hotspots`, etc.) return empty until this runs. `data/` is gitignored, so re-run it if `data/parkpulse.db` is missing. The full pipeline (`python -m src.run_pipeline`) is NOT runnable here — it needs `data/raw/violations.csv` (298k rows, gitignored, absent); use the committed artifacts instead.
2. **Backend API (FastAPI, port 8000, `/api` prefix):** `source .venv/bin/activate && uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`. Health check: `GET http://127.0.0.1:8000/api/health`. Startup auto-creates schema and seeds operational tables (challans/reports/parking/officers).
3. **Web (Next.js 16, port 3000):** `cd web && npm run dev`. The browser talks to the backend via `NEXT_PUBLIC_API_BASE`; there is no Next.js proxy/rewrite, so client fetches default to same-origin and 404 unless this is set. `web/.env.local` with `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` is required for the UI to load data (gitignored; recreate if missing).

Gotchas:
- `requirements.txt` historically pinned an invalid `starlette==1.3.1` (conflicts with `fastapi==0.128.0`, needs `starlette<0.51.0`). Corrected to `0.50.0`; the update script also strips any `starlette==` pin and lets fastapi resolve a compatible version, so it stays robust if that fix is unmerged.
- Tests: `PYTHONPATH=. pytest -q` (from repo root, venv active). Web lint: `cd web && npm run lint` — note it currently reports pre-existing `react-hooks` errors in app code unrelated to setup.
- System package `python3.12-venv` is required for venv creation (provided by the VM snapshot, not the update script).
