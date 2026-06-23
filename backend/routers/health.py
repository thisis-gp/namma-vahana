from fastapi import APIRouter

from backend.config import IS_PRODUCTION, get_db_path
from backend.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        db="ok" if IS_PRODUCTION else str(get_db_path()),
    )
