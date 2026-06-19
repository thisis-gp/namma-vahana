"""Column contracts for every artifact. The UI builds against these names."""

HOTSPOT_CELLS = ["h3", "lat", "lon", "violation_count", "confirmed_count",
                 "junction_name", "police_station", "dominant_vehicle",
                 "dominant_violation", "dbscan_cluster"]

CIS_SCORES = ["h3", "lat", "lon", "cis", "f_volume", "f_severity", "f_road",
              "f_peak", "road_class", "rank"]

HOURLY_HEAT = ["h3", "lat", "lon", "hour", "is_weekend", "count", "cis_hour"]

FORECAST = ["h3", "lat", "lon", "date", "shift", "pred_intensity", "expected_violations"]

PATROL_PLAN = ["shift", "h3", "lat", "lon", "junction_name", "police_station",
               "expected_violations", "dominant_vehicle", "dominant_violation",
               "cis", "assigned_unit", "rank"]

KPIS = ["total_violations", "confirmed_violations", "n_stations", "n_hotspots",
        "top20_impact_share", "evening_enforcement_share", "repeat_offenders",
        "precision_at_20", "naive_precision_at_20", "speed_corr_spearman",
        "date_min", "date_max"]
