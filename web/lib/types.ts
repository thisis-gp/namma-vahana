// Mirrors backend/schemas — keep in sync with the FastAPI contract.

export interface Kpis {
  total_violations: number;
  confirmed_violations: number;
  n_stations: number;
  n_hotspots: number;
  top20_impact_share: number;
  evening_enforcement_share: number;
  repeat_offenders: number;
  repeat_offender_share: number;
  precision_at_20: number;
  naive_precision_at_20: number;
  uplift_k: number;
  parkpulse_coverage: number;
  reactive_coverage: number;
  uplift_pp: number;
  date_min: string;
  date_max: string;
  overdispersion: number | null;
  pseudo_r2: number | null;
}

export interface Hotspot {
  h3: string;
  lat: number;
  lon: number;
  priority_pct: number;
  rank: number;
  violation_count: number;
  dominant_station: string;
  junction_name: string;
  display_location: string;
  dominant_vehicle: string;
  dominant_violation: string;
  severity_10: number;
  road_class: string;
  intervention_type: string;
  peak_hours: string;
  repeat_offender_ratio: number;
  confidence_flag: string;
  units_recommended: number;
  near_school: boolean;
  near_hospital: boolean;
  blocks_bus: boolean;
  nl_summary: string;
}

export interface Station {
  police_station: string;
  violations: number;
  devices: number;
  enforcement_gap: number;
  gap_confidence: string;
  units_recommended: number;
}

export interface Citizen {
  h3: string;
  lat: number;
  lon: number;
  junction_name: string;
  display_location: string;
  dominant_station: string;
  fine_risk: number;
  risk_band: string;
  peak_hours: string;
  nl_summary: string;
}

export interface Backtest {
  k: number;
  parkpulse_coverage: number;
  reactive_coverage: number;
  uplift_pp: number;
}

export interface NbForecast {
  police_station: string;
  forecast_next_week: number;
  lower_95: number;
  upper_95: number;
}

export interface Patrol {
  shift: string;
  h3: string;
  junction_name: string;
  display_location: string;
  police_station: string;
  expected_violations: number;
  dominant_vehicle: string;
  dominant_violation: string;
  assigned_unit: string;
  rank: number;
}

export interface Watch {
  vehicle_number: string;
  vehicle_type: string;
  violations: number;
  distinct_cells: number;
  top_location: string;
  top_junction: string;
  severity_sum: number;
  first_seen: string;
  last_seen: string;
  station: string | null;
  station_exact: boolean;
}

export type ReportStatus = "Pending" | "Verified" | "Rejected";

export interface Report {
  id: number;
  reporter: string;
  vehicle: string;
  category: string;
  location: string;
  note: string;
  lat: number | null;
  lon: number | null;
  status: ReportStatus;
  points: number;
  challan_id: string | null;
  image: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface LeaderEntry {
  reporter: string;
  points: number;
  verified: number;
  reports: number;
  badge: string;
}

export interface ParkingSpot {
  id: number;
  name: string;
  area: string;
  lat: number | null;
  lon: number | null;
  kind: string;
  price: string;
  note: string;
  added_by: string;
  upvotes: number;
  flags: number;
  risk_band: string;
  fine_risk: number | null;
  image: string;
  status: string;
  created_at: string | null;
  distance_km: number | null;
}

export interface Officer {
  id: number;
  name: string;
  badge: string | null;
  station: string;
  beat_h3: string | null;
  area: string | null;
  patrol_window: string | null;
  shift: string;
  target: number;
  done: number;
  status: string;
  updated_at: string | null;
}

export interface StationSummary {
  police_station: string;
  violations: number;
  devices: number;
  enforcement_gap: number;
  gap_confidence: string;
  units_recommended: number;
  officers: number;
  target_total: number;
  done_total: number;
  forecast_next_week: number | null;
}

export type ChallanStatus = "Issued" | "Paid" | "Unpaid" | "Disputed";

export interface Challan {
  id: string;
  vehicle: string;
  category: string;
  amount: number;
  status: ChallanStatus;
  station: string;
  officer: string;
  location: string;
  due: string | null;
  evidence: string;
  created_at: string | null;
  updated_at: string | null;
}
