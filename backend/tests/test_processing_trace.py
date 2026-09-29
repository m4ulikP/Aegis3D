"""Unit and integration tests for Telemetry Processing Inspector trace API and service."""

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
from app.services.telemetry_service import TelemetryService


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


@pytest.fixture(name="seeded_context")
def seeded_context_fixture(db_session: Session):
    """Fixture seeding standard demo zones, baseline stats, and active monitoring session."""
    TelemetryService.clear_processing_traces()
    now = datetime.now(timezone.utc)

    # Zones
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


def test_get_processing_trace_unknown_identifier_returns_404(client: TestClient, seeded_context: dict):
    """Test retrieving trace with nonexistent identifier returns HTTP 404."""
    resp = client.get("/api/v1/telemetry/999999/processing-trace")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    resp_str = client.get("/api/v1/telemetry/NONEXISTENT-SENSOR/processing-trace")
    assert resp_str.status_code == 404


def test_get_processing_trace_quiet_normal_telemetry(
    client: TestClient, seeded_context: dict, db_session: Session
):
    """Test trace for normal below-threshold telemetry does not falsely report anomaly or correlation."""
    samples = (np.random.RandomState(42).normal(0.0, 0.05, 500)).tolist()

    payload = {
        "sensor_id": "PZT-Z05",
        "zone_name": seeded_context["zone1_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 10,
        "samples": samples,
    }

    # 1. Ingest telemetry
    ingest_resp = client.post("/api/v1/telemetry", json=payload)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["events_detected"] == 0

    # 2. Retrieve trace via 'latest' and sensor_id
    trace_resp = client.get("/api/v1/telemetry/latest/processing-trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    # Verify Metadata
    assert trace["metadata"]["sensor_id"] == "PZT-Z05"
    assert trace["metadata"]["zone_id"] == seeded_context["zone1_id"]
    assert trace["metadata"]["sequence"] == 10
    assert trace["metadata"]["sample_rate_hz"] == 1000.0
    assert trace["metadata"]["samples_count"] == 500
    assert trace["metadata"]["event_id"] is None

    # Verify Ingestion
    assert trace["ingestion"]["sensor_id"] == "PZT-Z05"
    assert len(trace["ingestion"]["samples_bounded"]) == 500
    assert trace["ingestion"]["peak_amplitude"] > 0.0

    # Verify Conditioning
    assert trace["conditioning"]["dc_removal_applied"] is True
    assert trace["conditioning"]["dc_offset_removed"] is not None
    assert trace["conditioning"]["filter_applied"] is True
    assert trace["conditioning"]["filter_type"] == "MOVING_AVERAGE"
    assert len(trace["conditioning"]["conditioned_samples_bounded"]) == 500

    # Verify Event Detection
    assert trace["event_detection"]["events_detected"] is False
    assert trace["event_detection"]["events_detected_count"] == 0
    assert len(trace["event_detection"]["detected_windows"]) == 0

    # Verify Features is None
    assert trace["features"] is None

    # Verify Baseline exists
    assert trace["baseline"]["baseline_available"] is True
    assert trace["baseline"]["mean_magnitude"] == 1.20
    assert trace["baseline"]["std_magnitude"] == 0.15

    # Verify Anomaly stage was NOT evaluated (no event)
    assert trace["anomaly"]["evaluated"] is False
    assert trace["anomaly"]["is_anomalous"] is False

    # Verify Persistence & Correlation not falsely flagged
    assert trace["persistence"]["evaluated"] is False
    assert trace["persistence"]["is_persistent"] is False
    assert trace["correlation"]["evaluated"] is False
    assert trace["correlation"]["is_cross_sensor_correlated"] is False

    # Verify Alert not generated
    assert trace["alert"]["alert_generated"] is False

    # Also check retrieval by sensor_id
    trace_sensor = client.get("/api/v1/telemetry/PZT-Z05/processing-trace").json()
    assert trace_sensor["metadata"]["trace_id"] == trace["metadata"]["trace_id"]


def test_get_processing_trace_burst_signal_anomaly_and_alert(
    client: TestClient, seeded_context: dict, db_session: Session
):
    """Test processing trace contains real anomaly evidence, feature extraction, and alert details."""
    samples = np.zeros(1000)
    t = np.linspace(0, 0.1, 100, endpoint=False)
    # Burst with amplitude 5.0 (z-score will be > 20 against baseline mean 1.20, std 0.15)
    samples[300:400] = 5.0 * np.sin(2 * np.pi * 100 * t)

    payload = {
        "sensor_id": "PZT-Z05",
        "zone_name": seeded_context["zone1_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 101,
        "samples": samples.tolist(),
        "detection_threshold": 1.0,
    }

    # 1. Ingest
    ingest_resp = client.post("/api/v1/telemetry", json=payload)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["events_detected"] >= 1
    event_id = ingest_data["events"][0]["event_id"]

    # 2. Retrieve trace by event_id
    trace_resp = client.get(f"/api/v1/telemetry/{event_id}/processing-trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    # Metadata
    assert trace["metadata"]["event_id"] == event_id
    assert trace["metadata"]["sensor_id"] == "PZT-Z05"
    assert trace["metadata"]["sequence"] == 101

    # Ingestion & Conditioning
    assert trace["ingestion"]["samples_count"] == 1000
    assert trace["conditioning"]["dc_removal_applied"] is True
    assert trace["conditioning"]["filter_applied"] is True

    # Event Detection & Windows
    assert trace["event_detection"]["events_detected"] is True
    assert trace["event_detection"]["events_detected_count"] >= 1
    assert len(trace["event_detection"]["detected_windows"]) >= 1
    win = trace["event_detection"]["detected_windows"][0]
    assert win["peak_amplitude"] > 3.0
    assert win["duration_ms"] > 0

    # Feature Extraction
    assert trace["features"] is not None
    assert trace["features"]["event_id"] == event_id
    assert trace["features"]["peak_amplitude"] > 3.0
    assert trace["features"]["energy"] > 0.0
    assert trace["features"]["frequency_hz"] is not None

    # Baseline & Anomaly Evidence
    assert trace["baseline"]["baseline_available"] is True
    assert trace["anomaly"]["evaluated"] is True
    assert trace["anomaly"]["is_anomalous"] is True
    assert trace["anomaly"]["magnitude_z_score"] > 3.0
    assert len(trace["anomaly"]["reasons"]) > 0

    # Health / SHI
    assert trace["health"]["evaluated"] is True
    assert trace["health"]["health_score"] is not None
    assert trace["health"]["health_status"] is not None
    assert "prototype evidence-based monitoring indicator" in trace["health"]["disclaimer"]


def test_get_processing_trace_cross_sensor_correlation(
    client: TestClient, seeded_context: dict, db_session: Session
):
    """Test processing trace captures cross-sensor correlation evidence when multi-transducer events occur."""
    now = datetime.now(timezone.utc)
    t = np.linspace(0, 0.05, 50, endpoint=False)

    # 1. First transducer burst in Zone 2
    s1 = np.zeros(500)
    s1[100:150] = 3.5 * np.sin(2 * np.pi * 120 * t)
    p1 = {
        "sensor_id": "PZT-Z01",
        "zone_name": seeded_context["zone2_name"],
        "timestamp": now.isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 1,
        "samples": s1.tolist(),
        "detection_threshold": 0.5,
    }
    r1 = client.post("/api/v1/telemetry", json=p1)
    assert r1.status_code == 200

    # 2. Second transducer burst in Zone 2 within tolerance (10ms later)
    s2 = np.zeros(500)
    s2[100:150] = 3.2 * np.sin(2 * np.pi * 120 * t)
    p2 = {
        "sensor_id": "PZT-Z02",
        "zone_name": seeded_context["zone2_name"],
        "timestamp": now.isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 2,
        "samples": s2.tolist(),
        "detection_threshold": 0.5,
    }
    r2 = client.post("/api/v1/telemetry", json=p2)
    assert r2.status_code == 200

    # 3. Retrieve trace for latest telemetry (PZT-Z02)
    trace_resp = client.get("/api/v1/telemetry/latest/processing-trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    assert trace["metadata"]["sensor_id"] == "PZT-Z02"
    assert trace["correlation"]["evaluated"] is True
    assert trace["correlation"]["is_cross_sensor_correlated"] is True
    assert len(trace["correlation"]["participating_sensors"]) >= 2
    assert "PZT-Z01" in trace["correlation"]["participating_sensors"]
    assert "PZT-Z02" in trace["correlation"]["participating_sensors"]


def test_get_processing_trace_reconstruction_from_database_after_cache_cleared(
    client: TestClient, seeded_context: dict, db_session: Session
):
    """Test that trace can be accurately reconstructed from database records even when in-memory cache is wiped."""
    samples = np.zeros(500)
    t = np.linspace(0, 0.05, 50, endpoint=False)
    samples[100:150] = 4.0 * np.sin(2 * np.pi * 100 * t)

    payload = {
        "sensor_id": "PZT-Z05",
        "zone_name": seeded_context["zone1_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_rate_hz": 1000.0,
        "sequence": 77,
        "samples": samples.tolist(),
        "detection_threshold": 0.8,
    }

    # Ingest
    ingest_resp = client.post("/api/v1/telemetry", json=payload)
    assert ingest_resp.status_code == 200
    event_id = ingest_resp.json()["events"][0]["event_id"]

    # Clear in-memory cache completely
    TelemetryService.clear_processing_traces()

    # Query trace by event_id - should reconstruct from database records without running pipeline
    trace_resp = client.get(f"/api/v1/telemetry/{event_id}/processing-trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    assert trace["metadata"]["event_id"] == event_id
    assert trace["metadata"]["sensor_id"] == "PZT-Z05"
    assert trace["metadata"]["sequence"] == 77
    assert trace["features"]["peak_amplitude"] > 3.0
    assert trace["anomaly"]["evaluated"] is True
    assert trace["anomaly"]["is_anomalous"] is True


def test_processing_trace_is_read_only_and_does_not_mutate_state(
    client: TestClient, seeded_context: dict, db_session: Session
):
    """Test calling get_processing_trace does not create new database events or modify database counts."""
    samples = np.zeros(500)
    t = np.linspace(0, 0.05, 50, endpoint=False)
    samples[100:150] = 3.0 * np.sin(2 * np.pi * 100 * t)

    payload = {
        "sensor_id": "PZT-Z05",
        "zone_name": seeded_context["zone1_name"],
        "sample_rate_hz": 1000.0,
        "sequence": 88,
        "samples": samples.tolist(),
    }
    client.post("/api/v1/telemetry", json=payload)

    initial_event_count = db_session.query(Event).count()
    initial_alert_count = db_session.query(Alert).count()
    initial_health_count = db_session.query(HealthSnapshot).count()

    # Call processing-trace multiple times
    for _ in range(5):
        resp = client.get("/api/v1/telemetry/latest/processing-trace")
        assert resp.status_code == 200

    # Ensure no database mutations occurred
    assert db_session.query(Event).count() == initial_event_count
    assert db_session.query(Alert).count() == initial_alert_count
    assert db_session.query(HealthSnapshot).count() == initial_health_count
