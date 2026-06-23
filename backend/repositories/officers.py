"""Officer roster, data-derived targets, and station summaries.

Targets come from the violations data (the expected load on each assigned beat),
so deployment is fair and auditable rather than arbitrary.
"""
from __future__ import annotations

from backend.database import rows_to_dicts, session


def list_officers(station: str | None = None) -> list[dict]:
    sql = "SELECT * FROM officers"
    args: list = []
    if station:
        sql += " WHERE station = ?"
        args.append(station)
    sql += " ORDER BY station, id"
    with session() as con:
        return rows_to_dicts(con.execute(sql, args).fetchall())


def assign_officer(oid: int, patch: dict) -> dict | None:
    fields = {
        k: v
        for k, v in patch.items()
        if k in ("beat_h3", "area", "patrol_window", "shift", "status")
        and v is not None
    }
    if not fields:
        return None
    sets = ", ".join(f"{k} = ?" for k in fields)
    args = list(fields.values()) + [oid]
    with session() as con:
        con.execute(
            f"UPDATE officers SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            args,
        )
        row = con.execute("SELECT * FROM officers WHERE id = ?", [oid]).fetchone()
        return dict(row) if row else None


def station_summary(station: str) -> dict | None:
    with session() as con:
        st = con.execute(
            "SELECT * FROM stations WHERE police_station = ?", [station]
        ).fetchone()
        if not st:
            return None
        agg = con.execute(
            """
            SELECT COUNT(*) AS officers,
                   COALESCE(SUM(target), 0) AS target_total,
                   COALESCE(SUM(done), 0) AS done_total
            FROM officers WHERE station = ?
            """,
            [station],
        ).fetchone()
        fc = con.execute(
            "SELECT forecast_next_week FROM nb_forecast WHERE police_station = ?",
            [station],
        ).fetchone()
    out = dict(st)
    out.update(dict(agg))
    out["forecast_next_week"] = fc["forecast_next_week"] if fc else None
    return out


# Officer name pool — assigned round-robin across each station's top beats.
_NAMES = [
    ("ASI Kavitha R.", "BTP-1042"),
    ("HC Ramesh N.", "BTP-2087"),
    ("PC Imran S.", "BTP-3310"),
    ("PC Lakshmi D.", "BTP-3418"),
    ("HC Suresh M.", "BTP-2231"),
    ("PC Anita K.", "BTP-3502"),
]
# Vary done vs target so the roster shows real accountability spread.
_DONE_FACTORS = [0.92, 0.61, 1.08, 0.74, 0.45, 0.83]


def seed_officers_if_empty() -> None:
    with session() as con:
        if con.execute("SELECT COUNT(*) AS n FROM officers").fetchone()["n"] > 0:
            return
        # Busiest stations get a roster; each officer takes one of the station's
        # top beats, with a target derived from that beat's recorded load.
        stations = con.execute(
            "SELECT police_station FROM stations ORDER BY violations DESC LIMIT 6"
        ).fetchall()

        ni = 0
        for s in stations:
            station = s["police_station"]
            beats = con.execute(
                """
                SELECT h3, display_location, peak_hours, violation_count, dominant_violation
                FROM hotspots WHERE dominant_station = ?
                ORDER BY rank LIMIT 3
                """,
                [station],
            ).fetchall()
            for j, b in enumerate(beats):
                name, badge = _NAMES[ni % len(_NAMES)]
                factor = _DONE_FACTORS[ni % len(_DONE_FACTORS)]
                # Weekly target ≈ recorded violations on the beat over ~21 weeks.
                target = max(8, round((b["violation_count"] or 0) / 21))
                done = round(target * factor)
                window = b["peak_hours"] or "5pm – 8pm"
                shift = ("Morning", "Afternoon", "Evening")[j % 3]
                con.execute(
                    """
                    INSERT INTO officers
                    (name, badge, station, beat_h3, area, patrol_window, shift, target, done, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'On duty')
                    """,
                    [
                        name,
                        badge,
                        station,
                        b["h3"],
                        b["display_location"],
                        window,
                        shift,
                        target,
                        done,
                    ],
                )
                ni += 1
