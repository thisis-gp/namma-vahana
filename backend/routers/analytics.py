from fastapi import APIRouter, HTTPException, Query

from backend.schemas import (
    Backtest, Citizen, Hotspot, Kpis, NbForecast, Patrol, Station, Watch,
)
from backend.services import analytics as svc

router = APIRouter(tags=["analytics"])


@router.get("/kpis", response_model=Kpis)
def kpis() -> Kpis:
    try:
        return svc.get_kpis()
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/hotspots", response_model=list[Hotspot])
def hotspots(
    station: str | None = None,
    limit: int | None = Query(None, ge=1, le=5000),
) -> list[Hotspot]:
    try:
        return svc.get_hotspots(station, limit)
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/stations", response_model=list[Station])
def stations() -> list[Station]:
    try:
        return svc.get_stations()
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/citizen", response_model=list[Citizen])
def citizen(limit: int | None = Query(None, ge=1, le=5000)) -> list[Citizen]:
    try:
        return svc.get_citizen(limit)
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/backtest", response_model=list[Backtest])
def backtest() -> list[Backtest]:
    try:
        return svc.get_backtest()
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/nb-forecast", response_model=list[NbForecast])
def nb_forecast() -> list[NbForecast]:
    try:
        return svc.get_nb_forecast()
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/patrol", response_model=list[Patrol])
def patrol(
    station: str | None = None,
    shift: str | None = None,
) -> list[Patrol]:
    try:
        return svc.get_patrol(station, shift)
    except LookupError as e:
        raise HTTPException(503, str(e)) from e


@router.get("/watchlist", response_model=list[Watch])
def watchlist(
    limit: int = Query(60, ge=1, le=500),
    station: str | None = None,
) -> list[Watch]:
    try:
        return svc.get_watchlist(limit, station)
    except LookupError as e:
        raise HTTPException(503, str(e)) from e
