"""Service layer orchestrating event anomaly analysis against stored zone baselines."""

from typing import Optional
from sqlalchemy.orm import Session

from app.anomaly.calculator import DEFAULT_ANOMALY_Z_THRESHOLD, analyze_event
from app.anomaly.exceptions import BaselineNotFoundError, InvalidEventDataError
from app.anomaly.types import AnomalyAnalysisResult
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.event_repository import EventRepository


class AnomalyService:
    """Service handling rule-based statistical anomaly detection for events."""

    def __init__(
        self,
        db: Session,
        baseline_repository: Optional[BaselineRepository] = None,
        event_repository: Optional[EventRepository] = None,
    ) -> None:
        self.db = db
        self.baseline_repository = baseline_repository or BaselineRepository(db)
        self.event_repository = event_repository or EventRepository(db)

    def analyze_event_by_id(
        self,
        event_id: int,
        z_threshold: float = DEFAULT_ANOMALY_Z_THRESHOLD,
    ) -> AnomalyAnalysisResult:
        """
        Retrieve an Event by ID, fetch the latest baseline for its zone, and perform anomaly analysis.

        Args:
            event_id: ID of event entity in database.
            z_threshold: Configurable z-score threshold (default 3.0).

        Returns:
            AnomalyAnalysisResult containing deviation analysis and explainable evidence.

        Raises:
            InvalidEventDataError: If event_id does not exist.
            BaselineNotFoundError: If no baseline exists for event's zone.
        """
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise InvalidEventDataError(f"Event with id {event_id} not found")

        baseline = self.baseline_repository.get_latest_for_zone(event.zone_id)
        if not baseline:
            raise BaselineNotFoundError(f"No Baseline found for zone id {event.zone_id}")

        return analyze_event(event=event, baseline=baseline, z_threshold=z_threshold)
