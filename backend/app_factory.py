"""Shared FastAPI factory — local uses /api prefix; Vercel api/ mount uses none."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.database import init_db
from backend.repositories.officers import seed_officers_if_empty
from backend.repositories.operations import seed_challans_if_empty, seed_reports_if_empty
from backend.repositories.parking import seed_parking_if_empty
from backend.routers import analytics_router, health_router, operations_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_challans_if_empty()
    seed_reports_if_empty()
    seed_parking_if_empty()
    seed_officers_if_empty()
    yield


def create_app(api_prefix: str = "/api") -> FastAPI:
    app = FastAPI(
        title="Namma Vahana API",
        description="Smart parking intelligence for Namma Bengaluru",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = api_prefix.rstrip("/")
    app.include_router(health_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(operations_router, prefix=prefix)
    return app
