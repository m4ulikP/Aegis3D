"""Integration tests verifying end-to-end telemetry flow between Simulator and Aegis3D Backend.

These tests run in-process using FastAPI TestClient and an in-memory SQLite database,
verifying that:
1. Simulator payloads strictly follow the backend contract.
2. The simulator sends only raw samples (zero forced anomaly flags).
3. The backend independently detects events, evaluates z-score anomalies, and calculates health.
4. The 2-PZT correlated scenario triggers cross-sensor correlation on the backend.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.baseline import Baseline
from app.models.enums import SessionMode, SessionStatus
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone

from simulator.sensors.virtual_pzt import VirtualPZTSensor
from simulator.signal_generator import generate_correlated_pair


@pytest.fixture(name="db_session")
def db_session_fixture():
    """In-memory SQLite database session fixture."""
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
    """FastAPI TestClient with overridden get_db dependency."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="seeded_context")
def seeded_context_fixture(db_session: Session):
    """Seed Zone 1, baseline statistics, and an active session."""
    now = datetime.now(timezone.utc)

    zone1 = Zone(name="Zone 1 - Main Deck Girder", floor="Level 2")
    zone2 = Zone(name="Zone 2 - Substructure Pier B", floor="Substructure")
    db_session.add_all([zone1, zone2])
    db_session.flush()

    b1 = Baseline(
        zone_id=zone1.id,
        mean_magnitude=1.20,
        std_magnitude=0.15,
        mean_energy=12.00,
        std_energy=1.50,
        normal_event_rate=0.02,
        valid_from=now,
    )
    db_session.add(b1)

    session = MonitoringSession(
        name="Integration Test Session",
        mode=SessionMode.LIVE,
        status=SessionStatus.RUNNING,
        started_at=now,
    )
    db_session.add(session)
    db_session.commit()

    return {
        "zone1_id": zone1.id,
        "zone1_name": zone1.name,
        "zone2_id": zone2.id,
        "zone2_name": zone2.name,
        "session_id": session.id,
    }


def test_integration_normal_telemetry_flow(client: TestClient, seeded_context: dict):
    """Verify normal simulator payload results in PROCESSED_NO_EVENT on backend."""
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-01", zone_name=seeded_context["zone1_name"])
    payload = sensor.generate_payload(mode="normal", sample_count=500, seed=42)

    # Confirm simulator does NOT include decision fields
    for field in ("is_anomalous", "anomaly", "severity", "health_score", "alert"):
        assert field not in payload

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["telemetry_accepted"] is True
    assert data["status"] == "PROCESSED_NO_EVENT"
    assert data["events_detected"] == 0
    assert data["alert_generated"] is False


def test_integration_anomaly_telemetry_flow(client: TestClient, seeded_context: dict):
    """Verify anomaly simulator payload results in PROCESSED_ANOMALY_DETECTED on backend."""
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-01", zone_name=seeded_context["zone1_name"])
    payload = sensor.generate_payload(mode="anomaly", sample_count=1000, seed=42)

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["telemetry_accepted"] is True
    assert data["status"] == "PROCESSED_ANOMALY_DETECTED"
    assert data["events_detected"] >= 1
    assert data["events"][0]["is_anomalous"] is True
    assert data["events"][0]["magnitude_z_score"] is not None
    assert data["health_score"] is not None


def test_integration_two_sensor_correlation_flow(client: TestClient, seeded_context: dict):
    """Verify coordinated signals from PZT-Z1-01 and PZT-Z1-02 trigger cross-sensor correlation."""
    sensor1 = VirtualPZTSensor(sensor_id="PZT-Z1-01", zone_name=seeded_context["zone1_name"])
    sensor2 = VirtualPZTSensor(sensor_id="PZT-Z1-02", zone_name=seeded_context["zone1_name"])

    # Generate physically related signals (5ms TDOA)
    s1, s2, _ = generate_correlated_pair(
        sample_count=1000,
        sample_rate_hz=1000.0,
        peak_amp=4.5,
        tdoa_seconds=0.005,
        seed=100,
    )

    common_time = datetime.now(timezone.utc)

    p1 = sensor1.generate_payload(samples=s1, timestamp=common_time)
    r1 = client.post("/api/v1/telemetry", json=p1)
    assert r1.status_code == 200
    assert r1.json()["events_detected"] >= 1

    p2 = sensor2.generate_payload(samples=s2, timestamp=common_time)
    r2 = client.post("/api/v1/telemetry", json=p2)
    assert r2.status_code == 200
    assert r2.json()["events_detected"] >= 1

    # Backend cross-sensor correlation should be confirmed upon second sensor ingestion
    assert r2.json()["cross_sensor_correlation_confirmed"] is True
