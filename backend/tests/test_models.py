from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateTable

from app.db.base import Base
from app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    Baseline,
    Event,
    EventSeverity,
    EventSourceType,
    EventStatus,
    HealthSnapshot,
    HealthStatus,
    HealthTrend,
    MonitoringSession,
    SessionMode,
    SessionStatus,
    Zone,
)


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_imports():
    """Verify all domain models and enums can be imported cleanly."""
    assert Zone is not None
    assert MonitoringSession is not None
    assert Event is not None
    assert Baseline is not None
    assert HealthSnapshot is not None
    assert Alert is not None


def test_enum_values():
    """Verify enum values match domain specifications."""
    assert list(SessionMode) == ["LIVE", "SIMULATION", "REPLAY"]
    assert list(SessionStatus) == ["PLANNED", "RUNNING", "COMPLETED", "CANCELLED"]
    assert list(EventSourceType) == ["SIMULATOR", "SENSOR", "IMPORTED"]
    assert list(EventSeverity) == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert list(EventStatus) == ["DETECTED", "REVIEWED", "DISMISSED"]
    assert list(HealthStatus) == [
        "NORMAL",
        "MONITOR",
        "INSPECTION_ADVISED",
        "HIGH_PRIORITY_INSPECTION",
    ]
    assert list(HealthTrend) == ["STABLE", "INCREASING", "DECREASING"]
    assert list(AlertSeverity) == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert list(AlertStatus) == ["ACTIVE", "ACKNOWLEDGED", "RESOLVED"]


def test_zone_creation_and_fields(session: Session):
    """Test Zone model required and optional fields."""
    zone = Zone(name="Beam Section A", floor="Level 2", description="Main structural beam")
    session.add(zone)
    session.commit()

    assert zone.id is not None
    assert zone.name == "Beam Section A"
    assert zone.floor == "Level 2"
    assert zone.description == "Main structural beam"
    assert zone.created_at is not None


def test_monitoring_session_creation(session: Session):
    """Test MonitoringSession model fields (without zone_id dependency)."""
    session_obj = MonitoringSession(
        name="Test Run 01",
        mode=SessionMode.SIMULATION,
        status=SessionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    session.add(session_obj)
    session.commit()

    assert session_obj.id is not None
    assert session_obj.name == "Test Run 01"
    assert session_obj.mode == SessionMode.SIMULATION
    assert session_obj.status == SessionStatus.RUNNING
    assert session_obj.started_at is not None
    assert session_obj.ended_at is None
    # Verify zone_id attribute does not exist on MonitoringSession
    assert not hasattr(session_obj, "zone_id")


def test_event_generic_sources_and_relationships(session: Session):
    """Test Event model hardware independence (SIM-01, PZT-01) and foreign keys."""
    zone = Zone(name="Column C3")
    msession = MonitoringSession(name="Live Run", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    session.add_all([zone, msession])
    session.commit()

    event = Event(
        session_id=msession.id,
        zone_id=zone.id,
        source_type=EventSourceType.SENSOR,
        source_id="PZT-01",
        correlation_id="CORR-101",
        timestamp=datetime.now(timezone.utc),
        magnitude=4.2,
        energy=120.5,
        duration_ms=15.0,
        frequency_hz=150000.0,
        severity=EventSeverity.HIGH,
        status=EventStatus.DETECTED,
        metadata_json={"raw_channel": 1, "gain_db": 20},
    )
    session.add(event)
    session.commit()

    assert event.id is not None
    assert event.source_id == "PZT-01"
    assert event.metadata_json == {"raw_channel": 1, "gain_db": 20}
    assert event.zone.name == "Column C3"
    assert event.session.name == "Live Run"
    assert event in zone.events
    assert event in msession.events


def test_baseline_creation(session: Session):
    """Test Baseline model statistical fields."""
    zone = Zone(name="Zone 1")
    session.add(zone)
    session.commit()

    baseline = Baseline(
        zone_id=zone.id,
        mean_magnitude=1.5,
        std_magnitude=0.2,
        mean_energy=50.0,
        std_energy=5.0,
        normal_event_rate=2.5,
    )
    session.add(baseline)
    session.commit()

    assert baseline.id is not None
    assert baseline.zone_id == zone.id
    assert baseline.valid_until is None
    assert baseline in zone.baselines


def test_health_snapshot_and_alerts_relationships(session: Session):
    """Test HealthSnapshot belongs to Zone & Session, and has many Alerts."""
    zone = Zone(name="Bridge Pier 4")
    msession = MonitoringSession(
        name="Replay Test", mode=SessionMode.REPLAY, status=SessionStatus.COMPLETED
    )
    session.add_all([zone, msession])
    session.commit()

    snapshot = HealthSnapshot(
        session_id=msession.id,
        zone_id=zone.id,
        timestamp=datetime.now(timezone.utc),
        score=45.0,
        status=HealthStatus.INSPECTION_ADVISED,
        trend=HealthTrend.DECREASING,
        reason="Elevated event frequency over 10m window",
        evidence={
            "event_frequency": "HIGH",
            "baseline_deviation": "HIGH",
            "persistence": "MEDIUM",
        },
    )
    session.add(snapshot)
    session.commit()

    alert = Alert(
        health_snapshot_id=snapshot.id,
        zone_id=zone.id,
        timestamp=datetime.now(timezone.utc),
        severity=AlertSeverity.HIGH,
        title="Inspection Advised for Pier 4",
        message="Structural health score dropped to 45.0.",
        status=AlertStatus.ACTIVE,
    )
    session.add(alert)
    session.commit()

    assert alert.id is not None
    assert alert.health_snapshot.score == 45.0
    assert alert.zone.name == "Bridge Pier 4"
    assert len(snapshot.alerts) == 1
    assert snapshot.alerts[0].title == "Inspection Advised for Pier 4"
    assert snapshot in zone.health_snapshots
    assert snapshot in msession.health_snapshots
    assert alert in zone.alerts


def test_cascading_deletes(session: Session):
    """Verify deleting a Zone cascades appropriately to dependent entities."""
    zone = Zone(name="Zone Deletable")
    msession = MonitoringSession(name="S1", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    session.add_all([zone, msession])
    session.commit()

    event = Event(
        session_id=msession.id,
        zone_id=zone.id,
        source_type=EventSourceType.SIMULATOR,
        source_id="SIM-01",
        timestamp=datetime.now(timezone.utc),
        severity=EventSeverity.LOW,
        status=EventStatus.DETECTED,
    )
    session.add(event)
    session.commit()

    event_id = event.id
    session.delete(zone)
    session.commit()

    # Query deleted event
    deleted_event = session.get(Event, event_id)
    assert deleted_event is None


def test_postgresql_dialect_schema_compilation():
    """Verify all 6 core domain models compile valid PostgreSQL DDL statements."""
    models = [Zone, MonitoringSession, Event, Baseline, HealthSnapshot, Alert]
    for model in models:
        ddl_str = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
        assert ddl_str is not None
        assert model.__tablename__ in ddl_str
