from fastapi import APIRouter

from backend.config import get_db_path
from backend.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(db=str(get_db_path()))
