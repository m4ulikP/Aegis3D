from typing import Optional
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone


class EventRepository:
    """Repository handling database operations for Event entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, event_id: int) -> Optional[Event]:
        """Retrieve an Event by primary key ID."""
        return self.db.query(Event).filter(Event.id == event_id).first()

    def session_exists(self, session_id: int) -> bool:
        """Check if a MonitoringSession with session_id exists."""
        return self.db.query(MonitoringSession.id).filter(MonitoringSession.id == session_id).first() is not None

    def zone_exists(self, zone_id: int) -> bool:
        """Check if a Zone with zone_id exists."""
        return self.db.query(Zone.id).filter(Zone.id == zone_id).first() is not None

    def create(self, event: Event) -> Event:
        """Persist a new Event instance to the database."""
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
