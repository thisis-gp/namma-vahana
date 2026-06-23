"""Operations service — challans, assignments, and citizen reports."""
from backend.repositories import operations as repo
from backend.schemas import (
    Assignment,
    AssignmentUpsert,
    Challan,
    ChallanCreate,
    ChallanUpdate,
    LeaderEntry,
    Report,
    ReportAction,
    ReportCreate,
)


def list_challans(station: str | None = None, vehicle: str | None = None) -> list[Challan]:
    return [Challan(**r) for r in repo.list_challans(station, vehicle)]


def create_challan(body: ChallanCreate) -> Challan:
    return Challan(**repo.create_challan(body.model_dump(exclude_none=True)))


def update_challan(cid: str, body: ChallanUpdate) -> Challan:
    row = repo.update_challan(cid, body.model_dump(exclude_none=True))
    if not row:
        raise LookupError(f"Challan {cid} not found")
    return Challan(**row)


def list_assignments(station: str | None = None) -> list[Assignment]:
    return [Assignment(**r) for r in repo.list_assignments(station)]


def upsert_assignment(body: AssignmentUpsert) -> Assignment:
    return Assignment(**repo.upsert_assignment(body.model_dump()))


def list_reports(status: str | None = None, reporter: str | None = None) -> list[Report]:
    return [Report(**r) for r in repo.list_reports(status, reporter)]


def create_report(body: ReportCreate) -> Report:
    return Report(**repo.create_report(body.model_dump()))


def act_on_report(rid: int, body: ReportAction) -> Report:
    row = repo.act_on_report(rid, body.action, body.officer)
    if not row:
        raise LookupError(f"Report {rid} not found")
    return Report(**row)


def leaderboard(limit: int = 10) -> list[LeaderEntry]:
    return [LeaderEntry(**r) for r in repo.leaderboard(limit)]
