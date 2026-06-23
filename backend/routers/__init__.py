"""API routers."""
from backend.routers.analytics import router as analytics_router
from backend.routers.health import router as health_router
from backend.routers.operations import router as operations_router

__all__ = ["analytics_router", "health_router", "operations_router"]
