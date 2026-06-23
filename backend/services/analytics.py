"""Analytics service — thin validation layer over repository."""
from backend.repositories import analytics as repo
from backend.schemas import (
    Backtest, Citizen, Hotspot, Kpis, NbForecast, Patrol, Station, Watch,
)


def get_kpis() -> Kpis:
    data = repo.get_kpis()
    if not data:
        raise LookupError("KPIs not loaded — run the pipeline first")
    return Kpis(**data)


def get_hotspots(station: str | None = None, limit: int | None = None) -> list[Hotspot]:
    return [Hotspot(**r) for r in repo.list_hotspots(station, limit)]


def get_stations() -> list[Station]:
    return [Station(**r) for r in repo.list_stations()]


def get_citizen(limit: int | None = None) -> list[Citizen]:
    return [Citizen(**r) for r in repo.list_citizen(limit)]


def get_backtest() -> list[Backtest]:
    return [Backtest(**r) for r in repo.list_backtest()]


def get_nb_forecast() -> list[NbForecast]:
    return [NbForecast(**r) for r in repo.list_nb_forecast()]


def get_patrol(station: str | None = None, shift: str | None = None) -> list[Patrol]:
    return [Patrol(**r) for r in repo.list_patrol(station, shift)]


def get_watchlist(limit: int = 60, station: str | None = None) -> list[Watch]:
    return [Watch(**r) for r in repo.list_watchlist(limit, station)]
