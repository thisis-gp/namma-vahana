"""Pydantic schemas — API contract layer."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool = True
    db: str
    version: str = "1.0.0"


class Kpis(BaseModel):
    total_violations: int
    confirmed_violations: int
    n_stations: int
    n_hotspots: int
    top20_impact_share: float
    evening_enforcement_share: float
    repeat_offenders: int
    repeat_offender_share: float
    precision_at_20: float
    naive_precision_at_20: float
    uplift_k: int
    parkpulse_coverage: float
    reactive_coverage: float
    uplift_pp: float
    date_min: str
    date_max: str
    overdispersion: float | None = None
    pseudo_r2: float | None = None


class Hotspot(BaseModel):
    h3: str
    lat: float
    lon: float
    priority_pct: float
    rank: int
    violation_count: int
    dominant_station: str
    junction_name: str
    display_location: str
    dominant_vehicle: str
    dominant_violation: str
    severity_10: float
    road_class: str
    intervention_type: str
    peak_hours: str
    repeat_offender_ratio: float
    confidence_flag: str
    units_recommended: int
    near_school: bool
    near_hospital: bool
    blocks_bus: bool
    nl_summary: str


class Station(BaseModel):
    police_station: str
    violations: int
    devices: int
    enforcement_gap: float
    gap_confidence: str
    units_recommended: int


class Citizen(BaseModel):
    h3: str
    lat: float
    lon: float
    junction_name: str
    display_location: str
    dominant_station: str
    fine_risk: float
    risk_band: str
    peak_hours: str
    nl_summary: str


class Backtest(BaseModel):
    k: int
    parkpulse_coverage: float
    reactive_coverage: float
    uplift_pp: float


class NbForecast(BaseModel):
    police_station: str
    forecast_next_week: float
    lower_95: float
    upper_95: float


class Patrol(BaseModel):
    shift: str
    h3: str
    junction_name: str
    display_location: str
    police_station: str
    expected_violations: float
    dominant_vehicle: str
    dominant_violation: str
    assigned_unit: str
    rank: int


class Watch(BaseModel):
    vehicle_number: str
    vehicle_type: str
    violations: int
    distinct_cells: int
    top_location: str
    top_junction: str
    severity_sum: float
    first_seen: str
    last_seen: str
    station: str | None = None        # derived: which station this offender falls under
    station_exact: bool = False       # True if from a named junction, False if inferred from area


class ChallanCreate(BaseModel):
    vehicle: str
    category: str = "Wrong Parking"
    amount: int = 1000
    status: Literal["Issued", "Paid", "Unpaid", "Disputed"] = "Issued"
    station: str = "City-wide"
    officer: str = "To be assigned"
    location: str = ""
    due: str | None = None
    evidence: str = ""
    id: str | None = None


class ChallanUpdate(BaseModel):
    status: Literal["Issued", "Paid", "Unpaid", "Disputed"] | None = None
    officer: str | None = None


class Challan(ChallanCreate):
    id: str
    created_at: str | None = None
    updated_at: str | None = None


class ReportCreate(BaseModel):
    reporter: str
    vehicle: str = ""
    category: str = "Wrong Parking"
    location: str
    note: str = ""
    lat: float | None = None
    lon: float | None = None
    image: str = ""


class ReportAction(BaseModel):
    action: Literal["verify", "reject"]
    officer: str = "Officer on duty"


class Report(BaseModel):
    id: int
    reporter: str
    vehicle: str
    category: str
    location: str
    note: str
    lat: float | None = None
    lon: float | None = None
    status: Literal["Pending", "Verified", "Rejected"]
    points: int
    challan_id: str | None = None
    image: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class LeaderEntry(BaseModel):
    reporter: str
    points: int
    verified: int
    reports: int
    badge: str


class ParkingCreate(BaseModel):
    name: str
    area: str
    lat: float | None = None
    lon: float | None = None
    kind: Literal["Roadside", "Open ground", "Building", "Pay-and-park"] = "Roadside"
    price: Literal["Free", "Paid"] = "Free"
    note: str = ""
    added_by: str = "Anonymous"
    image: str = ""


class ParkingVote(BaseModel):
    kind: Literal["up", "flag"]


class ParkingSpot(BaseModel):
    id: int
    name: str
    area: str
    lat: float | None = None
    lon: float | None = None
    kind: str
    price: str
    note: str
    added_by: str
    upvotes: int
    flags: int
    risk_band: str
    fine_risk: float | None = None
    image: str = ""
    status: str
    created_at: str | None = None
    distance_km: float | None = None


class Officer(BaseModel):
    id: int
    name: str
    badge: str | None = None
    station: str
    beat_h3: str | None = None
    area: str | None = None
    patrol_window: str | None = None
    shift: str
    target: int
    done: int
    status: str
    updated_at: str | None = None


class OfficerAssign(BaseModel):
    beat_h3: str | None = None
    area: str | None = None
    patrol_window: str | None = None
    shift: str | None = None
    status: str | None = None


class StationSummary(BaseModel):
    police_station: str
    violations: int
    devices: int
    enforcement_gap: float
    gap_confidence: str
    units_recommended: int
    officers: int
    target_total: int
    done_total: int
    forecast_next_week: float | None = None


class AssignmentUpsert(BaseModel):
    station: str
    h3: str
    shift: str
    beat_name: str
    assigned_to: str
    location: str = ""
    expected_violations: int = 0
    status: str = "Assigned"


class Assignment(AssignmentUpsert):
    id: int
    updated_at: str | None = None
