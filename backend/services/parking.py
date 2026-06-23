"""Community parking service."""
from backend.repositories import parking as repo
from backend.schemas import ParkingCreate, ParkingSpot


def list_parking(
    area: str | None = None,
    near_lat: float | None = None,
    near_lon: float | None = None,
    limit: int = 50,
) -> list[ParkingSpot]:
    return [
        ParkingSpot(**r)
        for r in repo.list_parking(area, near_lat, near_lon, limit)
    ]


def create_parking(body: ParkingCreate) -> ParkingSpot:
    return ParkingSpot(**repo.create_parking(body.model_dump()))


def vote_parking(pid: int, kind: str) -> ParkingSpot:
    row = repo.vote_parking(pid, kind)
    if not row:
        raise LookupError(f"Parking spot {pid} not found")
    return ParkingSpot(**row)
