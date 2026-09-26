"""Unit and integration tests for Aegis3D Step 10: Deterministic Structural Health Indicator (SHI)."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.health.calculator import calculate_structural_health_indicator
from app.health.exceptions import InvalidHealthConfigError
from app.health.types import (
    DEFAULT_ANOMALY_PENALTY,
    DEFAULT_BASE_SCORE,
    DEFAULT_CROSS_SENSOR_PENALTY,
    DEFAULT_INCREASING_TREND_PENALTY,
    DEFAULT_PERSISTENCE_PENALTY,
    SHI_PROTOTYPE_DISCLAIMER,
    SHIConfig,
    StructuralHealthResult,
)
from app.models.enums import EventSeverity, EventSourceType, EventStatus, HealthStatus, HealthTrend, SessionMode, SessionStatus
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.services.health_service import HealthService


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


class TestSHICalculatorCore:
    """Test suite covering deterministic SHI scoring scenarios."""

    def test_completely_normal_evidence(self):
        """1. Verify zero evidence yields score 100.0 and status NORMAL."""
        res = calculate_structural_health_indicator(
            is_anomalous=False,
            is_persistent=False,
            is_cross_sensor=False,
            trend="STABLE",
        )
        assert res.score == 100.0
        assert res.status == HealthStatus.NORMAL
        assert res.deductions.total_deductions == 0.0
        assert res.disclaimer == SHI_PROTOTYPE_DISCLAIMER

    def test_individual_anomaly(self):
        """2. Verify individual anomaly yields -15 pts penalty, score 85.0, status MONITOR."""
        res = calculate_structural_health_indicator(
            is_anomalous=True,
            is_persistent=False,
            is_cross_sensor=False,
            trend="STABLE",
        )
        assert res.score == 85.0
        assert res.status == HealthStatus.MONITOR
        assert res.deductions.anomaly_activity_deduction == 15.0

    def test_persistent_anomaly(self):
        """3. Verify persistent anomaly yields anomaly + persistence penalties (-35 pts), score 65.0, status INSPECTION_ADVISED."""
        res = calculate_structural_health_indicator(
            is_anomalous=True,
            is_persistent=True,
            is_cross_sensor=False,
            trend="STABLE",
        )
        assert res.score == 65.0
        assert res.status == HealthStatus.INSPECTION_ADVISED
        assert res.deductions.persistence_deduction == 20.0

    def test_cross_sensor_correlated_anomaly(self):
        """4. Verify cross-sensor correlated anomaly yields anomaly + cross-sensor penalties (-40 pts), score 60.0, status INSPECTION_ADVISED."""
        res = calculate_structural_health_indicator(
            is_anomalous=True,
            is_persistent=False,
            is_cross_sensor=True,
            trend="STABLE",
        )
        assert res.score == 60.0
        assert res.status == HealthStatus.INSPECTION_ADVISED
        assert res.deductions.cross_sensor_deduction == 25.0

    def test_increasing_trend(self):
        """5. Verify INCREASING trend adds -15 pts penalty."""
        res = calculate_structural_health_indicator(
            is_anomalous=False,
            is_persistent=False,
            is_cross_sensor=False,
            trend="INCREASING",
        )
        assert res.score == 85.0
        assert res.status == HealthStatus.MONITOR
        assert res.deductions.increasing_trend_deduction == 15.0

    def test_decreasing_trend(self):
        """6. Verify DECREASING trend applies 0 pts penalty."""
        res = calculate_structural_health_indicator(
            is_anomalous=False,
            is_persistent=False,
            is_cross_sensor=False,
            trend="DECREASING",
        )
        assert res.score == 100.0
        assert res.status == HealthStatus.NORMAL
        assert res.deductions.increasing_trend_deduction == 0.0

    def test_stable_trend(self):
        """7. Verify STABLE trend applies 0 pts penalty."""
        res = calculate_structural_health_indicator(
            is_anomalous=False,
            is_persistent=False,
            is_cross_sensor=False,
            trend="STABLE",
        )
        assert res.score == 100.0
        assert res.status == HealthStatus.NORMAL
        assert res.deductions.increasing_trend_deduction == 0.0

    def test_insufficient_trend_data(self):
        """8. Verify INSUFFICIENT_DATA trend applies 0 penalty and preserves uncertainty in explanation."""
        res = calculate_structural_health_indicator(
            is_anomalous=False,
            is_persistent=False,
            is_cross_sensor=False,
            trend="INSUFFICIENT_DATA",
        )
        assert res.score == 100.0
        assert res.status == HealthStatus.NORMAL
        assert res.deductions.increasing_trend_deduction == 0.0
        assert any("INSUFFICIENT_DATA" in r for r in res.evidence_summary)

    def test_combined_evidence(self):
        """9. Verify combined evidence (anomaly + persistence + cross-sensor + INCREASING) yields score 25.0 and HIGH_PRIORITY_INSPECTION."""
        res = calculate_structural_health_indicator(
            is_anomalous=True,
            is_persistent=True,
            is_cross_sensor=True,
            trend="INCREASING",
        )
        assert res.score == 25.0
        assert res.status == HealthStatus.HIGH_PRIORITY_INSPECTION
        assert res.deductions.total_deductions == 75.0

    def test_score_lower_bound(self):
        """10. Verify score lower bound clamping to 0.0 on extreme penalties."""
        cfg = SHIConfig(
            base_score=100.0,
            anomaly_penalty=50.0,
            persistence_penalty=50.0,
            cross_sensor_penalty=50.0,
            increasing_trend_penalty=50.0,
        )
        res = calculate_structural_health_indicator(
            is_anomalous=True,
            is_persistent=True,
            is_cross_sensor=True,
            trend="INCREASING",
            config=cfg,
        )
        assert res.score == 0.0
        assert res.status == HealthStatus.HIGH_PRIORITY_INSPECTION

    def test_score_upper_bound(self):
        """11. Verify score upper bound clamping to 100.0."""
        res = calculate_structural_health_indicator(
            is_anomalous=False,
            is_persistent=False,
            is_cross_sensor=False,
            trend="STABLE",
        )
        assert res.score == 100.0
        assert res.score <= 100.0

    def test_exact_threshold_boundaries(self):
        """12. Verify status mapping at exact score boundaries (90, 70, 45)."""
        # Score 90 -> NORMAL
        res_90 = calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=10.0), is_anomalous=True)
        assert res_90.score == 90.0
        assert res_90.status == HealthStatus.NORMAL

        # Score 85 -> MONITOR
        res_85 = calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=15.0), is_anomalous=True)
        assert res_85.score == 85.0
        assert res_85.status == HealthStatus.MONITOR

        # Score 70 -> MONITOR
        res_70 = calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=30.0), is_anomalous=True)
        assert res_70.score == 70.0
        assert res_70.status == HealthStatus.MONITOR

        # Score 65 -> INSPECTION_ADVISED
        res_65 = calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=35.0), is_anomalous=True)
        assert res_65.score == 65.0
        assert res_65.status == HealthStatus.INSPECTION_ADVISED

        # Score 45 -> INSPECTION_ADVISED
        res_45 = calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=55.0), is_anomalous=True)
        assert res_45.score == 45.0
        assert res_45.status == HealthStatus.INSPECTION_ADVISED

        # Score 40 -> HIGH_PRIORITY_INSPECTION
        res_40 = calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=60.0), is_anomalous=True)
        assert res_40.score == 40.0
        assert res_40.status == HealthStatus.HIGH_PRIORITY_INSPECTION

    def test_deterministic_repeated_calculation(self):
        """13. Verify repeated evaluation with identical inputs produces identical results."""
        ts = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        res1 = calculate_structural_health_indicator(is_anomalous=True, is_persistent=True, timestamp=ts)
        res2 = calculate_structural_health_indicator(is_anomalous=True, is_persistent=True, timestamp=ts)
        assert res1 == res2
        assert res1.to_dict() == res2.to_dict()

    def test_explanation_reason_generation(self):
        """14. Verify explainable reason generation contains itemized penalty breakdown."""
        res = calculate_structural_health_indicator(is_anomalous=True, is_persistent=True)
        dict_rep = res.to_dict()
        assert "deductions" in dict_rep
        assert dict_rep["deductions"]["anomaly_activity_deduction"] == 15.0
        assert dict_rep["deductions"]["persistence_deduction"] == 20.0
        assert len(res.evidence_summary) >= 5

    def test_status_mapping_enum_values(self):
        """15. Verify status maps directly to domain HealthStatus enum values."""
        res = calculate_structural_health_indicator(is_anomalous=False)
        assert isinstance(res.status, HealthStatus)
        assert res.status == HealthStatus.NORMAL

    def test_invalid_configuration(self):
        """16. Verify invalid config parameters raise InvalidHealthConfigError."""
        with pytest.raises(InvalidHealthConfigError, match="base_score must be in"):
            calculate_structural_health_indicator(config=SHIConfig(base_score=0.0))
        with pytest.raises(InvalidHealthConfigError, match="anomaly_penalty must be non-negative"):
            calculate_structural_health_indicator(config=SHIConfig(anomaly_penalty=-5.0))

    def test_zero_no_evidence(self):
        """17. Verify explicit zero evidence returns score 100.0."""
        res = calculate_structural_health_indicator(
            is_anomalous=False, is_persistent=False, is_cross_sensor=False, trend="STABLE"
        )
        assert res.score == 100.0

    def test_maximum_evidence(self):
        """18. Verify maximum evidence applies all 4 deductions (-75 pts total) -> score 25.0."""
        res = calculate_structural_health_indicator(
            is_anomalous=True, is_persistent=True, is_cross_sensor=True, trend="INCREASING"
        )
        assert res.score == 25.0
        assert res.status == HealthStatus.HIGH_PRIORITY_INSPECTION

    def test_conflicting_evidence(self):
        """19. Verify conflicting evidence (persistent anomaly + DECREASING trend) handles penalties deterministically."""
        res = calculate_structural_health_indicator(
            is_anomalous=True, is_persistent=True, is_cross_sensor=False, trend="DECREASING"
        )
        assert res.score == 65.0
        assert res.deductions.persistence_deduction == 20.0
        assert res.deductions.increasing_trend_deduction == 0.0

    def test_step_7_9_integration_compatibility(self, db_session):
        """20. Verify HealthService integration with SQLite database session and HealthSnapshot persistence."""
        mon_session = MonitoringSession(name="SHI Test Session", mode=SessionMode.LIVE, status=SessionStatus.RUNNING)
        db_session.add(mon_session)
        db_session.commit()

        zone = Zone(name="Zone-301")
        db_session.add(zone)
        db_session.commit()

        ref_t = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)

        # Create anomalous events
        e1 = Event(
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
        e2 = Event(
            session_id=mon_session.id,
            zone_id=zone.id,
            source_type=EventSourceType.SENSOR,
            source_id="PZT-02",
            timestamp=ref_t - timedelta(minutes=10),
            magnitude=10.0,
            energy=10.0,
            severity=EventSeverity.HIGH,
            status=EventStatus.DETECTED,
        )
        db_session.add_all([e1, e2])
        db_session.commit()

        service = HealthService(db_session)
        res = service.evaluate_zone_health(
            zone_id=zone.id,
            session_id=mon_session.id,
            reference_time=ref_t,
            persist_snapshot=True,
        )

        assert isinstance(res, StructuralHealthResult)
        assert res.zone_id == zone.id

        # Verify HealthSnapshot was persisted to SQLite DB
        snapshot = db_session.query(HealthSnapshot).filter_by(zone_id=zone.id).first()
        assert snapshot is not None
        assert snapshot.score == res.score
        assert snapshot.status == res.status
        assert snapshot.reason == res.reason
        assert "deductions" in snapshot.evidence
