"""Live event surge store — police-entered upcoming events that scale a station's
NB baseline forecast. Human-in-the-loop; multipliers are explicit assumptions
(the dataset has no labeled events). Persisted to events.json (survives rebuilds)."""
import json
from datetime import date
from src.config import EVENTS_FILE, EVENT_IMPACT


def _load():
    try:
        return json.load(open(EVENTS_FILE))
    except Exception:
        return []


def _save(events):
    json.dump(events, open(EVENTS_FILE, "w"), indent=2, default=str)


def add_event(name, etype, station, ev_date, impact_level, note, created_by="Officer"):
    events = _load()
    events.append({
        "id": (max([e["id"] for e in events], default=0) + 1),
        "name": name or etype, "type": etype, "station": station,
        "date": str(ev_date), "impact_level": impact_level,
        "multiplier": EVENT_IMPACT.get(impact_level, 1.0),
        "note": note or "", "created_by": created_by,
    })
    _save(events)


def list_events(station=None, upcoming_only=False):
    events = _load()
    if station:
        events = [e for e in events if e["station"] == station]
    if upcoming_only:
        today = str(date.today())
        events = [e for e in events if e["date"] >= today]
    return sorted(events, key=lambda e: e["date"])


def delete_event(event_id):
    _save([e for e in _load() if e["id"] != event_id])


def station_multiplier(station):
    """Combined surge multiplier for a station's upcoming events + the drivers."""
    drivers = list_events(station=station, upcoming_only=True)
    mult = 1.0
    for e in drivers:
        mult *= float(e["multiplier"])
    return mult, drivers
