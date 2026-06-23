"""Test FastAPI analytics endpoints — uses isolated DB, never production data."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.database import init_db, session
from backend.main import app
from backend.repositories.analytics import clear_analytics


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setenv("PARKPULSE_DB", str(test_db))
    init_db()
    with session() as con:
        clear_analytics(con)
        con.execute(
            "INSERT OR REPLACE INTO kpis (id, payload) VALUES (1, ?)",
            [json.dumps({
                "total_violations": 100,
                "confirmed_violations": 90,
                "n_stations": 5,
                "n_hotspots": 10,
                "top20_impact_share": 0.3,
                "evening_enforcement_share": 0.02,
                "repeat_offenders": 3,
                "repeat_offender_share": 0.01,
                "precision_at_20": 0.85,
                "naive_precision_at_20": 0.75,
                "uplift_k": 20,
                "parkpulse_coverage": 0.23,
                "reactive_coverage": 0.10,
                "uplift_pp": 0.13,
                "date_min": "2023-11-01",
                "date_max": "2024-04-08",
            })],
        )
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "test.db" in r.json()["db"]


def test_kpis(client):
    r = client.get("/api/kpis")
    assert r.status_code == 200
    assert r.json()["total_violations"] == 100


def test_challans_seed(client):
    r = client.get("/api/challans")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_production_db_not_used(monkeypatch, tmp_path):
    """Guard: pytest must not point at the real parkpulse.db."""
    test_db = tmp_path / "guard.db"
    monkeypatch.setenv("PARKPULSE_DB", str(test_db))
    from backend.config import get_db_path
    assert get_db_path() == test_db
    assert "parkpulse.db" not in str(get_db_path()) or str(test_db).endswith("guard.db")
