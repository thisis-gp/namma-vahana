"""Operations data access — challans and patrol assignments."""
from __future__ import annotations

from datetime import date, timedelta

from backend.database import rows_to_dicts, session


def list_challans(station: str | None = None, vehicle: str | None = None) -> list[dict]:
    sql = "SELECT * FROM challans WHERE 1=1"
    args: list = []
    if station:
        sql += " AND station = ?"
        args.append(station)
    if vehicle:
        sql += " AND vehicle = ?"
        args.append(vehicle.upper())
    sql += " ORDER BY created_at DESC, id DESC"
    with session() as con:
        return rows_to_dicts(con.execute(sql, args).fetchall())


def next_challan_id(con) -> str:
    rows = con.execute("SELECT id FROM challans WHERE id LIKE 'PP-%'").fetchall()
    nums = []
    for row in rows:
        try:
            nums.append(int(str(row["id"]).split("-", 1)[1]))
        except (IndexError, ValueError):
            pass
    return f"PP-{(max(nums) if nums else 2400) + 1}"


def create_challan(data: dict) -> dict:
    with session() as con:
        cid = data.get("id") or next_challan_id(con)
        row = {
            "id": cid,
            "vehicle": str(data["vehicle"]).upper(),
            "category": data.get("category", "Wrong Parking"),
            "amount": int(data.get("amount", 1000)),
            "status": data.get("status", "Issued"),
            "station": data.get("station", "City-wide"),
            "officer": data.get("officer", "To be assigned"),
            "location": data.get("location", ""),
            "due": data.get("due") or (date.today() + timedelta(days=7)).isoformat(),
            "evidence": data.get("evidence", ""),
        }
        con.execute(
            """
            INSERT INTO challans
            (id, vehicle, category, amount, status, station, officer, location, due, evidence)
            VALUES (:id, :vehicle, :category, :amount, :status, :station, :officer, :location, :due, :evidence)
            """,
            row,
        )
        return dict(con.execute("SELECT * FROM challans WHERE id = ?", [cid]).fetchone())


def update_challan(cid: str, patch: dict) -> dict | None:
    allowed = {k: patch[k] for k in ("status", "officer") if k in patch and patch[k] is not None}
    if not allowed:
        return None
    sets = ", ".join(f"{k} = ?" for k in allowed)
    args = list(allowed.values()) + [cid]
    with session() as con:
        con.execute(
            f"UPDATE challans SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            args,
        )
        row = con.execute("SELECT * FROM challans WHERE id = ?", [cid]).fetchone()
        return dict(row) if row else None


def list_assignments(station: str | None = None) -> list[dict]:
    sql = "SELECT * FROM assignments"
    args: list = []
    if station:
        sql += " WHERE station = ?"
        args.append(station)
    sql += " ORDER BY updated_at DESC, id DESC"
    with session() as con:
        return rows_to_dicts(con.execute(sql, args).fetchall())


def upsert_assignment(data: dict) -> dict:
    with session() as con:
        con.execute(
            """
            INSERT INTO assignments
            (station, h3, shift, beat_name, assigned_to, location, expected_violations, status)
            VALUES (:station, :h3, :shift, :beat_name, :assigned_to, :location, :expected_violations, :status)
            ON CONFLICT(station, h3, shift) DO UPDATE SET
              beat_name = excluded.beat_name,
              assigned_to = excluded.assigned_to,
              location = excluded.location,
              expected_violations = excluded.expected_violations,
              status = excluded.status,
              updated_at = CURRENT_TIMESTAMP
            """,
            data,
        )
        row = con.execute(
            "SELECT * FROM assignments WHERE station = ? AND h3 = ? AND shift = ?",
            [data["station"], data["h3"], data["shift"]],
        ).fetchone()
        return dict(row)


# ── Citizen reports + gamification ──────────────────────────────────────────

POINTS_PER_VERIFIED = 50


def badge_for(points: int) -> str:
    if points >= 600:
        return "Gold Guardian"
    if points >= 300:
        return "Silver Guardian"
    if points >= 100:
        return "Bronze Guardian"
    if points > 0:
        return "Street Spotter"
    return "New Reporter"


def list_reports(status: str | None = None, reporter: str | None = None) -> list[dict]:
    sql = "SELECT * FROM reports WHERE 1=1"
    args: list = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if reporter:
        sql += " AND reporter = ?"
        args.append(reporter)
    sql += " ORDER BY created_at DESC, id DESC"
    with session() as con:
        return rows_to_dicts(con.execute(sql, args).fetchall())


def create_report(data: dict) -> dict:
    with session() as con:
        row = {
            "reporter": str(data["reporter"]).strip() or "Anonymous",
            "vehicle": str(data.get("vehicle", "")).upper().strip(),
            "category": data.get("category", "Wrong Parking"),
            "location": data.get("location", ""),
            "note": data.get("note", ""),
            "lat": data.get("lat"),
            "lon": data.get("lon"),
            "image": data.get("image", ""),
        }
        cur = con.execute(
            """
            INSERT INTO reports (reporter, vehicle, category, location, note, lat, lon, image)
            VALUES (:reporter, :vehicle, :category, :location, :note, :lat, :lon, :image)
            """,
            row,
        )
        rid = cur.lastrowid
        return dict(con.execute("SELECT * FROM reports WHERE id = ?", [rid]).fetchone())


def act_on_report(rid: int, action: str, officer: str) -> dict | None:
    """Officer verifies (→ creates a challan, awards points) or rejects a report."""
    with session() as con:
        report = con.execute("SELECT * FROM reports WHERE id = ?", [rid]).fetchone()
        if not report:
            return None
        report = dict(report)
        if report["status"] != "Pending":
            return report  # already actioned — idempotent

        if action == "verify":
            cid = None
            if report["vehicle"]:
                cid = next_challan_id(con)
                due = (date.today() + timedelta(days=7)).isoformat()
                con.execute(
                    """
                    INSERT INTO challans
                    (id, vehicle, category, amount, status, station, officer, location, due, evidence)
                    VALUES (?, ?, ?, ?, 'Issued', 'Citizen report', ?, ?, ?, ?)
                    """,
                    [
                        cid,
                        report["vehicle"],
                        report["category"],
                        1000,
                        officer,
                        report["location"],
                        due,
                        f"citizen-report-{rid}",
                    ],
                )
            con.execute(
                """
                UPDATE reports
                SET status = 'Verified', points = ?, challan_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [POINTS_PER_VERIFIED, cid, rid],
            )
        else:
            con.execute(
                "UPDATE reports SET status = 'Rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [rid],
            )
        return dict(con.execute("SELECT * FROM reports WHERE id = ?", [rid]).fetchone())


def leaderboard(limit: int = 10) -> list[dict]:
    with session() as con:
        rows = con.execute(
            """
            SELECT reporter,
                   COALESCE(SUM(points), 0) AS points,
                   SUM(CASE WHEN status = 'Verified' THEN 1 ELSE 0 END) AS verified,
                   COUNT(*) AS reports
            FROM reports
            GROUP BY reporter
            ORDER BY points DESC, verified DESC, reports DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["badge"] = badge_for(int(d["points"]))
        out.append(d)
    return out


def seed_reports_if_empty() -> None:
    with session() as con:
        count = con.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
        if count > 0:
            return
        # A demo community so the leaderboard + review queue aren't empty.
        seed = [
            # reporter, vehicle, category, location, note, status, points
            ("Priya R.", "KA05MN3344", "Wrong Parking", "Koramangala 80 Ft Road",
             "Auto blocking the cycle lane near the bakery.", "Verified", 50),
            ("Arjun M.", "KA01HK7720", "No Parking", "Indiranagar 100 Ft Road",
             "Car parked on the no-parking stretch outside the metro.", "Verified", 50),
            ("Priya R.", "KA03PQ1102", "Footpath Parking", "Jayanagar 4th Block",
             "Two-wheelers on the footpath, pedestrians forced onto the road.", "Verified", 50),
            ("Sneha K.", "", "Double Parking", "MG Road, near Trinity",
             "Double-parked cars during evening rush.", "Pending", 0),
            ("Arjun M.", "KA02RT8890", "Wrong Parking", "Whitefield Main Road",
             "Cab idling in the bus bay.", "Pending", 0),
            ("Vikram S.", "KA51DD2031", "No Parking", "HSR Layout Sector 1",
             "Tempo unloading in a no-parking zone, blocking traffic.", "Pending", 0),
        ]
        for reporter, vehicle, cat, loc, note, status, pts in seed:
            challan_id = None
            con.execute(
                """
                INSERT INTO reports (reporter, vehicle, category, location, note, status, points, challan_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [reporter, vehicle, cat, loc, note, status, pts, challan_id],
            )


def seed_challans_if_empty() -> None:
    with session() as con:
        count = con.execute("SELECT COUNT(*) AS n FROM challans").fetchone()["n"]
        if count > 0:
            return
        seed_due = (date.today() + timedelta(days=7)).isoformat()
        con.executemany(
            """
            INSERT INTO challans
            (id, vehicle, category, amount, status, station, officer, location, due, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("PP-2401", "KA05AB1234", "Wrong Parking", 1000, "Unpaid", "Shivajinagar",
                 "ASI Kavitha", "BTP051 - Safina Plaza Junction", seed_due, "safina_01.jpg"),
                ("PP-2402", "KA03CD4521", "No Parking", 1000, "Paid", "Upparpet",
                 "HC Ramesh", "BTP040 - Elite Junction", seed_due, "elite_04.jpg"),
                ("PP-2403", "KA01EF9088", "Double Parking", 1500, "Issued", "HAL Old Airport",
                 "PC Imran", "Outer Ring Road, Vajram Onyx", seed_due, "orr_02.jpg"),
            ],
        )
