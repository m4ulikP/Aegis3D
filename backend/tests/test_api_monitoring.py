"""Unit and integration tests for Aegis3D Step 11: Monitoring & Health REST APIs."""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.health.types import SHI_PROTOTYPE_DISCLAIMER
from app.main import app
from app.models.alert import Alert
from app.models.baseline import Baseline
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    EventSeverity,
    EventSourceType,
    EventStatus,
    HealthStatus,
    HealthTrend,
    SessionMode,
    SessionStatus,
)
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.schemas.zone import CORRELATION_NOTE_TEXT


@pytest.fixture(name="db_session")
def db_session_fixture():
    """In-memory SQLite database session fixture with StaticPool for thread-safe test sharing."""
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


@pytest.fixture(name="seeded_data")
def seeded_data_fixture(db_session: Session):
    """Fixture seeding Zone, MonitoringSession, Baseline, Events, HealthSnapshots, and Alerts."""
    now = datetime.now(timezone.utc)

    zone = Zone(name="Zone 1 - North Wing", floor="Floor 2", description="Primary structural test zone")
    zone2 = Zone(name="Zone 2 - South Wing", floor="Floor 1", description="Secondary zone")
    db_session.add_all([zone, zone2])
    db_session.commit()

    msession = MonitoringSession(
        name="Session 2026-09",
        mode=SessionMode.LIVE,
        status=SessionStatus.RUNNING,
        started_at=now - timedelta(hours=2),
    )
    db_session.add(msession)
    db_session.commit()

    baseline = Baseline(
        zone_id=zone.id,
        mean_magnitude=1.0,
        std_magnitude=0.1,
        mean_energy=10.0,
        std_energy=1.0,
        normal_event_rate=0.01,
        valid_from=now - timedelta(days=30),
    )
    db_session.add(baseline)
    db_session.commit()

    # Seed events
    evt1 = Event(
        session_id=msession.id,
        zone_id=zone.id,
        source_type=EventSourceType.SENSOR,
        source_id="PZT-01",
        timestamp=now - timedelta(minutes=10),
        magnitude=5.0,  # Anomalous magnitude
        energy=50.0,
        duration_ms=30.0,
        frequency_hz=150000.0,
        severity=EventSeverity.HIGH,
        status=EventStatus.DETECTED,
    )
    evt2 = Event(
        session_id=msession.id,
        zone_id=zone.id,
        source_type=EventSourceType.SENSOR,
        source_id="PZT-02",
        timestamp=now - timedelta(minutes=10) + timedelta(milliseconds=10),  # Correlated time
        magnitude=4.8,
        energy=48.0,
        duration_ms=28.0,
        frequency_hz=148000.0,
        severity=EventSeverity.HIGH,
        status=EventStatus.DETECTED,
    )
    db_session.add_all([evt1, evt2])
    db_session.commit()

    # Seed health snapshot
    snapshot = HealthSnapshot(
        session_id=msession.id,
        zone_id=zone.id,
        timestamp=now - timedelta(minutes=5),
        score=75.0,
        status=HealthStatus.MONITOR,
        trend=HealthTrend.STABLE,
        reason="Minor elevated observations detected",
        evidence={"anomalous_events": 2},
    )
    db_session.add(snapshot)
    db_session.commit()

    # Seed alert
    alert = Alert(
        health_snapshot_id=snapshot.id,
        zone_id=zone.id,
        timestamp=now - timedelta(minutes=5),
        severity=AlertSeverity.MEDIUM,
        title="Elevated Structural Activity",
        message="Zone 1 exhibits persistent anomalous reflections",
        status=AlertStatus.ACTIVE,
    )
    db_session.add(alert)
    db_session.commit()

    return {
        "zone_id": zone.id,
        "zone2_id": zone2.id,
        "session_id": msession.id,
        "event_ids": [evt1.id, evt2.id],
        "snapshot_id": snapshot.id,
        "alert_id": alert.id,
    }


# ============================================================================
# 1. ZONES ENDPOINTS TESTS
# ============================================================================

def test_list_zones_empty(client: TestClient):
    """Test GET /api/v1/zones returns empty list when DB has no zones."""
    response = client.get("/api/v1/zones")
    assert response.status_code == 200
    assert response.json() == []


def test_list_zones_populated(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones returns all zones."""
    response = client.get("/api/v1/zones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Zone 1 - North Wing"
    assert data[1]["name"] == "Zone 2 - South Wing"


def test_get_zone_detail_success(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones/{zone_id} returns zone detail metadata."""
    response = client.get(f"/api/v1/zones/{seeded_data['zone_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == seeded_data["zone_id"]
    assert data["name"] == "Zone 1 - North Wing"
    assert data["event_count"] == 2
    assert data["active_alert_count"] == 1
    assert data["latest_health_status"] == "MONITOR"


def test_get_zone_detail_not_found(client: TestClient):
    """Test GET /api/v1/zones/{zone_id} returns 404 for missing zone."""
    response = client.get("/api/v1/zones/999999")
    assert response.status_code == 404
    assert "Zone with id 999999 not found" in response.json()["detail"]


# ============================================================================
# 2. ZONE EVENTS ENDPOINT TESTS
# ============================================================================

def test_get_zone_events_success(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones/{zone_id}/events returns zone events."""
    response = client.get(f"/api/v1/zones/{seeded_data['zone_id']}/events")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["source_id"] in ["PZT-01", "PZT-02"]


def test_get_zone_events_filtered(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones/{zone_id}/events with limit and severity filters."""
    response = client.get(f"/api/v1/zones/{seeded_data['zone_id']}/events?limit=1&severity=HIGH")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_zone_events_not_found(client: TestClient):
    """Test GET /api/v1/zones/{zone_id}/events returns 404 for missing zone."""
    response = client.get("/api/v1/zones/999999/events")
    assert response.status_code == 404


# ============================================================================
# 3. ZONE HEALTH (SHI) ENDPOINT TESTS
# ============================================================================

def test_get_zone_health_success(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones/{zone_id}/health exposes SHI result and disclaimer."""
    response = client.get(f"/api/v1/zones/{seeded_data['zone_id']}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["zone_id"] == seeded_data["zone_id"]
    assert "score" in data
    assert "status" in data
    assert "trend" in data
    assert "reason" in data
    assert "timestamp" in data
    assert "disclaimer" in data
    assert SHI_PROTOTYPE_DISCLAIMER in data["disclaimer"]


def test_get_zone_health_not_found(client: TestClient):
    """Test GET /api/v1/zones/{zone_id}/health returns 404 for missing zone."""
    response = client.get("/api/v1/zones/999999/health")
    assert response.status_code == 404


# ============================================================================
# 4. ZONE TREND ENDPOINT TESTS
# ============================================================================

def test_get_zone_trend_success(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones/{zone_id}/trend exposes deterministic trend evaluation."""
    response = client.get(f"/api/v1/zones/{seeded_data['zone_id']}/trend")
    assert response.status_code == 200
    data = response.json()
    assert data["zone_id"] == seeded_data["zone_id"]
    assert "overall_trend_direction" in data
    assert "earlier_period" in data
    assert "later_period" in data
    assert data["overall_trend_direction"] in ["STABLE", "INCREASING", "DECREASING", "INSUFFICIENT_DATA"]


def test_get_zone_trend_not_found(client: TestClient):
    """Test GET /api/v1/zones/{zone_id}/trend returns 404 for missing zone."""
    response = client.get("/api/v1/zones/999999/trend")
    assert response.status_code == 404


# ============================================================================
# 5. ZONE CORRELATION ENDPOINT TESTS
# ============================================================================

def test_get_zone_correlation_success(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/zones/{zone_id}/correlation exposes persistence & 2-PZT correlation."""
    response = client.get(f"/api/v1/zones/{seeded_data['zone_id']}/correlation")
    assert response.status_code == 200
    data = response.json()
    assert data["zone_id"] == seeded_data["zone_id"]
    assert "temporal_persistence" in data
    assert "correlated_groups_count" in data
    assert "cross_sensor_groups_count" in data
    assert "note" in data
    assert CORRELATION_NOTE_TEXT in data["note"]


def test_get_zone_correlation_not_found(client: TestClient):
    """Test GET /api/v1/zones/{zone_id}/correlation returns 404 for missing zone."""
    response = client.get("/api/v1/zones/999999/correlation")
    assert response.status_code == 404


# ============================================================================
# 6. ALERTS ENDPOINT TESTS
# ============================================================================

def test_list_alerts_empty(client: TestClient):
    """Test GET /api/v1/alerts returns empty list when DB has no alerts."""
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    assert response.json() == []


def test_list_alerts_populated(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/alerts returns alerts list with filtering."""
    response = client.get(f"/api/v1/alerts?zone_id={seeded_data['zone_id']}&status=ACTIVE")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Elevated Structural Activity"
    assert data[0]["severity"] == "MEDIUM"


# ============================================================================
# 7. HEALTH SUMMARY ENDPOINT TESTS
# ============================================================================

def test_get_health_summary_empty(client: TestClient):
    """Test GET /api/v1/health/summary with empty database."""
    response = client.get("/api/v1/health/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_zones"] == 0
    assert data["active_alerts_count"] == 0
    assert data["recent_events_count"] == 0
    assert data["latest_timestamp"] is None


def test_get_health_summary_populated(client: TestClient, seeded_data: dict):
    """Test GET /api/v1/health/summary with populated database."""
    response = client.get("/api/v1/health/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_zones"] == 2
    assert data["active_alerts_count"] == 1
    assert data["recent_events_count"] == 2
    assert data["health_status_counts"]["MONITOR"] == 1
    assert data["health_status_counts"]["NORMAL"] == 1
    assert data["latest_timestamp"] is not None
