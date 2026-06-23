"""Community parking data access.

Citizens contribute spots; the violations dataset grades each spot's fine risk
by looking up the nearest analyzed cell. Everything stays in-dataset.
"""
from __future__ import annotations

import math

from backend.database import rows_to_dicts, session


def nearest_risk(con, lat: float | None, lon: float | None) -> tuple[str, float | None]:
    """Risk band + fine_risk of the nearest citizen cell to a point."""
    if lat is None or lon is None:
        return "Unknown", None
    row = con.execute(
        """
        SELECT risk_band, fine_risk
        FROM citizen
        ORDER BY ((lat - ?) * (lat - ?)) + ((lon - ?) * (lon - ?))
        LIMIT 1
        """,
        [lat, lat, lon, lon],
    ).fetchone()
    if not row:
        return "Unknown", None
    return row["risk_band"] or "Unknown", row["fine_risk"]


def _haversine_km(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def list_parking(
    area: str | None = None,
    near_lat: float | None = None,
    near_lon: float | None = None,
    limit: int = 50,
) -> list[dict]:
    sql = "SELECT * FROM parking_spots WHERE status = 'Active'"
    args: list = []
    if area:
        sql += " AND area LIKE ?"
        args.append(f"%{area}%")
    with session() as con:
        rows = rows_to_dicts(con.execute(sql, args).fetchall())

    if near_lat is not None and near_lon is not None:
        for r in rows:
            r["distance_km"] = _haversine_km(near_lat, near_lon, r["lat"], r["lon"])
        rows.sort(key=lambda r: (r["distance_km"] is None, r["distance_km"] or 0))
    else:
        # Best community-rated first.
        rows.sort(key=lambda r: (r["upvotes"], -r["flags"]), reverse=True)
    return rows[:limit]


def create_parking(data: dict) -> dict:
    with session() as con:
        band, risk = nearest_risk(con, data.get("lat"), data.get("lon"))
        row = {
            "name": data["name"].strip(),
            "area": data["area"].strip(),
            "lat": data.get("lat"),
            "lon": data.get("lon"),
            "kind": data.get("kind", "Roadside"),
            "price": data.get("price", "Free"),
            "note": data.get("note", ""),
            "added_by": (data.get("added_by") or "Anonymous").strip(),
            "image": data.get("image", ""),
            "risk_band": band,
            "fine_risk": risk,
        }
        cur = con.execute(
            """
            INSERT INTO parking_spots
            (name, area, lat, lon, kind, price, note, added_by, image, risk_band, fine_risk)
            VALUES (:name, :area, :lat, :lon, :kind, :price, :note, :added_by, :image, :risk_band, :fine_risk)
            """,
            row,
        )
        pid = cur.lastrowid
        return dict(con.execute("SELECT * FROM parking_spots WHERE id = ?", [pid]).fetchone())


def vote_parking(pid: int, kind: str) -> dict | None:
    col = "upvotes" if kind == "up" else "flags"
    with session() as con:
        exists = con.execute("SELECT 1 FROM parking_spots WHERE id = ?", [pid]).fetchone()
        if not exists:
            return None
        con.execute(f"UPDATE parking_spots SET {col} = {col} + 1 WHERE id = ?", [pid])
        # Auto-retire spots the community keeps flagging.
        con.execute(
            "UPDATE parking_spots SET status = 'Retired' WHERE id = ? AND flags >= 5",
            [pid],
        )
        return dict(con.execute("SELECT * FROM parking_spots WHERE id = ?", [pid]).fetchone())


# Realistic Bengaluru seed so the map isn't empty on first run.
# lat/lon approximate real areas; risk_band is recomputed from data on insert.
_SEED = [
    ("Freedom Park open ground", "Gandhi Nagar", 12.9779, 77.5773, "Open ground", "Free",
     "Large open lot, plenty of space on weekends.", "Ravi T.", 14, 0),
    ("MG Road boulevard pay-and-park", "MG Road", 12.9756, 77.6068, "Pay-and-park", "Paid",
     "BBMP pay-and-park along the boulevard, ₹30/hr.", "Anita P.", 22, 1),
    ("Koramangala 5th Block side lane", "Koramangala", 12.9352, 77.6245, "Roadside", "Free",
     "Quiet residential lane, free after 7pm.", "Imran K.", 9, 2),
    ("Jayanagar 4th Block complex", "Jayanagar", 12.9250, 77.5938, "Building", "Paid",
     "Multi-level near the shopping complex, always has space.", "Deepa N.", 17, 0),
    ("Indiranagar 12th Main roadside", "Indiranagar", 12.9719, 77.6412, "Roadside", "Free",
     "Marked roadside bays, busy on weekend evenings.", "Suresh M.", 6, 3),
    ("HSR BDA complex ground", "HSR Layout", 12.9116, 77.6474, "Open ground", "Free",
     "BDA ground, free and spacious.", "Lakshmi R.", 11, 0),
    ("Malleshwaram 8th Cross", "Malleshwaram", 13.0030, 77.5710, "Roadside", "Free",
     "Free roadside near the market, fills up by 10am.", "Vijay S.", 8, 1),
    ("Whitefield Forum lot", "Whitefield", 12.9700, 77.7499, "Building", "Paid",
     "Mall parking, covered, ₹40 first hour.", "Neha G.", 19, 0),
    ("Brigade Road basement", "Brigade Road", 12.9716, 77.6090, "Building", "Paid",
     "Covered basement, safe but fills fast on weekends.", "Arun V.", 13, 1),
    ("Banashankari BDA ground", "Banashankari", 12.9255, 77.5468, "Open ground", "Free",
     "Open BDA ground near the temple, free.", "Geeta H.", 7, 0),
]


def seed_parking_if_empty() -> None:
    with session() as con:
        if con.execute("SELECT COUNT(*) AS n FROM parking_spots").fetchone()["n"] > 0:
            return
        for name, area, lat, lon, kind, price, note, who, up, flg in _SEED:
            band, risk = nearest_risk(con, lat, lon)
            con.execute(
                """
                INSERT INTO parking_spots
                (name, area, lat, lon, kind, price, note, added_by, upvotes, flags, risk_band, fine_risk)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [name, area, lat, lon, kind, price, note, who, up, flg, band, risk],
            )
