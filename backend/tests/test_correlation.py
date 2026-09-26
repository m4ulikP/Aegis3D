"""Comprehensive test suite for Aegis3D Step 8 Temporal Persistence and 2-PZT Event Correlation."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.correlation import (
    DEFAULT_CORRELATION_TOLERANCE_SECONDS,
    DEFAULT_MIN_ANOMALY_COUNT,
    DEFAULT_MIN_ANOMALY_RATIO,
    DEFAULT_PERSISTENCE_WINDOW_SECONDS,
    AggregatedEvidenceResult,
    CorrelatedEventGroup,
    EvidenceCategory,
    InvalidToleranceError,
    InvalidWindowError,
    TemporalPersistenceResult,
    aggregate_event_evidence,
    correlate_two_pzt_events,
    evaluate_temporal_persistence,
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
from app.services import CorrelationService


@pytest.fixture(name="sqlite_session")
def sqlite_session_fixture():
    """In-memory SQLite session fixture for isolated service testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


# -----------------------------------------------------------------------------
# TEMPORAL PERSISTENCE TESTS
# -----------------------------------------------------------------------------

def test_temporal_persistence_no_anomalies():
    """Verify sequence with all normal events evaluates to no persistence."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"timestamp": t0 + timedelta(seconds=i * 10), "is_anomalous": False}
        for i in range(5)
    ]
    res = evaluate_temporal_persistence(events, window_duration_seconds=300.0)

    assert isinstance(res, TemporalPersistenceResult)
    assert res.is_persistent is False
    assert res.total_events == 5
    assert res.anomalous_events == 0
    assert res.anomaly_ratio == 0.0
    assert res.max_consecutive_anomalies == 0
    assert "No temporal persistence" in res.reasons[0]


def test_temporal_persistence_isolated_anomaly():
    """Verify a single isolated anomaly does not trigger persistence."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"timestamp": t0, "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=10), "is_anomalous": False},
        {"timestamp": t0 + timedelta(seconds=20), "is_anomalous": False},
        {"timestamp": t0 + timedelta(seconds=30), "is_anomalous": False},
        {"timestamp": t0 + timedelta(seconds=40), "is_anomalous": False},
    ]
    res = evaluate_temporal_persistence(
        events,
        window_duration_seconds=300.0,
        min_anomaly_count=3,
        min_anomaly_ratio=0.5,
    )
    assert res.is_persistent is False
    assert res.anomalous_events == 1
    assert res.max_consecutive_anomalies == 1


def test_temporal_persistence_repeated_consecutive_anomalies():
    """Verify repeated consecutive anomalies trigger temporal persistence."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"timestamp": t0, "is_anomalous": False},
        {"timestamp": t0 + timedelta(seconds=10), "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=20), "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=30), "is_anomalous": True},
    ]
    res = evaluate_temporal_persistence(
        events,
        window_duration_seconds=300.0,
        min_anomaly_count=3,
        min_anomaly_ratio=0.5,
    )
    assert res.is_persistent is True
    assert res.anomalous_events == 3
    assert res.total_events == 4
    assert res.anomaly_ratio == pytest.approx(0.75)
    assert res.max_consecutive_anomalies == 3
    assert "Temporal persistence confirmed" in res.reasons[0]


def test_temporal_persistence_anomalies_separated_by_normal_events():
    """Verify anomalies separated by normal events evaluate consecutive count accurately."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"timestamp": t0, "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=10), "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=20), "is_anomalous": False},
        {"timestamp": t0 + timedelta(seconds=30), "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=40), "is_anomalous": True},
        {"timestamp": t0 + timedelta(seconds=50), "is_anomalous": True},
    ]
    res = evaluate_temporal_persistence(
        events,
        window_duration_seconds=300.0,
        min_anomaly_count=3,
        min_anomaly_ratio=0.5,
    )
    assert res.is_persistent is True
    assert res.anomalous_events == 5
    assert res.max_consecutive_anomalies == 3


def test_temporal_persistence_events_outside_window_excluded():
    """Verify events outside the temporal observation window are excluded."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        # 3 anomalies 10 minutes (600s) before window -> should be excluded
        {"timestamp": t0 - timedelta(seconds=600), "is_anomalous": True},
        {"timestamp": t0 - timedelta(seconds=590), "is_anomalous": True},
        {"timestamp": t0 - timedelta(seconds=580), "is_anomalous": True},
        # Inside 300s window (reference_time = t0)
        {"timestamp": t0 - timedelta(seconds=50), "is_anomalous": True},
        {"timestamp": t0 - timedelta(seconds=10), "is_anomalous": False},
        {"timestamp": t0, "is_anomalous": False},
    ]
    res = evaluate_temporal_persistence(
        events,
        window_duration_seconds=300.0,
        min_anomaly_count=3,
        reference_time=t0,
    )
    assert res.total_events == 3
    assert res.anomalous_events == 1
    assert res.is_persistent is False


def test_temporal_persistence_min_count_and_ratio_thresholds():
    """Verify persistence respects both min_anomaly_count and min_anomaly_ratio."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # 3 anomalies out of 10 events (count=3, ratio=0.3 < 0.5)
    events = [
        {"timestamp": t0 + timedelta(seconds=i * 10), "is_anomalous": i < 3}
        for i in range(10)
    ]
    res = evaluate_temporal_persistence(
        events,
        window_duration_seconds=300.0,
        min_anomaly_count=3,
        min_anomaly_ratio=0.5,
    )
    assert res.anomalous_events == 3
    assert res.total_events == 10
    assert res.anomaly_ratio == pytest.approx(0.3)
    assert res.is_persistent is False  # Fails ratio requirement


def test_temporal_persistence_empty_input():
    """Verify empty input returns non-persistent result gracefully."""
    res = evaluate_temporal_persistence([], window_duration_seconds=300.0)
    assert res.is_persistent is False
    assert res.total_events == 0
    assert res.anomalous_events == 0


def test_temporal_persistence_invalid_configuration():
    """Verify invalid window parameters raise appropriate exceptions."""
    with pytest.raises(InvalidWindowError):
        evaluate_temporal_persistence([], window_duration_seconds=0.0)

    with pytest.raises(ValueError):
        evaluate_temporal_persistence([], min_anomaly_count=0)

    with pytest.raises(ValueError):
        evaluate_temporal_persistence([], min_anomaly_ratio=1.5)


# -----------------------------------------------------------------------------
# TWO-PZT EVENT CORRELATION TESTS
# -----------------------------------------------------------------------------

def test_sensor_correlation_exact_timestamp_match():
    """Verify events from PZT-01 and PZT-02 at exact same timestamp form a cross-sensor group."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"id": 101, "timestamp": t0, "source_id": "PZT-01", "zone_id": 1},
        {"id": 102, "timestamp": t0, "source_id": "PZT-02", "zone_id": 1},
    ]
    groups = correlate_two_pzt_events(events, tolerance_seconds=0.025)

    assert len(groups) == 1
    grp = groups[0]
    assert isinstance(grp, CorrelatedEventGroup)
    assert grp.is_cross_sensor is True
    assert grp.sensor_count == 2
    assert set(grp.participating_sensors) == {"PZT-01", "PZT-02"}
    assert set(grp.event_ids) == {101, 102}
    assert grp.temporal_spread_ms == 0.0
    assert "Two-sensor event correlation confirmed" in grp.relative_source_hint


def test_sensor_correlation_events_within_tolerance():
    """Verify events within tolerance (15ms apart with 25ms tolerance) correlate."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=15)
    events = [
        {"id": 201, "timestamp": t0, "source_id": "PZT-01", "zone_id": 1},
        {"id": 202, "timestamp": t1, "source_id": "PZT-02", "zone_id": 1},
    ]
    groups = correlate_two_pzt_events(events, tolerance_seconds=0.025)

    assert len(groups) == 1
    grp = groups[0]
    assert grp.is_cross_sensor is True
    assert grp.temporal_spread_ms == pytest.approx(15.0)


def test_sensor_correlation_events_outside_tolerance():
    """Verify events outside tolerance (500ms apart with 25ms tolerance) form separate single-sensor groups."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=500)
    events = [
        {"id": 301, "timestamp": t0, "source_id": "PZT-01", "zone_id": 1},
        {"id": 302, "timestamp": t1, "source_id": "PZT-02", "zone_id": 1},
    ]
    groups = correlate_two_pzt_events(events, tolerance_seconds=0.025)

    assert len(groups) == 2
    assert groups[0].is_cross_sensor is False
    assert groups[0].participating_sensors == ("PZT-01",)
    assert groups[1].is_cross_sensor is False
    assert groups[1].participating_sensors == ("PZT-02",)


def test_sensor_correlation_single_sensor_only():
    """Verify events from a single sensor form single-sensor groups."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"id": 401, "timestamp": t0, "source_id": "PZT-01", "zone_id": 1},
        {"id": 402, "timestamp": t0 + timedelta(milliseconds=10), "source_id": "PZT-01", "zone_id": 1},
    ]
    groups = correlate_two_pzt_events(events, tolerance_seconds=0.025)

    assert len(groups) == 1
    grp = groups[0]
    assert grp.sensor_count == 1
    assert grp.is_cross_sensor is False
    assert "Single-sensor event observation" in grp.relative_source_hint


def test_sensor_correlation_events_different_zones_separated():
    """Verify events from different zones are never correlated together."""
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        {"id": 501, "timestamp": t0, "source_id": "PZT-01", "zone_id": 1},
        {"id": 502, "timestamp": t0, "source_id": "PZT-02", "zone_id": 2},  # Zone 2!
    ]
    groups = correlate_two_pzt_events(events, tolerance_seconds=0.025)

    assert len(groups) == 2
    assert groups[0].zone_id == 1
    assert groups[1].zone_id == 2
    assert groups[0].is_cross_sensor is False
    assert groups[1].is_cross_sensor is False


def test_sensor_correlation_empty_input_and_invalid_tolerance():
    """Verify empty input returns [] and non-positive tolerance raises InvalidToleranceError."""
    assert correlate_two_pzt_events([], tolerance_seconds=0.025) == []

    with pytest.raises(InvalidToleranceError):
        correlate_two_pzt_events([{"timestamp": datetime.now(timezone.utc)}], tolerance_seconds=0.0)


# -----------------------------------------------------------------------------
# COMBINED EVIDENCE AGGREGATION TESTS
# -----------------------------------------------------------------------------

def test_aggregate_evidence_isolated_anomaly():
    """Verify isolated anomaly produces INDIVIDUAL_ANOMALY category."""
    p_res = TemporalPersistenceResult(
        is_persistent=False,
        total_events=1,
        anomalous_events=1,
        anomaly_ratio=1.0,
        max_consecutive_anomalies=1,
        time_span_seconds=0.0,
        window_duration_seconds=300.0,
        min_anomaly_count_used=3,
        min_anomaly_ratio_used=0.5,
        reasons=("No temporal persistence: 1 anomaly",),
    )
    res = aggregate_event_evidence(
        is_anomalous=True,
        persistence_result=p_res,
        correlation_group=None,
        primary_event_id=1,
        anomaly_reasons=["Magnitude deviation exceeded threshold"],
    )
    assert res.category == EvidenceCategory.INDIVIDUAL_ANOMALY
    assert res.is_anomalous is True
    assert res.is_persistent is False
    assert res.is_cross_sensor is False


def test_aggregate_evidence_persistent_anomaly():
    """Verify persistent single-sensor anomaly produces PERSISTENT_ANOMALY category."""
    p_res = TemporalPersistenceResult(
        is_persistent=True,
        total_events=5,
        anomalous_events=4,
        anomaly_ratio=0.8,
        max_consecutive_anomalies=3,
        time_span_seconds=40.0,
        window_duration_seconds=300.0,
        min_anomaly_count_used=3,
        min_anomaly_ratio_used=0.5,
        reasons=("Temporal persistence confirmed",),
    )
    res = aggregate_event_evidence(
        is_anomalous=True,
        persistence_result=p_res,
        correlation_group=None,
        primary_event_id=2,
    )
    assert res.category == EvidenceCategory.PERSISTENT_ANOMALY
    assert res.is_persistent is True
    assert res.is_cross_sensor is False


def test_aggregate_evidence_cross_sensor_correlated_anomaly():
    """Verify non-persistent cross-sensor anomaly produces CROSS_SENSOR_CORRELATED category."""
    p_res = TemporalPersistenceResult(
        is_persistent=False,
        total_events=2,
        anomalous_events=1,
        anomaly_ratio=0.5,
        max_consecutive_anomalies=1,
        time_span_seconds=0.015,
        window_duration_seconds=300.0,
        min_anomaly_count_used=3,
        min_anomaly_ratio_used=0.5,
        reasons=("No temporal persistence",),
    )
    c_grp = CorrelatedEventGroup(
        group_id="CORR-Z1-100-2",
        zone_id=1,
        participating_sensors=("PZT-01", "PZT-02"),
        event_ids=(10, 11),
        start_timestamp=datetime.now(timezone.utc),
        end_timestamp=datetime.now(timezone.utc),
        event_count=2,
        sensor_count=2,
        is_cross_sensor=True,
        temporal_spread_ms=15.0,
        relative_source_hint="Two-sensor event correlation confirmed",
    )
    res = aggregate_event_evidence(
        is_anomalous=True,
        persistence_result=p_res,
        correlation_group=c_grp,
        primary_event_id=10,
    )
    assert res.category == EvidenceCategory.CROSS_SENSOR_CORRELATED
    assert res.is_persistent is False
    assert res.is_cross_sensor is True


def test_aggregate_evidence_persistent_and_cross_sensor_correlated():
    """Verify persistent and cross-sensor anomaly produces PERSISTENT_AND_CROSS_SENSOR_CORRELATED category."""
    p_res = TemporalPersistenceResult(
        is_persistent=True,
        total_events=5,
        anomalous_events=4,
        anomaly_ratio=0.8,
        max_consecutive_anomalies=3,
        time_span_seconds=100.0,
        window_duration_seconds=300.0,
        min_anomaly_count_used=3,
        min_anomaly_ratio_used=0.5,
        reasons=("Temporal persistence confirmed",),
    )
    c_grp = CorrelatedEventGroup(
        group_id="CORR-Z1-100-2",
        zone_id=1,
        participating_sensors=("PZT-01", "PZT-02"),
        event_ids=(10, 11),
        start_timestamp=datetime.now(timezone.utc),
        end_timestamp=datetime.now(timezone.utc),
        event_count=2,
        sensor_count=2,
        is_cross_sensor=True,
        temporal_spread_ms=15.0,
        relative_source_hint="Two-sensor event correlation confirmed",
    )
    res = aggregate_event_evidence(
        is_anomalous=True,
        persistence_result=p_res,
        correlation_group=c_grp,
        primary_event_id=10,
    )
    assert res.category == EvidenceCategory.PERSISTENT_AND_CROSS_SENSOR_CORRELATED
    assert res.is_persistent is True
    assert res.is_cross_sensor is True
    assert res.correlation_group_id == "CORR-Z1-100-2"


def test_aggregate_evidence_normal_observation():
    """Verify normal event produces NORMAL_OBSERVATION category."""
    p_res = TemporalPersistenceResult(
        is_persistent=False,
        total_events=1,
        anomalous_events=0,
        anomaly_ratio=0.0,
        max_consecutive_anomalies=0,
        time_span_seconds=0.0,
        window_duration_seconds=300.0,
        min_anomaly_count_used=3,
        min_anomaly_ratio_used=0.5,
        reasons=("No temporal persistence",),
    )
    res = aggregate_event_evidence(
        is_anomalous=False,
        persistence_result=p_res,
        correlation_group=None,
    )
    assert res.category == EvidenceCategory.NORMAL_OBSERVATION
    assert res.is_anomalous is False


# -----------------------------------------------------------------------------
# SERVICE INTEGRATION TESTS
# -----------------------------------------------------------------------------

def test_correlation_service_full_integration(sqlite_session: Session):
    """Verify CorrelationService queries DB entities and evaluates evidence aggregation."""
    zone = Zone(name="Main Beam Section", floor="Level 1")
    msession = MonitoringSession(name="Run Step 8", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone, msession])
    sqlite_session.commit()

    # Seed baseline
    baseline = Baseline(
        zone_id=zone.id,
        mean_magnitude=10.0,
        std_magnitude=2.0,
        mean_energy=100.0,
        std_energy=10.0,
        normal_event_rate=0.5,
        valid_from=datetime.now(timezone.utc),
    )
    sqlite_session.add(baseline)
    sqlite_session.commit()

    base_t = datetime.now(timezone.utc)

    # Seed 3 anomalous events for PZT-01 and 3 corresponding events for PZT-02 within 15ms tolerance
    events = []
    for i in range(3):
        t1 = base_t + timedelta(seconds=i * 5)
        t2 = t1 + timedelta(milliseconds=15)

        e1 = Event(
            session_id=msession.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-01",
            timestamp=t1,
            magnitude=18.0,  # z = 4.0 (anomalous)
            energy=150.0,   # z = 5.0 (anomalous)
            severity=EventSeverity.LOW,
            status=EventStatus.DETECTED,
        )
        e2 = Event(
            session_id=msession.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-02",
            timestamp=t2,
            magnitude=18.0,
            energy=150.0,
            severity=EventSeverity.LOW,
            status=EventStatus.DETECTED,
        )
        events.extend([e1, e2])

    sqlite_session.add_all(events)
    sqlite_session.commit()

    service = CorrelationService(sqlite_session)

    # Test persistence evaluation
    p_res = service.evaluate_zone_persistence(zone.id, reference_time=events[-1].timestamp)
    assert p_res.is_persistent is True
    assert p_res.anomalous_events == 6

    # Test sensor correlation query
    c_groups = service.correlate_zone_events(
        zone.id,
        valid_from=base_t - timedelta(seconds=1),
        valid_until=base_t + timedelta(seconds=30),
    )
    assert len(c_groups) == 3
    assert all(grp.is_cross_sensor for grp in c_groups)

    # Test full evidence aggregation for primary event (events[-1] evaluated when sequence is complete)
    agg_res = service.evaluate_event_evidence(events[-1].id)
    assert isinstance(agg_res, AggregatedEvidenceResult)
    assert agg_res.category == EvidenceCategory.PERSISTENT_AND_CROSS_SENSOR_CORRELATED
    assert agg_res.is_anomalous is True
    assert agg_res.is_persistent is True
    assert agg_res.is_cross_sensor is True
    assert agg_res.correlation_group_id is not None
