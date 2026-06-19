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
