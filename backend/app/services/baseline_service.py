"""Service layer for computing and persisting statistical baselines."""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.baseline.calculator import DEFAULT_MIN_EVENTS, calculate_baseline_statistics
from app.baseline.exceptions import ZoneNotFoundError
from app.models.baseline import Baseline
from app.repositories.baseline_repository import BaselineRepository


class BaselineService:
    """Service handling business orchestration for Baseline generation."""

    def __init__(self, db: Session, repository: Optional[BaselineRepository] = None) -> None:
        self.db = db
        self.repository = repository or BaselineRepository(db)

    def build_baseline(
        self,
        zone_id: int,
        valid_from: datetime,
        valid_until: datetime,
        min_events: int = DEFAULT_MIN_EVENTS,
    ) -> Baseline:
        """
        Derive and persist a statistical baseline for a specified Zone over a historical window.

        Args:
            zone_id: Target zone ID.
            valid_from: Start of historical observation period.
            valid_until: End of historical observation period.
            min_events: Minimum number of qualifying events required (default 10).

        Returns:
            Persisted Baseline entity instance.

        Raises:
            ZoneNotFoundError: If zone_id does not exist.
            InvalidTimeWindowError: If valid_until <= valid_from.
            InsufficientDataError: If qualifying events count < min_events.
        """
        if not self.repository.zone_exists(zone_id):
            raise ZoneNotFoundError(f"Zone with id {zone_id} not found")

        events = self.repository.get_qualifying_events_for_zone(
            zone_id=zone_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        magnitudes = [e.magnitude for e in events if e.magnitude is not None]
        energies = [e.energy for e in events if e.energy is not None]

        stats = calculate_baseline_statistics(
            magnitudes=magnitudes,
            energies=energies,
            valid_from=valid_from,
            valid_until=valid_until,
            min_events=min_events,
        )

        baseline = Baseline(
            zone_id=zone_id,
            mean_magnitude=stats.mean_magnitude,
            std_magnitude=stats.std_magnitude,
            mean_energy=stats.mean_energy,
            std_energy=stats.std_energy,
            normal_event_rate=stats.normal_event_rate,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        return self.repository.create(baseline)

    def get_latest_baseline(self, zone_id: int) -> Optional[Baseline]:
        """Retrieve the latest baseline for a zone or None if none exists."""
        if not self.repository.zone_exists(zone_id):
            raise ZoneNotFoundError(f"Zone with id {zone_id} not found")
        return self.repository.get_latest_for_zone(zone_id)
