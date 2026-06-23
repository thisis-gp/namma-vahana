"""Column contracts for every artifact. The UI builds against these names."""

HOTSPOT_CELLS = ["h3", "lat", "lon", "violation_count", "confirmed_count",
                 "junction_name", "display_location", "police_station", "dominant_vehicle",
                 "dominant_violation", "dbscan_cluster"]

CIS_SCORES = ["h3", "lat", "lon", "cis", "f_volume", "f_severity", "f_road",
              "f_peak", "road_class", "rank"]

HOURLY_HEAT = ["h3", "lat", "lon", "hour", "is_weekend", "count", "cis_hour"]

FORECAST = ["h3", "lat", "lon", "date", "shift", "pred_intensity", "expected_violations"]

PATROL_PLAN = ["shift", "h3", "lat", "lon", "junction_name", "display_location", "police_station",
               "expected_violations", "dominant_vehicle", "dominant_violation",
               "cis", "assigned_unit", "rank"]

HOTSPOTS_ENRICHED = ["h3", "lat", "lon", "cis", "priority_score", "priority_pct", "rank",
                     "violation_count", "confirmed_count", "dominant_station", "junction_name",
                     "display_location", "dominant_vehicle", "dominant_violation", "severity_10",
                     "road_class", "repeat_offender_ratio", "intervention_type",
                     "correction_rate", "confidence_flag", "near_school", "near_hospital",
                     "blocks_bus", "peak_hours", "peak_lq", "units_recommended", "nl_summary"]

STATIONS = ["police_station", "violations", "devices", "enforcement_gap",
            "gap_confidence", "units_recommended"]

CITIZEN = ["h3", "lat", "lon", "junction_name", "display_location", "dominant_station", "fine_risk",
           "risk_band", "peak_hours", "nl_summary"]

BACKTEST = ["k", "parkpulse_coverage", "reactive_coverage", "uplift_pp"]

WATCHLIST = ["vehicle_number", "vehicle_type", "violations", "distinct_cells",
             "top_location", "top_junction", "severity_sum", "first_seen", "last_seen"]

KPIS = ["total_violations", "confirmed_violations", "n_stations", "n_hotspots",
        "top20_impact_share", "evening_enforcement_share", "repeat_offenders",
        "repeat_offender_share", "precision_at_20", "naive_precision_at_20",
        "uplift_k", "parkpulse_coverage", "reactive_coverage", "uplift_pp",
        "speed_corr_spearman", "date_min", "date_max"]
