from sqlalchemy.orm import Session

from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate


class SessionNotFoundError(Exception):
    """Raised when referenced MonitoringSession does not exist."""
    pass


class ZoneNotFoundError(Exception):
    """Raised when referenced Zone does not exist."""
    pass


class EventNotFoundError(Exception):
    """Raised when requested Event does not exist."""
    pass


class EventService:
    """Service handling business rules and orchestration for Event entities."""

    def __init__(self, db: Session) -> None:
        self.repository = EventRepository(db)

    def create_event(self, event_in: EventCreate) -> Event:
        """Validate referenced entities and create a new structural observation event."""
        if not self.repository.session_exists(event_in.session_id):
            raise SessionNotFoundError(f"MonitoringSession with id {event_in.session_id} not found")

        if not self.repository.zone_exists(event_in.zone_id):
            raise ZoneNotFoundError(f"Zone with id {event_in.zone_id} not found")

        db_event = Event(
            session_id=event_in.session_id,
            zone_id=event_in.zone_id,
            source_type=event_in.source_type,
            source_id=event_in.source_id,
            correlation_id=event_in.correlation_id,
            timestamp=event_in.timestamp,
            magnitude=event_in.magnitude,
            energy=event_in.energy,
            duration_ms=event_in.duration_ms,
            frequency_hz=event_in.frequency_hz,
            severity=event_in.severity,
            status=event_in.status,
            metadata_json=event_in.metadata,
        )
        return self.repository.create(db_event)

    def get_event(self, event_id: int) -> Event:
        """Retrieve an Event by ID or raise EventNotFoundError."""
        event = self.repository.get_by_id(event_id)
        if not event:
            raise EventNotFoundError(f"Event with id {event_id} not found")
        return event
