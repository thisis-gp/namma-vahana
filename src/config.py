from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

RAW_CSV = ROOT / CFG["paths"]["raw_csv"]
INTERIM = ROOT / CFG["paths"]["interim_dir"]
ARTIFACTS = ROOT / CFG["paths"]["artifacts_dir"]
INTERIM.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(parents=True, exist_ok=True)

BBOX = CFG["bbox"]
H3 = CFG["h3"]
TZ = CFG["timezone"]
SHIFT_SLOTS = CFG["shift_slots"]
PEAK = CFG["peak_hours"]
VALIDATION = CFG["validation"]
CIS_WEIGHTS = CFG["cis_weights"]
SEVERITY = CFG["severity_weights"]
VEH_FOOTPRINT = CFG["vehicle_footprint"]
COMMERCIAL = set(CFG["commercial_types"])
TWO_WHEELER = set(CFG["two_wheeler_types"])
OPT = CFG["optimizer"]
SPLIT = CFG["split"]


def shift_of(hour: int) -> str:
    """Map an IST hour (0-23) to a shift slot name."""
    for name, (start, end) in SHIFT_SLOTS.items():
        if start < end:
            if start <= hour < end:
                return name
        else:  # wraps midnight (NIGHT 22-06)
            if hour >= start or hour < end:
                return name
    return "NIGHT"


def footprint_class(vehicle_type: str) -> str:
    if vehicle_type in COMMERCIAL:
        return "commercial"
    if vehicle_type in TWO_WHEELER:
        return "two_wheeler"
    return "car"


# --- Merged-feature params (all operate on the provided dataset only) ---
REPEAT_MIN_APPEARANCES = 3      # a vehicle is a "repeat offender" at >= 3 appearances
REPEAT_RATIO_HIGH = 0.45        # hotspot repeat share >= this => targeted enforcement
CORRECTION_FLAG_MULT = 1.5      # hotspot correction rate >= avg*this => "lower confidence"
ACTIONABLE_HOURS = (6, 23)      # peak-window labels constrained to these IST hours
# Severity 1-10 from violation subtype (in-dataset; mirrors enforcement priority)
SEVERITY_10 = {
    "PARKING IN A MAIN ROAD": 10, "NO PARKING": 9, "PARKING ON FOOTPATH": 9,
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 8, "PARKING NEAR ROAD CROSSING": 8,
    "PARKING NEAR TRAFFIC LIGHT": 8, "PARKING ON ZEBRA": 8, "DOUBLE PARKING": 7,
    "WRONG PARKING": 5, "DEFECTIVE NUMBER PLATE": 2, "BLACK FILM": 2,
    "REFUSE TO GO FOR HIRE": 3,
}
SEVERITY_10_DEFAULT = 4
# Live event surge overlay — explicit operational ASSUMPTIONS (not learned; dataset
# has no labeled events). Scales a station's NB baseline forecast when an officer
# declares a known upcoming event.
EVENT_IMPACT = {
    "Minor — local gathering": 1.2,
    "Moderate — festival / market day": 1.5,
    "Major — IPL match / concert": 2.5,
    "Severe — VIP / PM visit / inauguration": 3.5,
}
EVENT_TYPES = ["Inauguration", "IPL / Sports match", "VIP / PM visit",
               "Festival / Procession", "Concert / Public event", "Protest / Rally", "Other"]
EVENTS_FILE = ROOT / "events.json"
# Allocation (station-level, severity-weighted demand vs patrol throughput)
VIOL_CLEARED_PER_UNIT = 40
SHIFTS_PER_DAY = 2
COVERAGE_TARGET = 0.80
GAP_CONF_STD_MULT = 1.0         # station device-correction rate >= mean + N*std => "lower"
