"""Tests for POST /api/v1/telemetry ingestion endpoint and end-to-end processing pipeline."""

from datetime import datetime, timezone
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.alert import Alert
from app.models.baseline import Baseline
from app.models.enums import AlertStatus, EventSeverity, EventSourceType, EventStatus, SessionMode, SessionStatus
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone


@pytest.fixture(name="db_session")
def db_session_fixture():
    """In-memory SQLite database session fixture with StaticPool for thread safety."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(name="client")
def client_fixture(db_session: Session):
    """FastAPI TestClient fixture with overridden get_db dependency."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="seeded_zones_context")
def seeded_zones_context_fixture(db_session: Session):
    """Fixture seeding standard demo zones, baseline stats, and active monitoring session."""
    now = datetime.now(timezone.utc)

    # Zone 1
    zone1 = Zone(name="Zone 1 - Main Deck Girder", floor="Level 2", description="Main deck framing")
    zone2 = Zone(name="Zone 2 - Substructure Pier B", floor="Substructure", description="Pier foundation")
    db_session.add_all([zone1, zone2])
    db_session.flush()

    # Baselines
    b1 = Baseline(
        zone_id=zone1.id,
        mean_magnitude=1.20,
        std_magnitude=0.15,
        mean_energy=12.00,
        std_energy=1.50,
        normal_event_rate=0.02,
        valid_from=now,
    )
    b2 = Baseline(
        zone_id=zone2.id,
        mean_magnitude=0.85,
        std_magnitude=0.10,
        mean_energy=8.50,
        std_energy=1.00,
        normal_event_rate=0.015,
        valid_from=now,
    )
    db_session.add_all([b1, b2])

    # Monitoring Session
    session = MonitoringSession(
        name="Demo Structural Health Session",
        mode=SessionMode.LIVE,
        status=SessionStatus.RUNNING,
        started_at=now,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(zone1)
    db_session.refresh(zone2)
    db_session.refresh(session)

    return {
        "zone1_id": zone1.id,
        "zone1_name": zone1.name,
        "zone2_id": zone2.id,
        "zone2_name": zone2.name,
        "session_id": session.id,
    }


def test_post_telemetry_quiet_signal_no_event(client: TestClient, seeded_zones_context: dict, db_session: Session):
    """Test telemetry with quiet/noise samples below threshold produces no detected event."""
    samples = (np.random.RandomState(42).normal(0.0, 0.05, 500)).tolist()

    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 1,
        "samples": samples,
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["telemetry_accepted"] is True
    assert data["status"] == "PROCESSED_NO_EVENT"
    assert data["sensor_id"] == "PZT-Z01"
    assert data["zone_id"] == seeded_zones_context["zone1_id"]
    assert data["events_detected"] == 0
    assert len(data["events"]) == 0
    assert data["extracted_features"] is None
    assert data["alert_generated"] is False

    # Confirm no new Event was persisted in database
    event_count = db_session.query(Event).filter(Event.zone_id == seeded_zones_context["zone1_id"]).count()
    assert event_count == 0


def test_post_telemetry_burst_signal_detects_event_and_persists(
    client: TestClient, seeded_zones_context: dict, db_session: Session
):
    """Test telemetry containing a high-amplitude burst signal generates a detected event."""
    # Construct 1000-sample signal with a distinct burst
    samples = np.zeros(1000)
    # Burst between index 300 and 400 with amplitude 4.5
    t = np.linspace(0, 0.1, 100, endpoint=False)
    samples[300:400] = 4.5 * np.sin(2 * np.pi * 100 * t)

    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 101,
        "samples": samples.tolist(),
        "detection_threshold": 1.0,
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["telemetry_accepted"] is True
    assert data["events_detected"] >= 1
    assert data["sensor_id"] == "PZT-Z01"
    assert data["zone_id"] == seeded_zones_context["zone1_id"]
    assert data["extracted_features"] is not None
    assert data["extracted_features"]["peak_amplitude"] > 3.0

    # Verify event detail
    evt = data["events"][0]
    assert evt["event_id"] is not None
    assert evt["magnitude"] > 3.0
    assert evt["is_anomalous"] is True
    assert evt["magnitude_z_score"] is not None
    assert len(evt["anomaly_reasons"]) > 0

    # Verify Event record in database
    db_evt = db_session.query(Event).filter(Event.id == evt["event_id"]).first()
    assert db_evt is not None
    assert db_evt.source_id == "PZT-Z01"
    assert db_evt.zone_id == seeded_zones_context["zone1_id"]
    assert db_evt.magnitude == pytest.approx(evt["magnitude"], rel=1e-3)
    assert db_evt.source_type == EventSourceType.SENSOR


def test_post_telemetry_unknown_zone_returns_404(client: TestClient):
    """Test telemetry targeting an unregistered zone returns HTTP 404."""
    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": "Nonexistent Roof Deck Section",
        "sample_rate_hz": 1000.0,
        "samples": [0.1, 0.2, 0.3],
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 404
    assert "Zone 'Nonexistent Roof Deck Section' not found" in response.json()["detail"]


def test_post_telemetry_inconsistent_sensor_zone_returns_400(client: TestClient, seeded_zones_context: dict):
    """Test sending Zone 1 sensor (PZT-Z01) to Zone 2 returns HTTP 400."""
    payload = {
        "sensor_id": "PZT-Z01",  # Canonical Zone 1 sensor
        "zone_name": seeded_zones_context["zone2_name"],  # Zone 2 target
        "sample_rate_hz": 1000.0,
        "samples": [0.1, 0.2, 0.3],
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 400
    assert "is inconsistent with target zone" in response.json()["detail"]


def test_post_telemetry_invalid_sample_rate_returns_422(client: TestClient, seeded_zones_context: dict):
    """Test sample_rate <= 0 returns HTTP 422."""
    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": -100.0,
        "samples": [0.1, 0.2, 0.3],
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422


def test_post_telemetry_empty_samples_returns_422(client: TestClient, seeded_zones_context: dict):
    """Test empty samples list returns HTTP 422."""
    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "samples": [],
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422


def test_post_telemetry_sample_rate_alias(client: TestClient, seeded_zones_context: dict):
    """Test payload using 'sample_rate' field alias is accepted."""
    payload = {
        "sensor_id": "PZT-Z07",
        "zone_name": seeded_zones_context["zone2_name"],
        "sample_rate": 500.0,
        "samples": [0.01, 0.02, 0.01],
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200
    assert response.json()["sample_rate_hz"] == 500.0


def test_post_telemetry_zone2_multi_sensor_support(
    client: TestClient, seeded_zones_context: dict, db_session: Session
):
    """Test multi-sensor routing to Zone 2 with PZT-Z07 and PZT-Z08."""
    # Sensor 1
    p1 = {
        "sensor_id": "PZT-Z07",
        "zone_name": seeded_zones_context["zone2_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 1,
        "samples": [0.01] * 100,
    }
    r1 = client.post("/api/v1/telemetry", json=p1)
    assert r1.status_code == 200
    assert r1.json()["zone_id"] == seeded_zones_context["zone2_id"]

    # Sensor 2
    p2 = {
        "sensor_id": "PZT-Z08",
        "zone_name": seeded_zones_context["zone2_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 1,
        "samples": [0.02] * 100,
    }
    r2 = client.post("/api/v1/telemetry", json=p2)
    assert r2.status_code == 200
    assert r2.json()["zone_id"] == seeded_zones_context["zone2_id"]


def test_get_latest_telemetry_empty_and_populated(
    client: TestClient, seeded_zones_context: dict
):
    """Test GET /api/v1/telemetry/latest returns null when empty and populated after ingestion."""
    from app.services.telemetry_service import TelemetryService

    # 1. Clear cached snapshot
    TelemetryService.clear_latest_telemetry()
    resp_empty = client.get("/api/v1/telemetry/latest")
    assert resp_empty.status_code == 200
    assert resp_empty.json() is None

    # 2. Ingest telemetry
    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 42,
        "samples": [0.05, 0.10, 0.15, 0.08, 0.02],
        "detection_threshold": 0.5,
    }
    post_resp = client.post("/api/v1/telemetry", json=payload)
    assert post_resp.status_code == 200

    # 3. Query GET /latest
    latest_resp = client.get("/api/v1/telemetry/latest")
    assert latest_resp.status_code == 200
    data = latest_resp.json()
    assert data is not None
    assert data["sensor_id"] == "PZT-Z01"
    assert data["zone_id"] == seeded_zones_context["zone1_id"]
    assert data["sequence"] == 42
    assert data["samples_count"] == 5
    assert len(data["samples"]) == 5
    assert data["samples"] == [0.05, 0.10, 0.15, 0.08, 0.02]
    assert data["detection_threshold"] == 0.5


def test_get_latest_telemetry_bounded_samples(
    client: TestClient, seeded_zones_context: dict
):
    """Test that display samples returned in GET /latest are bounded to 500 items max."""
    large_samples = [float(i * 0.001) for i in range(1200)]
    payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 99,
        "samples": large_samples,
    }
    post_resp = client.post("/api/v1/telemetry", json=payload)
    assert post_resp.status_code == 200
    assert post_resp.json()["samples_count"] == 1200

    latest_resp = client.get("/api/v1/telemetry/latest")
    assert latest_resp.status_code == 200
    data = latest_resp.json()
    assert data["samples_count"] == 1200
    assert len(data["samples"]) == 500


def test_get_latest_telemetry_multi_sensor_isolation(
    client: TestClient, seeded_zones_context: dict
):
    """Test that multiple sensors maintain independent cached snapshots without overwriting each other."""
    from app.services.telemetry_service import TelemetryService

    # 1. Clear cache
    TelemetryService.clear_latest_telemetry()
    assert client.get("/api/v1/telemetry/latest").json() is None

    # 2. Ingest PZT-Z01
    p1 = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 10,
        "samples": [0.01, 0.02, 0.03, 0.04, 0.05],
    }
    r1 = client.post("/api/v1/telemetry", json=p1)
    assert r1.status_code == 200

    # 3. Ingest PZT-Z02
    p2 = {
        "sensor_id": "PZT-Z02",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 20,
        "samples": [0.09, 0.08, 0.07],
    }
    r2 = client.post("/api/v1/telemetry", json=p2)
    assert r2.status_code == 200

    # 4. Without query param: returns most recent sensor (PZT-Z02)
    latest_general = client.get("/api/v1/telemetry/latest").json()
    assert latest_general["sensor_id"] == "PZT-Z02"
    assert latest_general["sequence"] == 20
    assert len(latest_general["samples"]) == 3

    # 5. Query specifically for PZT-Z01: returns PZT-Z01 intact (not overwritten!)
    z1_resp = client.get("/api/v1/telemetry/latest?sensor_id=PZT-Z01").json()
    assert z1_resp["sensor_id"] == "PZT-Z01"
    assert z1_resp["sequence"] == 10
    assert len(z1_resp["samples"]) == 5

    # 6. Query specifically for PZT-Z02: returns PZT-Z02 intact
    z2_resp = client.get("/api/v1/telemetry/latest?sensor_id=PZT-Z02").json()
    assert z2_resp["sensor_id"] == "PZT-Z02"
    assert z2_resp["sequence"] == 20

    # 7. Query unknown sensor: returns null
    unk_resp = client.get("/api/v1/telemetry/latest?sensor_id=PZT-UNKNOWN").json()
    assert unk_resp is None

    # 8. Send updated packet for PZT-Z01 with sequence 11
    p1_update = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_zones_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 11,
        "samples": [0.11, 0.12],
    }
    client.post("/api/v1/telemetry", json=p1_update)

    # Verify PZT-Z01 is updated to seq 11
    z1_updated = client.get("/api/v1/telemetry/latest?sensor_id=PZT-Z01").json()
    assert z1_updated["sequence"] == 11
    assert len(z1_updated["samples"]) == 2

    # Verify PZT-Z02 was NOT affected (still seq 20)
    z2_still = client.get("/api/v1/telemetry/latest?sensor_id=PZT-Z02").json()
    assert z2_still["sequence"] == 20

    # Now general query returns PZT-Z01 as the most recent
    assert client.get("/api/v1/telemetry/latest").json()["sensor_id"] == "PZT-Z01"
