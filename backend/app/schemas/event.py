from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EventSeverity, EventSourceType, EventStatus
from app.models.event import Event


class EventCreate(BaseModel):
    """Schema for creating a generic structural event observation."""

    session_id: int = Field(..., ge=1, description="ID of the associated monitoring session")
    zone_id: int = Field(..., ge=1, description="ID of the associated zone")
    source_type: EventSourceType = Field(..., description="Source type of observation (SIMULATOR, SENSOR, IMPORTED)")
    source_id: str = Field(..., min_length=1, max_length=255, description="Generic source identifier (e.g. SIM-01, PZT-01)")
    correlation_id: Optional[str] = Field(None, max_length=255, description="Optional correlation identifier across multiple sources")
    timestamp: datetime = Field(..., description="Timestamp of observation")
    magnitude: Optional[float] = Field(None, ge=0.0, description="Event magnitude physical measurement (>= 0)")
    energy: Optional[float] = Field(None, ge=0.0, description="Event energy measurement (>= 0)")
    duration_ms: Optional[float] = Field(None, ge=0.0, description="Event duration in milliseconds (>= 0)")
    frequency_hz: Optional[float] = Field(None, ge=0.0, description="Event frequency in Hz (>= 0)")
    severity: EventSeverity = Field(default=EventSeverity.LOW, description="Observation severity rating")
    status: EventStatus = Field(default=EventStatus.DETECTED, description="Observation status")
    metadata: Optional[Dict[str, Any]] = Field(None, serialization_alias="metadata", validation_alias="metadata", description="Arbitrary metadata payload")

    model_config = ConfigDict(populate_by_name=True)


class EventResponse(BaseModel):
    """Schema for returning a structural event observation."""

    id: int
    session_id: int
    zone_id: int
    source_type: EventSourceType
    source_id: str
    correlation_id: Optional[str] = None
    timestamp: datetime
    magnitude: Optional[float] = None
    energy: Optional[float] = None
    duration_ms: Optional[float] = None
    frequency_hz: Optional[float] = None
    severity: EventSeverity
    status: EventStatus
    metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def from_orm_event(cls, event: Event) -> "EventResponse":
        """Convert a SQLAlchemy Event instance to EventResponse."""
        return cls(
            id=event.id,
            session_id=event.session_id,
            zone_id=event.zone_id,
            source_type=event.source_type,
            source_id=event.source_id,
            correlation_id=event.correlation_id,
            timestamp=event.timestamp,
            magnitude=event.magnitude,
            energy=event.energy,
            duration_ms=event.duration_ms,
            frequency_hz=event.frequency_hz,
            severity=event.severity,
            status=event.status,
            metadata=event.metadata_json,
        )
