from fastapi import APIRouter, HTTPException, Query

from backend.schemas import (
    Assignment,
    AssignmentUpsert,
    Challan,
    ChallanCreate,
    ChallanUpdate,
    LeaderEntry,
    Officer,
    OfficerAssign,
    ParkingCreate,
    ParkingSpot,
    ParkingVote,
    Report,
    ReportAction,
    ReportCreate,
    StationSummary,
)
from backend.services import operations as svc
from backend.services import officers as officers_svc
from backend.services import parking as parking_svc

router = APIRouter(tags=["operations"])


@router.get("/challans", response_model=list[Challan])
def list_challans(
    station: str | None = None,
    vehicle: str | None = None,
) -> list[Challan]:
    return svc.list_challans(station, vehicle)


@router.post("/challans", response_model=Challan, status_code=201)
def create_challan(body: ChallanCreate) -> Challan:
    return svc.create_challan(body)


@router.patch("/challans/{cid}", response_model=Challan)
def patch_challan(cid: str, body: ChallanUpdate) -> Challan:
    if not body.model_dump(exclude_none=True):
        raise HTTPException(400, "no editable fields")
    try:
        return svc.update_challan(cid, body)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/assignments", response_model=list[Assignment])
def list_assignments(station: str | None = None) -> list[Assignment]:
    return svc.list_assignments(station)


@router.put("/assignments", response_model=Assignment)
def upsert_assignment(body: AssignmentUpsert) -> Assignment:
    return svc.upsert_assignment(body)


@router.get("/reports", response_model=list[Report])
def list_reports(
    status: str | None = None,
    reporter: str | None = None,
) -> list[Report]:
    return svc.list_reports(status, reporter)


@router.post("/reports", response_model=Report, status_code=201)
def create_report(body: ReportCreate) -> Report:
    return svc.create_report(body)


@router.patch("/reports/{rid}", response_model=Report)
def act_on_report(rid: int, body: ReportAction) -> Report:
    try:
        return svc.act_on_report(rid, body)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/leaderboard", response_model=list[LeaderEntry])
def leaderboard(limit: int = Query(10, ge=1, le=100)) -> list[LeaderEntry]:
    return svc.leaderboard(limit)


@router.get("/parking", response_model=list[ParkingSpot])
def list_parking(
    area: str | None = None,
    near_lat: float | None = None,
    near_lon: float | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[ParkingSpot]:
    return parking_svc.list_parking(area, near_lat, near_lon, limit)


@router.post("/parking", response_model=ParkingSpot, status_code=201)
def create_parking(body: ParkingCreate) -> ParkingSpot:
    return parking_svc.create_parking(body)


@router.post("/parking/{pid}/vote", response_model=ParkingSpot)
def vote_parking(pid: int, body: ParkingVote) -> ParkingSpot:
    try:
        return parking_svc.vote_parking(pid, body.kind)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/officers", response_model=list[Officer])
def list_officers(station: str | None = None) -> list[Officer]:
    return officers_svc.list_officers(station)


@router.patch("/officers/{oid}", response_model=Officer)
def assign_officer(oid: int, body: OfficerAssign) -> Officer:
    try:
        return officers_svc.assign_officer(oid, body.model_dump(exclude_none=True))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/station-summary", response_model=StationSummary)
def station_summary(station: str) -> StationSummary:
    try:
        return officers_svc.station_summary(station)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
