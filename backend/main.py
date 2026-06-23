"""Namma Vahana FastAPI application — layered SDE architecture.

Layers:
  routers/     → HTTP endpoints
  services/    → business logic + validation
  repositories/→ SQL data access
  schemas/     → Pydantic API contracts
  database.py  → connection + migrations

Run:
    python -m backend.main
    # or: .\\run.ps1 backend
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.database import init_db
from backend.repositories.operations import seed_challans_if_empty, seed_reports_if_empty
from backend.repositories.parking import seed_parking_if_empty
from backend.repositories.officers import seed_officers_if_empty
from backend.routers import analytics_router, health_router, operations_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_challans_if_empty()
    seed_reports_if_empty()
    seed_parking_if_empty()
    seed_officers_if_empty()
    yield


app = FastAPI(
    title="Namma Vahana API",
    description="Smart parking intelligence for Namma Bengaluru — hotspots, patrol plans, and resident tools",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(operations_router)


def main() -> None:
    import uvicorn

    from backend.config import HOST, PORT

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
