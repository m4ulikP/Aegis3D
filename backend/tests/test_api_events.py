from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import EventSeverity, EventSourceType, EventStatus, SessionMode, SessionStatus
from app.models.event import Event
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


@pytest.fixture(name="seeded_context")
def seeded_context_fixture(db_session: Session):
    """Fixture to seed a Zone and MonitoringSession in the database."""
    zone = Zone(name="Test Zone Alpha", floor="Floor 1", description="Main test area")
    msession = MonitoringSession(
        name="Session 2026-01",
        mode=SessionMode.LIVE,
        status=SessionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add_all([zone, msession])
    db_session.commit()
    db_session.refresh(zone)
    db_session.refresh(msession)

    return {"zone_id": zone.id, "session_id": msession.id}


def test_post_valid_event(client: TestClient, seeded_context: dict, db_session: Session):
    """Test POST /api/v1/events with valid data persists to database and returns HTTP 201."""
    event_payload = {
        "session_id": seeded_context["session_id"],
        "zone_id": seeded_context["zone_id"],
        "source_type": "SENSOR",
        "source_id": "PZT-01",
        "correlation_id": "CORR-TEST-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "magnitude": 5.5,
        "energy": 150.0,
        "duration_ms": 25.0,
        "frequency_hz": 120000.0,
        "severity": "HIGH",
        "status": "DETECTED",
        "metadata": {"sensor_gain": 20, "location_offset": "center"},
    }

    response = client.post("/api/v1/events", json=event_payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["id"] is not None
    assert data["session_id"] == seeded_context["session_id"]
    assert data["zone_id"] == seeded_context["zone_id"]
    assert data["source_id"] == "PZT-01"
    assert data["metadata"] == {"sensor_gain": 20, "location_offset": "center"}

    # Verify event actually exists in database
    db_event = db_session.query(Event).filter(Event.id == data["id"]).first()
    assert db_event is not None
    assert db_event.source_id == "PZT-01"
    assert db_event.magnitude == 5.5
    assert db_event.metadata_json == {"sensor_gain": 20, "location_offset": "center"}


def test_post_invalid_event_negative_values(client: TestClient, seeded_context: dict):
    """Test POST /api/v1/events with invalid negative physical measurements returns HTTP 422."""
    invalid_payload = {
        "session_id": seeded_context["session_id"],
        "zone_id": seeded_context["zone_id"],
        "source_type": "SENSOR",
        "source_id": "PZT-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "magnitude": -10.0,  # Invalid negative magnitude
        "duration_ms": -5.0,  # Invalid negative duration
    }

    response = client.post("/api/v1/events", json=invalid_payload)
    assert response.status_code == 422


def test_post_invalid_event_enum(client: TestClient, seeded_context: dict):
    """Test POST /api/v1/events with invalid source_type enum returns HTTP 422."""
    invalid_payload = {
        "session_id": seeded_context["session_id"],
        "zone_id": seeded_context["zone_id"],
        "source_type": "INVALID_SOURCE",  # Not in EventSourceType enum
        "source_id": "PZT-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post("/api/v1/events", json=invalid_payload)
    assert response.status_code == 422


def test_post_event_nonexistent_session(client: TestClient, seeded_context: dict):
    """Test POST /api/v1/events with nonexistent session_id returns HTTP 404."""
    payload = {
        "session_id": 999999,  # Nonexistent session
        "zone_id": seeded_context["zone_id"],
        "source_type": "SIMULATOR",
        "source_id": "SIM-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 404
    assert "MonitoringSession with id 999999 not found" in response.json()["detail"]


def test_post_event_nonexistent_zone(client: TestClient, seeded_context: dict):
    """Test POST /api/v1/events with nonexistent zone_id returns HTTP 404."""
    payload = {
        "session_id": seeded_context["session_id"],
        "zone_id": 999999,  # Nonexistent zone
        "source_type": "SIMULATOR",
        "source_id": "SIM-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 404
    assert "Zone with id 999999 not found" in response.json()["detail"]


def test_get_existing_event(client: TestClient, seeded_context: dict):
    """Test GET /api/v1/events/{id} returns existing event and HTTP 200."""
    post_payload = {
        "session_id": seeded_context["session_id"],
        "zone_id": seeded_context["zone_id"],
        "source_type": "IMPORTED",
        "source_id": "IMP-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "magnitude": 2.1,
        "energy": 45.0,
    }

    post_resp = client.post("/api/v1/events", json=post_payload)
    assert post_resp.status_code == 201
    created_id = post_resp.json()["id"]

    get_resp = client.get(f"/api/v1/events/{created_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == created_id
    assert data["source_id"] == "IMP-01"
    assert data["magnitude"] == 2.1


def test_get_nonexistent_event(client: TestClient):
    """Test GET /api/v1/events/{id} with nonexistent ID returns HTTP 404."""
    response = client.get("/api/v1/events/999999")
    assert response.status_code == 404
    assert "Event with id 999999 not found" in response.json()["detail"]
