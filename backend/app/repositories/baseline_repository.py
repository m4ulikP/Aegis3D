"""Repository handling database queries and persistence for Baseline entities."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.baseline import Baseline
from app.models.enums import EventStatus
from app.models.event import Event
from app.models.zone import Zone


class BaselineRepository:
    """Repository handling database operations for Baseline entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def zone_exists(self, zone_id: int) -> bool:
        """Check if a Zone with zone_id exists."""
        return self.db.query(Zone.id).filter(Zone.id == zone_id).first() is not None

    def get_qualifying_events_for_zone(
        self,
        zone_id: int,
        valid_from: datetime,
        valid_until: datetime,
    ) -> List[Event]:
        """
        Retrieve qualifying events for baseline calculation.

        Qualifying criteria:
        - Belongs to zone_id
        - Timestamp is within [valid_from, valid_until]
        - Status is not DISMISSED
        - magnitude is not None
        - energy is not None
        """
        return (
            self.db.query(Event)
            .filter(
                Event.zone_id == zone_id,
                Event.timestamp >= valid_from,
                Event.timestamp <= valid_until,
                Event.status != EventStatus.DISMISSED,
                Event.magnitude.isnot(None),
                Event.energy.isnot(None),
            )
            .order_by(Event.timestamp.asc())
            .all()
        )

    def create(self, baseline: Baseline) -> Baseline:
        """Persist a new Baseline entity instance to the database."""
        self.db.add(baseline)
        self.db.commit()
        self.db.refresh(baseline)
        return baseline

    def get_by_id(self, baseline_id: int) -> Optional[Baseline]:
        """Retrieve a Baseline by primary key ID."""
        return self.db.query(Baseline).filter(Baseline.id == baseline_id).first()

    def get_latest_for_zone(self, zone_id: int) -> Optional[Baseline]:
        """Retrieve the most recently created Baseline for a zone."""
        return (
            self.db.query(Baseline)
            .filter(Baseline.zone_id == zone_id)
            .order_by(Baseline.created_at.desc(), Baseline.id.desc())
            .first()
        )
