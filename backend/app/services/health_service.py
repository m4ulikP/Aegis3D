"""Service layer orchestrating Structural Health Indicator (SHI) evaluation and snapshot persistence."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.health.calculator import calculate_structural_health_indicator
from app.health.types import SHIConfig, StructuralHealthResult
from app.models.enums import HealthTrend
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.event_repository import EventRepository
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.services.trend_service import TrendService


class HealthService:
    """Service layer orchestrating multi-step evidence gathering and Structural Health Indicator evaluation."""

    def __init__(
        self,
        db: Session,
        event_repository: Optional[EventRepository] = None,
        baseline_repository: Optional[BaselineRepository] = None,
        anomaly_service: Optional[AnomalyService] = None,
        correlation_service: Optional[CorrelationService] = None,
        trend_service: Optional[TrendService] = None,
    ) -> None:
        self.db = db
        self.event_repository = event_repository or EventRepository(db)
        self.baseline_repository = baseline_repository or BaselineRepository(db)
        self.anomaly_service = anomaly_service or AnomalyService(
            db,
            baseline_repository=self.baseline_repository,
            event_repository=self.event_repository,
        )
        self.correlation_service = correlation_service or CorrelationService(
            db,
            event_repository=self.event_repository,
            baseline_repository=self.baseline_repository,
            anomaly_service=self.anomaly_service,
        )
        self.trend_service = trend_service or TrendService(
            db,
            event_repository=self.event_repository,
            baseline_repository=self.baseline_repository,
            anomaly_service=self.anomaly_service,
            correlation_service=self.correlation_service,
        )

    def evaluate_zone_health(
        self,
        zone_id: int,
        session_id: Optional[int] = None,
        reference_time: Optional[datetime] = None,
        window_duration_seconds: float = 3600.0,
        persist_snapshot: bool = False,
        config: Optional[SHIConfig] = None,
    ) -> StructuralHealthResult:
        """
        Evaluate structural health indicator for a zone by integrating Step 7-9 evidence.

        Args:
            zone_id: Target zone ID.
            session_id: Optional monitoring session ID (required if persist_snapshot is True).
            reference_time: Optional reference end time. Defaults to current UTC time.
            window_duration_seconds: Analysis window duration in seconds (default 3600.0).
            persist_snapshot: If True, persists a HealthSnapshot record to the database.
            config: Optional custom SHIConfig instance.

        Returns:
            StructuralHealthResult containing score, status, itemized deductions, and explainable evidence.
        """
        ref_t = reference_time or datetime.now(timezone.utc)
        if ref_t.tzinfo is None:
            ref_t = ref_t.replace(tzinfo=timezone.utc)

        # 1. Step 9 Trend Evaluation
        trend_res = self.trend_service.evaluate_zone_trend(
            zone_id=zone_id,
            reference_time=ref_t,
            analysis_window_seconds=window_duration_seconds,
        )

        # 2. Step 8 Temporal Persistence Evaluation
        persistence_res = self.correlation_service.evaluate_zone_persistence(
            zone_id=zone_id,
            reference_time=ref_t,
            window_duration_seconds=min(300.0, window_duration_seconds),
        )

        # 3. Step 8 Cross-Sensor Correlation Evaluation
        start_t = ref_t - timedelta(seconds=window_duration_seconds)
        corr_groups = self.correlation_service.correlate_zone_events(
            zone_id=zone_id,
            valid_from=start_t,
            valid_until=ref_t,
        )
        is_cross_sensor = any(g.is_cross_sensor for g in corr_groups)

        # 4. Step 7 Individual Anomaly Check across window
        total_anom_events = trend_res.earlier_period.anomalous_events + trend_res.later_period.anomalous_events
        total_events = trend_res.earlier_period.total_events + trend_res.later_period.total_events
        is_anomalous = persistence_res.anomalous_events > 0 or total_anom_events > 0

        # Calculate SHI
        result = calculate_structural_health_indicator(
            is_anomalous=is_anomalous,
            is_persistent=persistence_res.is_persistent,
            is_cross_sensor=is_cross_sensor,
            trend=trend_res.overall_trend_direction,
            anomalous_event_count=total_anom_events,
            total_event_count=total_events,
            zone_id=zone_id,
            timestamp=ref_t,
            config=config,
        )

        # Map trend string to HealthTrend enum
        trend_enum_map = {
            "STABLE": HealthTrend.STABLE,
            "INCREASING": HealthTrend.INCREASING,
            "DECREASING": HealthTrend.DECREASING,
            "INSUFFICIENT_DATA": HealthTrend.STABLE,
        }
        health_trend_enum = trend_enum_map.get(result.trend, HealthTrend.STABLE)

        # Optionally persist HealthSnapshot
        if persist_snapshot and session_id is not None:
            snapshot = HealthSnapshot(
                session_id=session_id,
                zone_id=zone_id,
                timestamp=ref_t,
                score=result.score,
                status=result.status,
                trend=health_trend_enum,
                reason=result.reason,
                evidence=result.to_dict(),
            )
            self.db.add(snapshot)
            self.db.commit()

        return result
