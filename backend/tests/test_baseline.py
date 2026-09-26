"""Tests for Aegis3D Step 6 Statistical Baseline Engine."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.baseline import (
    DEFAULT_MIN_EVENTS,
    BaselineStatistics,
    InsufficientDataError,
    InvalidTimeWindowError,
    ZoneNotFoundError,
    calculate_baseline_statistics,
)
from app.db.base import Base
from app.models import (
    Baseline,
    Event,
    EventSeverity,
    EventSourceType,
    EventStatus,
    MonitoringSession,
    SessionMode,
    SessionStatus,
    Zone,
)
from app.repositories import BaselineRepository
from app.services import BaselineService


@pytest.fixture(name="sqlite_session")
def sqlite_session_fixture():
    """In-memory SQLite session fixture for fast isolated database testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone for comparison across SQLite and PostgreSQL."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# -----------------------------------------------------------------------------
# PURE STATISTICAL CALCULATION TESTS
# -----------------------------------------------------------------------------

def test_calculate_baseline_statistics_correct_metrics():
    """Verify mean magnitude, mean energy, std devs, and normal event rate calculations."""
    valid_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 0, 1, 40, tzinfo=timezone.utc)  # 100 seconds window

    magnitudes = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    energies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    stats = calculate_baseline_statistics(
        magnitudes=magnitudes,
        energies=energies,
        valid_from=valid_from,
        valid_until=valid_until,
        min_events=10,
    )

    assert isinstance(stats, BaselineStatistics)
    assert stats.mean_magnitude == pytest.approx(5.5)
    assert stats.std_magnitude == pytest.approx(2.8722813232690143)  # population std (ddof=0)
    assert stats.mean_energy == pytest.approx(55.0)
    assert stats.std_energy == pytest.approx(28.722813232690143)
    assert stats.normal_event_rate == pytest.approx(0.1)  # 10 events / 100 seconds
    assert stats.event_count == 10
    assert stats.valid_from == valid_from
    assert stats.valid_until == valid_until


def test_calculate_baseline_identical_values_zero_std():
    """Verify standard deviation resolves to deterministic 0.0 for identical magnitude/energy values."""
    valid_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc)

    magnitudes = [4.5] * 10
    energies = [120.0] * 10

    stats = calculate_baseline_statistics(
        magnitudes=magnitudes,
        energies=energies,
        valid_from=valid_from,
        valid_until=valid_until,
        min_events=10,
    )

    assert stats.mean_magnitude == pytest.approx(4.5)
    assert stats.std_magnitude == 0.0
    assert stats.mean_energy == pytest.approx(120.0)
    assert stats.std_energy == 0.0


def test_calculate_baseline_insufficient_data():
    """Verify InsufficientDataError is raised when qualifying events < min_events."""
    valid_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    magnitudes = [1.0] * 5
    energies = [10.0] * 5

    with pytest.raises(InsufficientDataError) as exc_info:
        calculate_baseline_statistics(
            magnitudes=magnitudes,
            energies=energies,
            valid_from=valid_from,
            valid_until=valid_until,
            min_events=10,
        )

    assert "Insufficient qualifying events" in str(exc_info.value)
    assert "found 5, minimum required is 10" in str(exc_info.value)


def test_calculate_baseline_invalid_time_window():
    """Verify InvalidTimeWindowError is raised when valid_until <= valid_from."""
    valid_from = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)  # inverted window

    magnitudes = [1.0] * 10
    energies = [10.0] * 10

    with pytest.raises(InvalidTimeWindowError) as exc_info:
        calculate_baseline_statistics(
            magnitudes=magnitudes,
            energies=energies,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    assert "valid_until must be strictly after valid_from" in str(exc_info.value)


def test_calculate_baseline_zero_duration_window():
    """Verify InvalidTimeWindowError is raised when valid_from == valid_until."""
    t_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(InvalidTimeWindowError) as exc_info:
        calculate_baseline_statistics(
            magnitudes=[1.0] * 10,
            energies=[10.0] * 10,
            valid_from=t_now,
            valid_until=t_now,
        )

    assert "valid_until must be strictly after valid_from" in str(exc_info.value)


# -----------------------------------------------------------------------------
# SERVICE & REPOSITORY INTEGRATION TESTS
# -----------------------------------------------------------------------------

def test_baseline_service_build_and_persist(sqlite_session: Session):
    """Verify BaselineService computes and persists a valid Baseline entity in the DB."""
    zone = Zone(name="Beam B-1", floor="Level 1")
    msession = MonitoringSession(name="Run 1", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone, msession])
    sqlite_session.commit()

    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_from = base_time
    valid_until = base_time + timedelta(seconds=100)

    # Seed 10 qualifying events inside time window
    for i in range(10):
        evt = Event(
            session_id=msession.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="S-01",
            timestamp=base_time + timedelta(seconds=i * 10),
            magnitude=2.0 + i,
            energy=20.0 + (i * 10),
            severity=EventSeverity.LOW,
            status=EventStatus.DETECTED,
        )
        sqlite_session.add(evt)
    sqlite_session.commit()

    service = BaselineService(sqlite_session)
    baseline = service.build_baseline(
        zone_id=zone.id,
        valid_from=valid_from,
        valid_until=valid_until,
    )

    assert baseline.id is not None
    assert baseline.zone_id == zone.id
    assert baseline.mean_magnitude == pytest.approx(6.5)
    assert baseline.mean_energy == pytest.approx(65.0)
    assert baseline.normal_event_rate == pytest.approx(0.1)  # 10 events / 100 sec
    assert _ensure_utc(baseline.valid_from) == valid_from
    assert _ensure_utc(baseline.valid_until) == valid_until

    # Verify entity is retrievable via repository
    repo = BaselineRepository(sqlite_session)
    latest = repo.get_latest_for_zone(zone.id)
    assert latest is not None
    assert latest.id == baseline.id


def test_baseline_service_time_window_filtering(sqlite_session: Session):
    """Verify events outside the specified [valid_from, valid_until] window are excluded."""
    zone = Zone(name="Column C-1")
    msession = MonitoringSession(name="Run 2", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone, msession])
    sqlite_session.commit()

    valid_from = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

    # 5 events BEFORE window
    for i in range(5):
        evt = Event(
            session_id=msession.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="S-01",
            timestamp=valid_from - timedelta(minutes=10 - i),
            magnitude=100.0,
            energy=1000.0,
            severity=EventSeverity.CRITICAL,
            status=EventStatus.DETECTED,
        )
        sqlite_session.add(evt)

    # 10 events INSIDE window
    for i in range(10):
        evt = Event(
            session_id=msession.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="S-01",
            timestamp=valid_from + timedelta(minutes=i * 5),
            magnitude=2.0,
            energy=50.0,
            severity=EventSeverity.LOW,
            status=EventStatus.DETECTED,
        )
        sqlite_session.add(evt)

    # 5 events AFTER window
    for i in range(5):
        evt = Event(
            session_id=msession.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="S-01",
            timestamp=valid_until + timedelta(minutes=i + 1),
            magnitude=100.0,
            energy=1000.0,
            severity=EventSeverity.CRITICAL,
            status=EventStatus.DETECTED,
        )
        sqlite_session.add(evt)

    sqlite_session.commit()

    service = BaselineService(sqlite_session)
    baseline = service.build_baseline(
        zone_id=zone.id,
        valid_from=valid_from,
        valid_until=valid_until,
    )

    # Should only average the 10 events inside window (magnitude 2.0, energy 50.0)
    assert baseline.mean_magnitude == pytest.approx(2.0)
    assert baseline.mean_energy == pytest.approx(50.0)
    assert baseline.std_magnitude == 0.0
    assert baseline.std_energy == 0.0


def test_baseline_service_zone_filtering(sqlite_session: Session):
    """Verify events belonging to other zones are excluded from baseline computation."""
    zone_a = Zone(name="Zone A")
    zone_b = Zone(name="Zone B")
    msession = MonitoringSession(name="Run 3", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone_a, zone_b, msession])
    sqlite_session.commit()

    valid_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    # Seed 10 events for Zone A (magnitude=3.0)
    for i in range(10):
        sqlite_session.add(
            Event(
                session_id=msession.id,
                zone_id=zone_a.id,
                source_type=EventSourceType.SENSOR,
                source_id="S-01",
                timestamp=valid_from + timedelta(minutes=i),
                magnitude=3.0,
                energy=30.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            )
        )

    # Seed 10 events for Zone B (magnitude=99.0)
    for i in range(10):
        sqlite_session.add(
            Event(
                session_id=msession.id,
                zone_id=zone_b.id,
                source_type=EventSourceType.SENSOR,
                source_id="S-02",
                timestamp=valid_from + timedelta(minutes=i),
                magnitude=99.0,
                energy=990.0,
                severity=EventSeverity.HIGH,
                status=EventStatus.DETECTED,
            )
        )
    sqlite_session.commit()

    service = BaselineService(sqlite_session)
    baseline_a = service.build_baseline(zone_id=zone_a.id, valid_from=valid_from, valid_until=valid_until)

    assert baseline_a.zone_id == zone_a.id
    assert baseline_a.mean_magnitude == pytest.approx(3.0)
    assert baseline_a.mean_energy == pytest.approx(30.0)


def test_baseline_service_excludes_dismissed_events(sqlite_session: Session):
    """Verify DISMISSED events are excluded from baseline calculation."""
    zone = Zone(name="Zone Dismiss Test")
    msession = MonitoringSession(name="Run 4", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone, msession])
    sqlite_session.commit()

    valid_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    # 10 valid DETECTED events (magnitude=5.0)
    for i in range(10):
        sqlite_session.add(
            Event(
                session_id=msession.id,
                zone_id=zone.id,
                source_type=EventSourceType.SENSOR,
                source_id="S-01",
                timestamp=valid_from + timedelta(minutes=i),
                magnitude=5.0,
                energy=50.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            )
        )

    # 5 DISMISSED events (magnitude=100.0)
    for i in range(5):
        sqlite_session.add(
            Event(
                session_id=msession.id,
                zone_id=zone.id,
                source_type=EventSourceType.SENSOR,
                source_id="S-01",
                timestamp=valid_from + timedelta(minutes=i + 15),
                magnitude=100.0,
                energy=1000.0,
                severity=EventSeverity.CRITICAL,
                status=EventStatus.DISMISSED,
            )
        )
    sqlite_session.commit()

    service = BaselineService(sqlite_session)
    baseline = service.build_baseline(zone_id=zone.id, valid_from=valid_from, valid_until=valid_until)

    # Should exclude the 5 DISMISSED events and calculate statistics strictly from the 10 DETECTED events
    assert baseline.mean_magnitude == pytest.approx(5.0)
    assert baseline.mean_energy == pytest.approx(50.0)


def test_baseline_service_nonexistent_zone_raises(sqlite_session: Session):
    """Verify ZoneNotFoundError is raised when attempting to build a baseline for a nonexistent zone."""
    service = BaselineService(sqlite_session)
    valid_from = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ZoneNotFoundError) as exc_info:
        service.build_baseline(zone_id=999999, valid_from=valid_from, valid_until=valid_until)

    assert "Zone with id 999999 not found" in str(exc_info.value)
