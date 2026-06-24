"""Shared FastAPI factory — local uses /api prefix; Vercel api/ mount uses none."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS, IS_PRODUCTION
from backend.database import init_db
from src.db_export import ensure_analytics_loaded
from backend.routers import analytics_router, health_router, operations_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    ensure_analytics_loaded()
    yield


def create_app(api_prefix: str = "/api") -> FastAPI:
    app = FastAPI(
        title="Namma Vahana API",
        description="Smart parking intelligence for Namma Bengaluru",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if IS_PRODUCTION else "/docs",
        redoc_url=None if IS_PRODUCTION else "/redoc",
        openapi_url=None if IS_PRODUCTION else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    prefix = api_prefix.rstrip("/")
    app.include_router(health_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(operations_router, prefix=prefix)
    return app
