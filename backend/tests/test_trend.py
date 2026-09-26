"""Unit and integration tests for Aegis3D Step 9: Deterministic Zone Trend Analysis."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.enums import EventSeverity, EventSourceType, EventStatus, SessionMode, SessionStatus
from app.models.event import Event
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.services.trend_service import TrendService
from app.trend.evaluator import evaluate_zone_trend
from app.trend.exceptions import InvalidTrendConfigError
from app.trend.types import (
    DEFAULT_MAGNITUDE_DELTA_THRESHOLD,
    DEFAULT_MIN_EVENTS_PER_PERIOD,
    DEFAULT_TREND_DELTA_THRESHOLD,
    DEFAULT_TREND_WINDOW_SECONDS,
    PeriodMetrics,
    TrendDirection,
    ZoneTrendResult,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_event(ts: datetime, is_anom: bool, mag: float = 1.0, zone_id: int = 1, is_pers: bool = False, is_cross: bool = False):
    """Helper to construct event dict."""
    return {
        "timestamp": ts,
        "zone_id": zone_id,
        "is_anomalous": is_anom,
        "magnitude": mag,
        "is_persistent": is_pers,
        "is_cross_sensor": is_cross,
    }


class TestBasicTrendCalculation:
    """Test suite for primary anomaly rate trend directions."""

    def test_increasing_anomaly_rate(self):
        """Verify increasing anomaly rate (earlier 20%, later 60%) yields INCREASING trend."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        # Window: 3600s -> Earlier: [11:00, 11:30), Later: [11:30, 12:00]
        events = [
            # Earlier period: 5 events, 1 anomalous (20%)
            _make_event(ref_t - timedelta(minutes=55), is_anom=True),
            _make_event(ref_t - timedelta(minutes=50), is_anom=False),
            _make_event(ref_t - timedelta(minutes=45), is_anom=False),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False),
            _make_event(ref_t - timedelta(minutes=35), is_anom=False),
            # Later period: 5 events, 3 anomalous (60%)
            _make_event(ref_t - timedelta(minutes=25), is_anom=True),
            _make_event(ref_t - timedelta(minutes=20), is_anom=True),
            _make_event(ref_t - timedelta(minutes=15), is_anom=True),
            _make_event(ref_t - timedelta(minutes=10), is_anom=False),
            _make_event(ref_t - timedelta(minutes=5), is_anom=False),
        ]

        result = evaluate_zone_trend(events, reference_time=ref_t)

        assert result.overall_trend_direction == TrendDirection.INCREASING
        assert result.rate_trend_direction == TrendDirection.INCREASING
        assert pytest.approx(result.earlier_period.anomaly_rate) == 0.20
        assert pytest.approx(result.later_period.anomaly_rate) == 0.60
        assert pytest.approx(result.anomaly_rate_delta) == 0.40
        assert any("INCREASING" in r for r in result.reasons)

    def test_decreasing_anomaly_rate(self):
        """Verify decreasing anomaly rate (earlier 60%, later 20%) yields DECREASING trend."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier period: 5 events, 3 anomalous (60%)
            _make_event(ref_t - timedelta(minutes=55), is_anom=True),
            _make_event(ref_t - timedelta(minutes=50), is_anom=True),
            _make_event(ref_t - timedelta(minutes=45), is_anom=True),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False),
            _make_event(ref_t - timedelta(minutes=35), is_anom=False),
            # Later period: 5 events, 1 anomalous (20%)
            _make_event(ref_t - timedelta(minutes=25), is_anom=True),
            _make_event(ref_t - timedelta(minutes=20), is_anom=False),
            _make_event(ref_t - timedelta(minutes=15), is_anom=False),
            _make_event(ref_t - timedelta(minutes=10), is_anom=False),
            _make_event(ref_t - timedelta(minutes=5), is_anom=False),
        ]

        result = evaluate_zone_trend(events, reference_time=ref_t)

        assert result.overall_trend_direction == TrendDirection.DECREASING
        assert result.rate_trend_direction == TrendDirection.DECREASING
        assert pytest.approx(result.anomaly_rate_delta) == -0.40

    def test_stable_anomaly_rate(self):
        """Verify change within delta threshold yields STABLE trend."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier: 4 events, 2 anomalous (50%)
            _make_event(ref_t - timedelta(minutes=50), is_anom=True),
            _make_event(ref_t - timedelta(minutes=45), is_anom=True),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False),
            _make_event(ref_t - timedelta(minutes=35), is_anom=False),
            # Later: 4 events, 2 anomalous (50%)
            _make_event(ref_t - timedelta(minutes=25), is_anom=True),
            _make_event(ref_t - timedelta(minutes=20), is_anom=True),
            _make_event(ref_t - timedelta(minutes=15), is_anom=False),
            _make_event(ref_t - timedelta(minutes=10), is_anom=False),
        ]

        result = evaluate_zone_trend(events, reference_time=ref_t, trend_delta_threshold=0.10)

        assert result.overall_trend_direction == TrendDirection.STABLE
        assert result.rate_trend_direction == TrendDirection.STABLE
        assert pytest.approx(result.anomaly_rate_delta) == 0.0

    def test_exact_threshold_boundary(self):
        """Verify delta exactly equal to threshold (+0.10) yields INCREASING."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier: 10 events, 4 anomalous (40%)
            *[_make_event(ref_t - timedelta(minutes=50), is_anom=True) for _ in range(4)],
            *[_make_event(ref_t - timedelta(minutes=40), is_anom=False) for _ in range(6)],
            # Later: 10 events, 5 anomalous (50%) -> delta = +0.10
            *[_make_event(ref_t - timedelta(minutes=20), is_anom=True) for _ in range(5)],
            *[_make_event(ref_t - timedelta(minutes=10), is_anom=False) for _ in range(5)],
        ]

        result = evaluate_zone_trend(events, reference_time=ref_t, trend_delta_threshold=0.10)

        assert result.overall_trend_direction == TrendDirection.INCREASING
        assert pytest.approx(result.anomaly_rate_delta) == 0.10


class TestDataHandling:
    """Test suite for edge-case data handling, missing data, and boundary behavior."""

    def test_empty_input(self):
        """Verify empty event input returns INSUFFICIENT_DATA."""
        result = evaluate_zone_trend([])
        assert result.overall_trend_direction == TrendDirection.INSUFFICIENT_DATA
        assert any("No event observations available" in r for r in result.reasons)

    def test_only_earlier_period_populated(self):
        """Verify events present only in earlier sub-period returns INSUFFICIENT_DATA."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            _make_event(ref_t - timedelta(minutes=50), is_anom=True),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, min_events_per_period=2)

        assert result.overall_trend_direction == TrendDirection.INSUFFICIENT_DATA
        assert result.earlier_period.total_events == 2
        assert result.later_period.total_events == 0

    def test_only_later_period_populated(self):
        """Verify events present only in later sub-period returns INSUFFICIENT_DATA."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            _make_event(ref_t - timedelta(minutes=20), is_anom=True),
            _make_event(ref_t - timedelta(minutes=10), is_anom=False),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, min_events_per_period=2)

        assert result.overall_trend_direction == TrendDirection.INSUFFICIENT_DATA

    def test_insufficient_events_per_period(self):
        """Verify sub-period with fewer events than min_events_per_period returns INSUFFICIENT_DATA."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier: 1 event (requires 2)
            _make_event(ref_t - timedelta(minutes=40), is_anom=True),
            # Later: 2 events
            _make_event(ref_t - timedelta(minutes=20), is_anom=True),
            _make_event(ref_t - timedelta(minutes=10), is_anom=False),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, min_events_per_period=2)

        assert result.overall_trend_direction == TrendDirection.INSUFFICIENT_DATA

    def test_events_on_exact_boundary(self):
        """Verify event exactly on midpoint boundary is deterministically assigned to later period."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        midpoint = ref_t - timedelta(minutes=30)
        events = [
            _make_event(ref_t - timedelta(minutes=45), is_anom=False),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False),
            _make_event(midpoint, is_anom=True),  # Exactly on midpoint boundary
            _make_event(ref_t - timedelta(minutes=15), is_anom=True),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, min_events_per_period=2)

        assert result.earlier_period.total_events == 2
        assert result.later_period.total_events == 2

    def test_unordered_events_sorted_correctly(self):
        """Verify events provided out of chronological order are sorted prior to evaluation."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            _make_event(ref_t - timedelta(minutes=10), is_anom=True),  # later
            _make_event(ref_t - timedelta(minutes=50), is_anom=False), # earlier
            _make_event(ref_t - timedelta(minutes=20), is_anom=True),  # later
            _make_event(ref_t - timedelta(minutes=40), is_anom=False), # earlier
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, min_events_per_period=2)

        assert result.earlier_period.total_events == 2
        assert result.later_period.total_events == 2
        assert result.overall_trend_direction == TrendDirection.INCREASING

    def test_multi_zone_filtering(self):
        """Verify filtering by target_zone_id restricts evaluation to specified zone."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            _make_event(ref_t - timedelta(minutes=50), is_anom=False, zone_id=1),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False, zone_id=1),
            _make_event(ref_t - timedelta(minutes=20), is_anom=True, zone_id=1),
            _make_event(ref_t - timedelta(minutes=10), is_anom=True, zone_id=1),
            # Noise events in Zone 2
            _make_event(ref_t - timedelta(minutes=50), is_anom=True, zone_id=2),
            _make_event(ref_t - timedelta(minutes=40), is_anom=True, zone_id=2),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, target_zone_id=1)

        assert result.zone_id == 1
        assert result.earlier_period.total_events == 2
        assert result.later_period.total_events == 2
        assert result.overall_trend_direction == TrendDirection.INCREASING


class TestMagnitudeAndConflictingTrends:
    """Test suite for event magnitude trends and conflicting rate vs magnitude signals."""

    def test_increasing_anomaly_magnitude(self):
        """Verify increasing magnitude triggers INCREASING magnitude trend."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier: 2 events, mag 1.0 (mean 1.0)
            _make_event(ref_t - timedelta(minutes=50), is_anom=True, mag=1.0),
            _make_event(ref_t - timedelta(minutes=40), is_anom=True, mag=1.0),
            # Later: 2 events, mag 3.0 (mean 3.0) -> delta = +2.0
            _make_event(ref_t - timedelta(minutes=20), is_anom=True, mag=3.0),
            _make_event(ref_t - timedelta(minutes=10), is_anom=True, mag=3.0),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t, magnitude_delta_threshold=0.5)

        assert result.magnitude_trend_direction == TrendDirection.INCREASING
        assert pytest.approx(result.magnitude_delta) == 2.0
        assert result.overall_trend_direction == TrendDirection.INCREASING

    def test_conflicting_rate_increasing_magnitude_decreasing(self):
        """Verify overall trend follows rate trend when rate increases but magnitude decreases, with reason noting divergence."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier: 4 events, 1 anomalous (25%), mag 5.0
            _make_event(ref_t - timedelta(minutes=50), is_anom=True, mag=5.0),
            _make_event(ref_t - timedelta(minutes=45), is_anom=False, mag=5.0),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False, mag=5.0),
            _make_event(ref_t - timedelta(minutes=35), is_anom=False, mag=5.0),
            # Later: 4 events, 3 anomalous (75%), mag 1.0 -> rate delta +0.50, mag delta -4.0
            _make_event(ref_t - timedelta(minutes=25), is_anom=True, mag=1.0),
            _make_event(ref_t - timedelta(minutes=20), is_anom=True, mag=1.0),
            _make_event(ref_t - timedelta(minutes=15), is_anom=True, mag=1.0),
            _make_event(ref_t - timedelta(minutes=10), is_anom=False, mag=1.0),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t)

        assert result.rate_trend_direction == TrendDirection.INCREASING
        assert result.magnitude_trend_direction == TrendDirection.DECREASING
        assert result.overall_trend_direction == TrendDirection.INCREASING
        assert any("Divergent trend components" in r for r in result.reasons)


class TestStep8EvidenceIntegration:
    """Test suite for Step 8 evidence consumption (persistence & cross-sensor correlation)."""

    def test_increasing_persistent_and_cross_sensor_evidence(self):
        """Verify increasing persistent & cross-sensor evidence is accurately tracked."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            # Earlier: 2 events, 0 persistent, 0 cross-sensor
            _make_event(ref_t - timedelta(minutes=50), is_anom=True, is_pers=False, is_cross=False),
            _make_event(ref_t - timedelta(minutes=40), is_anom=True, is_pers=False, is_cross=False),
            # Later: 2 events, both persistent & cross-sensor
            _make_event(ref_t - timedelta(minutes=20), is_anom=True, is_pers=True, is_cross=True),
            _make_event(ref_t - timedelta(minutes=10), is_anom=True, is_pers=True, is_cross=True),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t)

        assert result.earlier_period.persistent_anomaly_count == 0
        assert result.later_period.persistent_anomaly_count == 2
        assert result.persistent_count_delta == 2
        assert result.earlier_period.cross_sensor_event_count == 0
        assert result.later_period.cross_sensor_event_count == 2
        assert result.cross_sensor_count_delta == 2
        assert result.overall_trend_direction == TrendDirection.INCREASING


class TestInvalidConfiguration:
    """Test suite for parameter validation and exception raising."""

    def test_invalid_window_duration(self):
        """Verify non-positive window duration raises InvalidTrendConfigError."""
        with pytest.raises(InvalidTrendConfigError, match="analysis_window_seconds must be positive"):
            evaluate_zone_trend([], analysis_window_seconds=0.0)

    def test_invalid_trend_delta_threshold(self):
        """Verify delta threshold outside [0.0, 1.0] raises InvalidTrendConfigError."""
        with pytest.raises(InvalidTrendConfigError, match="trend_delta_threshold must be between 0.0 and 1.0"):
            evaluate_zone_trend([], trend_delta_threshold=1.5)

    def test_invalid_min_events_per_period(self):
        """Verify min_events_per_period < 1 raises InvalidTrendConfigError."""
        with pytest.raises(InvalidTrendConfigError, match="min_events_per_period must be at least 1"):
            evaluate_zone_trend([], min_events_per_period=0)

    def test_invalid_magnitude_delta_threshold(self):
        """Verify negative magnitude delta threshold raises InvalidTrendConfigError."""
        with pytest.raises(InvalidTrendConfigError, match="magnitude_delta_threshold must be non-negative"):
            evaluate_zone_trend([], magnitude_delta_threshold=-0.5)


class TestServiceAndSerialization:
    """Test suite for TrendService orchestration and dictionary serialization."""

    def test_trend_result_to_dict(self):
        """Verify ZoneTrendResult serializes cleanly to dict."""
        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            _make_event(ref_t - timedelta(minutes=50), is_anom=False),
            _make_event(ref_t - timedelta(minutes=40), is_anom=False),
            _make_event(ref_t - timedelta(minutes=20), is_anom=True),
            _make_event(ref_t - timedelta(minutes=10), is_anom=True),
        ]
        result = evaluate_zone_trend(events, reference_time=ref_t)
        res_dict = result.to_dict()

        assert res_dict["overall_trend_direction"] == "INCREASING"
        assert "earlier_period" in res_dict
        assert "later_period" in res_dict
        assert isinstance(res_dict["reasons"], list)

    def test_trend_service_with_database(self, db_session):
        """Verify TrendService queries database events and calculates trend."""
        # 1. Setup Session and Zone
        mon_session = MonitoringSession(name="Test Session", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
        db_session.add(mon_session)
        db_session.commit()

        zone = Zone(name="Zone-101")
        db_session.add(zone)
        db_session.commit()

        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)

        # 2. Add events to DB
        # Earlier: 2 normal events
        e1 = Event(
            session_id=mon_session.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-01",
            timestamp=ref_t - timedelta(minutes=50),
            magnitude=1.0,
            energy=1.0,
            severity=EventSeverity.LOW,
            status=EventStatus.DETECTED,
        )
        e2 = Event(
            session_id=mon_session.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-01",
            timestamp=ref_t - timedelta(minutes=40),
            magnitude=1.0,
            energy=1.0,
            severity=EventSeverity.LOW,
            status=EventStatus.DETECTED,
        )
        # Later: 2 anomalous events (high magnitude)
        e3 = Event(
            session_id=mon_session.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-01",
            timestamp=ref_t - timedelta(minutes=20),
            magnitude=10.0,
            energy=10.0,
            severity=EventSeverity.HIGH,
            status=EventStatus.DETECTED,
        )
        e4 = Event(
            session_id=mon_session.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-01",
            timestamp=ref_t - timedelta(minutes=10),
            magnitude=10.0,
            energy=10.0,
            severity=EventSeverity.HIGH,
            status=EventStatus.DETECTED,
        )
        db_session.add_all([e1, e2, e3, e4])
        db_session.commit()

        service = TrendService(db_session)
        result = service.evaluate_zone_trend(
            zone_id=zone.id,
            reference_time=ref_t,
            analysis_window_seconds=3600.0,
        )

        assert isinstance(result, ZoneTrendResult)
        assert result.zone_id == zone.id
        assert result.earlier_period.total_events == 2
        assert result.later_period.total_events == 2
