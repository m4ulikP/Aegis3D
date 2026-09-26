"""Test suite for Aegis3D Step 7 Rule-Based Anomaly Detection."""

from datetime import datetime, timezone
import math
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.anomaly import (
    DEFAULT_ANOMALY_Z_THRESHOLD,
    AnomalyAnalysisResult,
    BaselineNotFoundError,
    InvalidBaselineError,
    InvalidEventDataError,
    InvalidThresholdError,
    analyze_event,
    analyze_event_against_baseline,
    calculate_z_score,
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
from app.services import AnomalyService


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
# PURE STATISTICAL ANOMALY CALCULATION TESTS
# -----------------------------------------------------------------------------

def test_event_within_normal_range():
    """Requirement A: Event within normal magnitude and energy range is not anomalous."""
    res = analyze_event_against_baseline(
        magnitude=11.0,
        energy=105.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert not res.is_anomalous
    assert not res.magnitude_anomalous
    assert not res.energy_anomalous
    assert res.magnitude_z_score == pytest.approx(0.5)
    assert res.energy_z_score == pytest.approx(0.5)
    assert len(res.reasons) == 1
    assert "within normal statistical threshold" in res.reasons[0]


def test_magnitude_above_threshold_anomalous():
    """Requirement B & E: Magnitude z-score above threshold produces magnitude anomaly evidence only."""
    res = analyze_event_against_baseline(
        magnitude=18.0,  # z = (18-10)/2 = 4.0 >= 3.0
        energy=105.0,   # z = 0.5 < 3.0
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert res.is_anomalous
    assert res.magnitude_anomalous
    assert not res.energy_anomalous
    assert res.magnitude_z_score == pytest.approx(4.0)
    assert len(res.reasons) == 1
    assert "Magnitude deviation (|z| = 4.00σ) exceeded statistical threshold" in res.reasons[0]


def test_energy_above_threshold_anomalous():
    """Requirement C & F: Energy z-score above threshold produces energy anomaly evidence only."""
    res = analyze_event_against_baseline(
        magnitude=10.0,  # z = 0.0
        energy=140.0,   # z = (140-100)/10 = 4.0 >= 3.0
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert res.is_anomalous
    assert not res.magnitude_anomalous
    assert res.energy_anomalous
    assert res.energy_z_score == pytest.approx(4.0)
    assert len(res.reasons) == 1
    assert "Energy deviation (|z| = 4.00σ) exceeded statistical threshold" in res.reasons[0]


def test_both_magnitude_and_energy_anomalous():
    """Requirement D: Both magnitude and energy anomalous reports both reasons."""
    res = analyze_event_against_baseline(
        magnitude=17.0,  # z = (17-10)/2 = 3.5
        energy=135.0,   # z = (135-100)/10 = 3.5
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert res.is_anomalous
    assert res.magnitude_anomalous
    assert res.energy_anomalous
    assert len(res.reasons) == 2
    assert "Magnitude deviation (|z| = 3.50σ)" in res.reasons[0]
    assert "Energy deviation (|z| = 3.50σ)" in res.reasons[1]


def test_boundary_exactly_at_threshold():
    """Requirement G: Exactly at configured threshold (|z| == threshold) is flagged as anomalous."""
    res = analyze_event_against_baseline(
        magnitude=16.0,  # z = (16-10)/2 = 3.0 exactly
        energy=100.0,   # z = 0.0
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert res.is_anomalous
    assert res.magnitude_anomalous
    assert res.magnitude_z_score == pytest.approx(3.0)


def test_zero_magnitude_standard_deviation():
    """Requirement H: Zero magnitude std dev returns finite 0.0 z-score, flagging anomaly if value != mean."""
    # Case 1: Event magnitude equals mean -> normal, finite z-score 0.0
    res_normal = analyze_event_against_baseline(
        magnitude=10.0,
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=0.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
    )
    assert not res_normal.magnitude_anomalous
    assert res_normal.magnitude_z_score == 0.0
    assert not math.isnan(res_normal.magnitude_z_score)
    assert not math.isinf(res_normal.magnitude_z_score)

    # Case 2: Event magnitude differs from mean -> anomalous, finite z-score 0.0
    res_anomalous = analyze_event_against_baseline(
        magnitude=10.5,
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=0.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
    )
    assert res_anomalous.magnitude_anomalous
    assert res_anomalous.magnitude_z_score == 0.0
    assert not math.isnan(res_anomalous.magnitude_z_score)
    assert not math.isinf(res_anomalous.magnitude_z_score)
    assert "deviated from zero-variance baseline mean" in res_anomalous.reasons[0]


def test_zero_energy_standard_deviation():
    """Requirement I: Zero energy std dev returns finite 0.0 z-score, flagging anomaly if value != mean."""
    # Case 1: Event energy equals mean -> normal, finite z-score 0.0
    res_normal = analyze_event_against_baseline(
        magnitude=10.0,
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=0.0,
    )
    assert not res_normal.energy_anomalous
    assert res_normal.energy_z_score == 0.0
    assert not math.isnan(res_normal.energy_z_score)
    assert not math.isinf(res_normal.energy_z_score)

    # Case 2: Event energy differs from mean -> anomalous, finite z-score 0.0
    res_anomalous = analyze_event_against_baseline(
        magnitude=10.0,
        energy=99.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=0.0,
    )
    assert res_anomalous.energy_anomalous
    assert res_anomalous.energy_z_score == 0.0
    assert not math.isnan(res_anomalous.energy_z_score)
    assert not math.isinf(res_anomalous.energy_z_score)
    assert "deviated from zero-variance baseline mean" in res_anomalous.reasons[0]


def test_no_result_field_contains_nan_or_infinity():
    """Verify strictly no field in AnomalyAnalysisResult contains NaN or Infinity."""
    res = analyze_event_against_baseline(
        magnitude=15.0,
        energy=50.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=0.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=0.0,
    )
    assert not math.isnan(res.magnitude_z_score)
    assert not math.isinf(res.magnitude_z_score)
    assert not math.isnan(res.energy_z_score)
    assert not math.isinf(res.energy_z_score)
    assert not math.isnan(res.threshold_used)
    assert not math.isinf(res.threshold_used)


def test_negative_z_score_unusually_low_values():
    """Requirement J: Unusually low values (negative z-score) evaluated using absolute deviation."""
    res = analyze_event_against_baseline(
        magnitude=2.0,  # z = (2-10)/2 = -4.0, |z| = 4.0 >= 3.0
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert res.is_anomalous
    assert res.magnitude_anomalous
    assert res.magnitude_z_score == pytest.approx(-4.0)
    assert "Magnitude deviation (|z| = 4.00σ)" in res.reasons[0]


def test_missing_or_non_finite_event_values():
    """Requirement K: Missing or non-finite event values fail clearly with InvalidEventDataError."""
    # None value
    with pytest.raises(InvalidEventDataError):
        analyze_event_against_baseline(
            magnitude=None,  # type: ignore
            energy=100.0,
            baseline_mean_magnitude=10.0,
            baseline_std_magnitude=2.0,
            baseline_mean_energy=100.0,
            baseline_std_energy=10.0,
        )

    # NaN value
    with pytest.raises(InvalidEventDataError):
        analyze_event_against_baseline(
            magnitude=10.0,
            energy=float("nan"),
            baseline_mean_magnitude=10.0,
            baseline_std_magnitude=2.0,
            baseline_mean_energy=100.0,
            baseline_std_energy=10.0,
        )

    # Infinite value
    with pytest.raises(InvalidEventDataError):
        analyze_event_against_baseline(
            magnitude=float("inf"),
            energy=100.0,
            baseline_mean_magnitude=10.0,
            baseline_std_magnitude=2.0,
            baseline_mean_energy=100.0,
            baseline_std_energy=10.0,
        )


def test_invalid_baseline_statistics():
    """Requirement L: Invalid baseline statistics fail clearly with InvalidBaselineError."""
    # Negative standard deviation
    with pytest.raises(InvalidBaselineError):
        analyze_event_against_baseline(
            magnitude=10.0,
            energy=100.0,
            baseline_mean_magnitude=10.0,
            baseline_std_magnitude=-1.0,  # invalid negative std
            baseline_mean_energy=100.0,
            baseline_std_energy=10.0,
        )

    # NaN in baseline stats
    with pytest.raises(InvalidBaselineError):
        analyze_event_against_baseline(
            magnitude=10.0,
            energy=100.0,
            baseline_mean_magnitude=float("nan"),
            baseline_std_magnitude=2.0,
            baseline_mean_energy=100.0,
            baseline_std_energy=10.0,
        )


def test_configurable_threshold_respected():
    """Requirement M: Configurable z_threshold is respected."""
    # Magnitude z = 2.5 is normal under threshold=3.0
    res_3 = analyze_event_against_baseline(
        magnitude=15.0,  # z = (15-10)/2 = 2.5
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=3.0,
    )
    assert not res_3.is_anomalous

    # Same magnitude z = 2.5 becomes anomalous under lower threshold=2.0
    res_2 = analyze_event_against_baseline(
        magnitude=15.0,  # z = 2.5 >= 2.0
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
        z_threshold=2.0,
    )
    assert res_2.is_anomalous
    assert res_2.threshold_used == 2.0

    # Invalid non-positive threshold raises InvalidThresholdError
    with pytest.raises(InvalidThresholdError):
        analyze_event_against_baseline(
            magnitude=10.0,
            energy=100.0,
            baseline_mean_magnitude=10.0,
            baseline_std_magnitude=2.0,
            baseline_mean_energy=100.0,
            baseline_std_energy=10.0,
            z_threshold=0.0,
        )


def test_result_to_dict_method():
    """Verify AnomalyAnalysisResult.to_dict() produces valid serializable dictionary."""
    res = analyze_event_against_baseline(
        magnitude=18.0,
        energy=100.0,
        baseline_mean_magnitude=10.0,
        baseline_std_magnitude=2.0,
        baseline_mean_energy=100.0,
        baseline_std_energy=10.0,
    )
    d = res.to_dict()
    assert d["is_anomalous"] is True
    assert d["magnitude_z_score"] == pytest.approx(4.0)
    assert d["magnitude_anomalous"] is True
    assert isinstance(d["reasons"], list)


# -----------------------------------------------------------------------------
# SERVICE & INTEGRATION TESTS
# -----------------------------------------------------------------------------

def test_anomaly_service_analyze_event_by_id(sqlite_session: Session):
    """Verify AnomalyService retrieves Event and latest Baseline from DB and computes result."""
    zone = Zone(name="Beam Section B7", floor="Level 3")
    msession = MonitoringSession(name="Run 7", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone, msession])
    sqlite_session.commit()

    # Seed baseline entity for zone
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

    # Seed event entity for zone
    event = Event(
        session_id=msession.id,
        zone_id=zone.id,
        source_type=EventSourceType.SENSOR,
        source_id="S-07",
        timestamp=datetime.now(timezone.utc),
        magnitude=18.0,  # z = 4.0 -> anomalous
        energy=105.0,   # z = 0.5 -> normal
        severity=EventSeverity.LOW,
        status=EventStatus.DETECTED,
    )
    sqlite_session.add(event)
    sqlite_session.commit()

    service = AnomalyService(sqlite_session)
    result = service.analyze_event_by_id(event.id, z_threshold=3.0)

    assert isinstance(result, AnomalyAnalysisResult)
    assert result.is_anomalous is True
    assert result.magnitude_anomalous is True
    assert result.energy_anomalous is False
    assert result.magnitude_z_score == pytest.approx(4.0)


def test_anomaly_service_missing_baseline_raises(sqlite_session: Session):
    """Verify BaselineNotFoundError is raised when no baseline exists for zone."""
    zone = Zone(name="Zone Without Baseline")
    msession = MonitoringSession(name="Run 8", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
    sqlite_session.add_all([zone, msession])
    sqlite_session.commit()

    event = Event(
        session_id=msession.id,
        zone_id=zone.id,
        source_type=EventSourceType.SENSOR,
        source_id="S-08",
        timestamp=datetime.now(timezone.utc),
        magnitude=10.0,
        energy=100.0,
        severity=EventSeverity.LOW,
        status=EventStatus.DETECTED,
    )
    sqlite_session.add(event)
    sqlite_session.commit()

    service = AnomalyService(sqlite_session)
    with pytest.raises(BaselineNotFoundError) as exc_info:
        service.analyze_event_by_id(event.id)

    assert f"No Baseline found for zone id {zone.id}" in str(exc_info.value)
