"""Unit and integration tests for Aegis3D demo dataset seeding mechanism."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seed import (
    DEMO_SESSION_NAME,
    DEMO_ZONE_1_NAME,
    DEMO_ZONE_2_NAME,
    clear_demo_data,
    seed_demo_data,
)
from app.db.session import get_db
from app.main import app
from app.models.alert import Alert
from app.models.baseline import Baseline
from app.models.enums import AlertStatus, EventStatus, HealthStatus, SessionMode, SessionStatus
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.services.health_service import HealthService
from app.services.monitoring_service import MonitoringService


@pytest.fixture(name="db_session")
def db_session_fixture():
    """In-memory SQLite database session fixture with StaticPool for thread-safe test isolation."""
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


def test_seed_demo_data_initial_creation(db_session: Session):
    """Verify that seed_demo_data populates all required entities and relationships."""
    result = seed_demo_data(db_session, reset=False)

    assert result["status"] == "created"
    assert result["zones_created"] == 2
    assert result["events_created"] == 10
    assert result["health_snapshots_created"] == 2
    assert result["alerts_created"] == 1

    # Query DB entities
    zones = db_session.query(Zone).order_by(Zone.id.asc()).all()
    assert len(zones) == 2
    assert zones[0].name == DEMO_ZONE_1_NAME
    assert zones[1].name == DEMO_ZONE_2_NAME

    session = db_session.query(MonitoringSession).filter_by(name=DEMO_SESSION_NAME).first()
    assert session is not None
    assert session.mode == SessionMode.LIVE
    assert session.status == SessionStatus.RUNNING

    baselines = db_session.query(Baseline).all()
    assert len(baselines) == 2

    zone1_events = db_session.query(Event).filter_by(zone_id=zones[0].id).all()
    assert len(zone1_events) == 8

    zone2_events = db_session.query(Event).filter_by(zone_id=zones[1].id).all()
    assert len(zone2_events) == 2

    # Verify relationships navigation
    assert len(zones[0].events) == 8
    assert len(zones[0].baselines) == 1
    assert len(zones[0].health_snapshots) >= 1
    assert len(zones[0].alerts) == 1

    alert = db_session.query(Alert).first()
    assert alert is not None
    assert alert.zone_id == zones[0].id
    assert alert.status == AlertStatus.ACTIVE


def test_seed_demo_data_idempotency(db_session: Session):
    """Verify running seed_demo_data twice does not create duplicate rows."""
    first_run = seed_demo_data(db_session, reset=False)
    assert first_run["status"] == "created"

    second_run = seed_demo_data(db_session, reset=False)
    assert second_run["status"] == "already_seeded"

    # Verify database entity counts remain unchanged
    assert db_session.query(Zone).count() == 2
    assert db_session.query(MonitoringSession).count() == 1
    assert db_session.query(Baseline).count() == 2
    assert db_session.query(Event).count() == 10
    assert db_session.query(HealthSnapshot).count() == 2
    assert db_session.query(Alert).count() == 1


def test_seed_demo_data_reset_option(db_session: Session):
    """Verify reset=True purges existing demo data before re-seeding."""
    seed_demo_data(db_session, reset=False)
    assert db_session.query(Zone).count() == 2

    reset_run = seed_demo_data(db_session, reset=True)
    assert reset_run["status"] == "created"
    assert reset_run["reset_performed"] is True

    # Entities should still be exactly 2 zones, 1 session, 10 events, 2 snapshots, 1 alert
    assert db_session.query(Zone).count() == 2
    assert db_session.query(MonitoringSession).count() == 1
    assert db_session.query(Event).count() == 10
    assert db_session.query(Alert).count() == 1


def test_seed_demo_transaction_rollback_on_failure(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Verify that an exception mid-way through seeding triggers a rollback and leaves no orphaned entities."""
    def _failing_evaluate(*args, **kwargs):
        raise RuntimeError("Simulated failure during health evaluation")

    monkeypatch.setattr(HealthService, "evaluate_zone_health", _failing_evaluate)

    with pytest.raises(RuntimeError, match="Simulated failure during health evaluation"):
        seed_demo_data(db_session, reset=False)

    # Verify atomic rollback: zero entities remain in DB
    assert db_session.query(Zone).count() == 0
    assert db_session.query(MonitoringSession).count() == 0
    assert db_session.query(Baseline).count() == 0
    assert db_session.query(Event).count() == 0
    assert db_session.query(HealthSnapshot).count() == 0
    assert db_session.query(Alert).count() == 0


def test_seeded_data_retrievable_via_rest_api(client: TestClient, db_session: Session):
    """Verify all 8 Step 11 REST API endpoints return coherent responses for seeded demo data."""
    seed_demo_data(db_session, reset=False)

    zones_res = client.get("/api/v1/zones")
    assert zones_res.status_code == 200
    zones_data = zones_res.json()
    assert len(zones_data) == 2
    zone1_id = zones_data[0]["id"]

    zone_detail_res = client.get(f"/api/v1/zones/{zone1_id}")
    assert zone_detail_res.status_code == 200
    zone_detail = zone_detail_res.json()
    assert zone_detail["name"] == DEMO_ZONE_1_NAME
    assert zone_detail["event_count"] == 8
    assert zone_detail["active_alert_count"] == 1

    events_res = client.get(f"/api/v1/zones/{zone1_id}/events")
    assert events_res.status_code == 200
    events_data = events_res.json()
    assert len(events_data) == 8

    health_res = client.get(f"/api/v1/zones/{zone1_id}/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert "score" in health_data
    assert "status" in health_data
    assert health_data["disclaimer"] != ""

    trend_res = client.get(f"/api/v1/zones/{zone1_id}/trend")
    assert trend_res.status_code == 200
    trend_data = trend_res.json()
    assert trend_data["zone_id"] == zone1_id

    corr_res = client.get(f"/api/v1/zones/{zone1_id}/correlation")
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    assert corr_data["zone_id"] == zone1_id

    alerts_res = client.get("/api/v1/alerts")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert len(alerts_data) == 1
    assert alerts_data[0]["title"] == "Cross-Sensor Structural Anomaly Cluster"

    summary_res = client.get("/api/v1/health/summary")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["total_zones"] == 2
    assert summary_data["active_alerts_count"] == 1
