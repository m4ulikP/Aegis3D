"""Service orchestrating temporal persistence evaluation, 2-PZT event correlation, and evidence aggregation."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.anomaly.exceptions import BaselineNotFoundError, InvalidEventDataError
from app.anomaly.types import AnomalyAnalysisResult
from app.correlation.evidence import aggregate_event_evidence
from app.correlation.sensor_correlation import correlate_two_pzt_events
from app.correlation.temporal import evaluate_temporal_persistence
from app.correlation.types import (
    DEFAULT_CORRELATION_TOLERANCE_SECONDS,
    DEFAULT_MIN_ANOMALY_COUNT,
    DEFAULT_MIN_ANOMALY_RATIO,
    DEFAULT_PERSISTENCE_WINDOW_SECONDS,
    AggregatedEvidenceResult,
    CorrelatedEventGroup,
    TemporalPersistenceResult,
)
from app.models.enums import EventStatus
from app.models.event import Event
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.event_repository import EventRepository
from app.services.anomaly_service import AnomalyService


class CorrelationService:
    """Service layer coordinating temporal persistence and cross-sensor event correlation."""

    def __init__(
        self,
        db: Session,
        event_repository: Optional[EventRepository] = None,
        baseline_repository: Optional[BaselineRepository] = None,
        anomaly_service: Optional[AnomalyService] = None,
    ) -> None:
        self.db = db
        self.event_repository = event_repository or EventRepository(db)
        self.baseline_repository = baseline_repository or BaselineRepository(db)
        self.anomaly_service = anomaly_service or AnomalyService(
            db,
            baseline_repository=self.baseline_repository,
            event_repository=self.event_repository,
        )

    def evaluate_zone_persistence(
        self,
        zone_id: int,
        reference_time: Optional[datetime] = None,
        window_duration_seconds: float = DEFAULT_PERSISTENCE_WINDOW_SECONDS,
        min_anomaly_count: int = DEFAULT_MIN_ANOMALY_COUNT,
        min_anomaly_ratio: float = DEFAULT_MIN_ANOMALY_RATIO,
    ) -> TemporalPersistenceResult:
        """
        Query historical events for a zone in an observation window and evaluate temporal persistence.
        """
        ref_t = reference_time or datetime.now(timezone.utc)
        if ref_t.tzinfo is None:
            ref_t = ref_t.replace(tzinfo=timezone.utc)

        start_t = ref_t - timedelta(seconds=window_duration_seconds)

        # Retrieve events in window
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

        baseline = self.baseline_repository.get_latest_for_zone(zone_id)

        event_items: List[dict] = []
        for evt in events:
            if baseline and evt.magnitude is not None and evt.energy is not None:
                try:
                    anom_res = self.anomaly_service.analyze_event(event=evt, baseline=baseline)
                    is_anom = anom_res.is_anomalous
                except Exception:
                    is_anom = False
            else:
                is_anom = False

            event_items.append(
                {
                    "id": evt.id,
                    "timestamp": evt.timestamp,
                    "is_anomalous": is_anom,
                }
            )

        return evaluate_temporal_persistence(
            events=event_items,
            window_duration_seconds=window_duration_seconds,
            min_anomaly_count=min_anomaly_count,
            min_anomaly_ratio=min_anomaly_ratio,
            reference_time=ref_t,
        )

    def correlate_zone_events(
        self,
        zone_id: int,
        valid_from: datetime,
        valid_until: datetime,
        tolerance_seconds: float = DEFAULT_CORRELATION_TOLERANCE_SECONDS,
    ) -> List[CorrelatedEventGroup]:
        """
        Query events for a zone within [valid_from, valid_until] and group them by sensor correlation.
        """
        events = (
            self.db.query(Event)
            .filter(
                Event.zone_id == zone_id,
                Event.timestamp >= valid_from,
                Event.timestamp <= valid_until,
                Event.status != EventStatus.DISMISSED,
            )
            .order_by(Event.timestamp.asc())
            .all()
        )

        return correlate_two_pzt_events(
            events=events,
            tolerance_seconds=tolerance_seconds,
            target_zone_id=zone_id,
        )

    def evaluate_event_evidence(
        self,
        event_id: int,
        window_duration_seconds: float = DEFAULT_PERSISTENCE_WINDOW_SECONDS,
        tolerance_seconds: float = DEFAULT_CORRELATION_TOLERANCE_SECONDS,
    ) -> AggregatedEvidenceResult:
        """
        Analyze a specific event by ID, evaluating its individual anomaly status, zone temporal persistence,
        and two-PZT sensor correlation into unified aggregated evidence.
        """
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise InvalidEventDataError(f"Event with id {event_id} not found")

        # 1. Individual Anomaly
        try:
            anom_res: Optional[AnomalyAnalysisResult] = self.anomaly_service.analyze_event_by_id(event_id)
            is_anomalous = anom_res.is_anomalous
            anom_reasons = list(anom_res.reasons)
        except BaselineNotFoundError:
            anom_res = None
            is_anomalous = False
            anom_reasons = ["No Baseline available for zone anomaly evaluation"]

        # 2. Temporal Persistence
        persistence_res = self.evaluate_zone_persistence(
            zone_id=event.zone_id,
            reference_time=event.timestamp,
            window_duration_seconds=window_duration_seconds,
        )

        # 3. Two-PZT Sensor Correlation
        start_t = event.timestamp - timedelta(seconds=tolerance_seconds)
        end_t = event.timestamp + timedelta(seconds=tolerance_seconds)
        corr_groups = self.correlate_zone_events(
            zone_id=event.zone_id,
            valid_from=start_t,
            valid_until=end_t,
            tolerance_seconds=tolerance_seconds,
        )

        target_group: Optional[CorrelatedEventGroup] = None
        for group in corr_groups:
            if event_id in group.event_ids:
                target_group = group
                break

        # Optionally persist group_id into event.correlation_id if not set
        if target_group and not event.correlation_id:
            event.correlation_id = target_group.group_id
            self.db.commit()

        return aggregate_event_evidence(
            is_anomalous=is_anomalous,
            persistence_result=persistence_res,
            correlation_group=target_group,
            primary_event_id=event.id,
            anomaly_reasons=anom_reasons,
        )
