"""Service layer orchestrating zone trend analysis by integrating database events with anomaly and correlation evidence."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.anomaly.exceptions import BaselineNotFoundError
from app.correlation.types import DEFAULT_CORRELATION_TOLERANCE_SECONDS
from app.models.enums import EventStatus
from app.models.event import Event
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.event_repository import EventRepository
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.trend.evaluator import evaluate_zone_trend
from app.trend.types import (
    DEFAULT_MAGNITUDE_DELTA_THRESHOLD,
    DEFAULT_MIN_EVENTS_PER_PERIOD,
    DEFAULT_TREND_DELTA_THRESHOLD,
    DEFAULT_TREND_WINDOW_SECONDS,
    ZoneTrendResult,
)


class TrendService:
    """Service layer orchestrating deterministic zone trend evaluation across historical database events."""

    def __init__(
        self,
        db: Session,
        event_repository: Optional[EventRepository] = None,
        baseline_repository: Optional[BaselineRepository] = None,
        anomaly_service: Optional[AnomalyService] = None,
        correlation_service: Optional[CorrelationService] = None,
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

    def evaluate_zone_trend(
        self,
        zone_id: int,
        reference_time: Optional[datetime] = None,
        analysis_window_seconds: float = DEFAULT_TREND_WINDOW_SECONDS,
        trend_delta_threshold: float = DEFAULT_TREND_DELTA_THRESHOLD,
        min_events_per_period: int = DEFAULT_MIN_EVENTS_PER_PERIOD,
        magnitude_delta_threshold: float = DEFAULT_MAGNITUDE_DELTA_THRESHOLD,
    ) -> ZoneTrendResult:
        """
        Query historical events for a zone over an analysis window, enrich with anomaly & Step 8 correlation
        evidence, and calculate deterministic zone trend.

        Args:
            zone_id: Target zone ID.
            reference_time: Optional window end reference time. Defaults to UTC now.
            analysis_window_seconds: Observation window in seconds (default 3600.0).
            trend_delta_threshold: Rate change threshold (default 0.10).
            min_events_per_period: Minimum events required per sub-period (default 2).
            magnitude_delta_threshold: Magnitude change threshold (default 0.5).

        Returns:
            ZoneTrendResult dataclass containing deterministic trend assessment.
        """
        ref_t = reference_time or datetime.now(timezone.utc)
        if ref_t.tzinfo is None:
            ref_t = ref_t.replace(tzinfo=timezone.utc)

        start_t = ref_t - timedelta(seconds=analysis_window_seconds)

        # Retrieve zone events within [start_t, ref_t]
        events = (
            self.db.query(Event)
            .filter(
                Event.zone_id == zone_id,
                Event.timestamp >= start_t,
                Event.timestamp <= ref_t,
                Event.status != EventStatus.DISMISSED,
            )
            .order_by(Event.timestamp.asc())
            .all()
        )

        event_items: List[Dict[str, Any]] = []
        for evt in events:
            try:
                evidence = self.correlation_service.evaluate_event_evidence(
                    event_id=evt.id,
                    window_duration_seconds=analysis_window_seconds / 2.0 if analysis_window_seconds > 0 else 300.0,
                )
                is_anom = evidence.is_anomalous
                is_pers = evidence.is_persistent
                is_cross = evidence.is_cross_sensor
            except BaselineNotFoundError:
                is_anom = False
                is_pers = False
                is_cross = False
            except Exception:
                is_anom = False
                is_pers = False
                is_cross = False

            event_items.append(
                {
                    "id": evt.id,
                    "timestamp": evt.timestamp,
                    "zone_id": evt.zone_id,
                    "is_anomalous": is_anom,
                    "magnitude": evt.magnitude,
                    "is_persistent": is_pers,
                    "is_cross_sensor": is_cross,
                }
            )

        return evaluate_zone_trend(
            events=event_items,
            analysis_window_seconds=analysis_window_seconds,
            trend_delta_threshold=trend_delta_threshold,
            min_events_per_period=min_events_per_period,
            magnitude_delta_threshold=magnitude_delta_threshold,
            reference_time=ref_t,
            target_zone_id=zone_id,
        )
