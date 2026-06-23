"""Officer roster service."""
from backend.repositories import officers as repo
from backend.schemas import Officer, StationSummary


def list_officers(station: str | None = None) -> list[Officer]:
    return [Officer(**r) for r in repo.list_officers(station)]


def assign_officer(oid: int, patch: dict) -> Officer:
    row = repo.assign_officer(oid, patch)
    if not row:
        raise LookupError(f"Officer {oid} not updated")
    return Officer(**row)


def station_summary(station: str) -> StationSummary:
    row = repo.station_summary(station)
    if not row:
        raise LookupError(f"Station {station} not found")
    return StationSummary(**row)
