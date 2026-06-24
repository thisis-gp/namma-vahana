from fastapi import APIRouter

from backend.config import IS_PRODUCTION, get_db_path
from backend.database import session
from backend.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    with session() as con:
        hotspots = con.execute("SELECT COUNT(*) FROM hotspots").fetchone()[0]
        kpis = con.execute("SELECT 1 FROM kpis WHERE id = 1").fetchone()
    ready = hotspots > 0 and kpis is not None
    if IS_PRODUCTION:
        db = "ok" if ready else "empty"
    else:
        db = f"{get_db_path()} ({hotspots} hotspots)"
    return HealthResponse(ok=ready, db=db)
