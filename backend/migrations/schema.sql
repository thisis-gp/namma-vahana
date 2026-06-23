-- ParkPulse SQLite schema — analytics (pipeline) + operations (live app)

PRAGMA foreign_keys = ON;

-- ── Analytics (refreshed by pipeline) ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kpis (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  payload TEXT NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hotspots (
  h3 TEXT PRIMARY KEY,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  priority_pct REAL,
  rank INTEGER,
  violation_count INTEGER,
  dominant_station TEXT,
  junction_name TEXT,
  display_location TEXT,
  dominant_vehicle TEXT,
  dominant_violation TEXT,
  severity_10 REAL,
  road_class TEXT,
  intervention_type TEXT,
  peak_hours TEXT,
  repeat_offender_ratio REAL,
  confidence_flag TEXT,
  units_recommended INTEGER,
  near_school INTEGER DEFAULT 0,
  near_hospital INTEGER DEFAULT 0,
  blocks_bus INTEGER DEFAULT 0,
  nl_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_hotspots_station ON hotspots(dominant_station);
CREATE INDEX IF NOT EXISTS idx_hotspots_rank ON hotspots(rank);

CREATE TABLE IF NOT EXISTS stations (
  police_station TEXT PRIMARY KEY,
  violations INTEGER,
  devices INTEGER,
  enforcement_gap REAL,
  gap_confidence TEXT,
  units_recommended INTEGER
);

CREATE TABLE IF NOT EXISTS citizen (
  h3 TEXT PRIMARY KEY,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  junction_name TEXT,
  display_location TEXT,
  dominant_station TEXT,
  fine_risk REAL,
  risk_band TEXT,
  peak_hours TEXT,
  nl_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_citizen_risk ON citizen(fine_risk DESC);

CREATE TABLE IF NOT EXISTS backtest (
  k INTEGER PRIMARY KEY,
  parkpulse_coverage REAL,
  reactive_coverage REAL,
  uplift_pp REAL
);

CREATE TABLE IF NOT EXISTS nb_forecast (
  police_station TEXT PRIMARY KEY,
  forecast_next_week REAL,
  lower_95 REAL,
  upper_95 REAL
);

CREATE TABLE IF NOT EXISTS patrol_plan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift TEXT NOT NULL,
  h3 TEXT NOT NULL,
  lat REAL,
  lon REAL,
  junction_name TEXT,
  display_location TEXT,
  police_station TEXT,
  expected_violations REAL,
  dominant_vehicle TEXT,
  dominant_violation TEXT,
  cis REAL,
  assigned_unit TEXT,
  rank INTEGER,
  UNIQUE(shift, h3, police_station)
);
CREATE INDEX IF NOT EXISTS idx_patrol_station ON patrol_plan(police_station);
CREATE INDEX IF NOT EXISTS idx_patrol_shift ON patrol_plan(shift);

CREATE TABLE IF NOT EXISTS watchlist (
  vehicle_number TEXT PRIMARY KEY,
  vehicle_type TEXT,
  violations INTEGER,
  distinct_cells INTEGER,
  top_location TEXT,
  top_junction TEXT,
  severity_sum REAL,
  first_seen TEXT,
  last_seen TEXT
);

-- ── Operations (mutable at runtime) ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS challans (
  id TEXT PRIMARY KEY,
  vehicle TEXT NOT NULL,
  category TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL,
  station TEXT NOT NULL,
  officer TEXT,
  location TEXT,
  due TEXT,
  evidence TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_challans_station ON challans(station);
CREATE INDEX IF NOT EXISTS idx_challans_vehicle ON challans(vehicle);

CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  station TEXT NOT NULL,
  h3 TEXT NOT NULL,
  shift TEXT NOT NULL,
  beat_name TEXT NOT NULL,
  assigned_to TEXT NOT NULL,
  location TEXT,
  expected_violations INTEGER DEFAULT 0,
  status TEXT DEFAULT 'Assigned',
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(station, h3, shift)
);

-- Citizen-submitted reports. A report is NOT a challan: a citizen cannot fine.
-- Pending → officer verifies → an official challan is created + points awarded.
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reporter TEXT NOT NULL,
  vehicle TEXT DEFAULT '',
  category TEXT NOT NULL DEFAULT 'Wrong Parking',
  location TEXT NOT NULL,
  note TEXT DEFAULT '',
  lat REAL,
  lon REAL,
  status TEXT NOT NULL DEFAULT 'Pending',  -- Pending | Verified | Rejected
  points INTEGER DEFAULT 0,
  challan_id TEXT,
  image TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_reporter ON reports(reporter);

-- Community-suggested parking. Citizens supply WHERE you can park; the
-- violations dataset supplies WHETHER it's actually safe (risk_band, derived
-- from the nearest citizen cell at insert time). No external data used.
CREATE TABLE IF NOT EXISTS parking_spots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  area TEXT NOT NULL,
  lat REAL,
  lon REAL,
  kind TEXT NOT NULL DEFAULT 'Roadside',   -- Roadside | Open ground | Building | Pay-and-park
  price TEXT NOT NULL DEFAULT 'Free',        -- Free | Paid
  note TEXT DEFAULT '',
  added_by TEXT DEFAULT 'Anonymous',
  upvotes INTEGER DEFAULT 0,
  flags INTEGER DEFAULT 0,
  risk_band TEXT DEFAULT 'Unknown',
  fine_risk REAL,
  image TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'Active',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_parking_area ON parking_spots(area);

-- Officer roster per station. Targets are DERIVED from the violations data
-- (expected load on the assigned beat) so deployment is fair and auditable —
-- the accountability angle: who's assigned where, expected vs done.
CREATE TABLE IF NOT EXISTS officers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  badge TEXT,
  station TEXT NOT NULL,
  beat_h3 TEXT,
  area TEXT,
  patrol_window TEXT,
  shift TEXT DEFAULT 'Morning',
  target INTEGER DEFAULT 0,
  done INTEGER DEFAULT 0,
  status TEXT DEFAULT 'On duty',
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_officers_station ON officers(station);
