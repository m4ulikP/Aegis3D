from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EventSeverity, EventSourceType, EventStatus

if TYPE_CHECKING:
    from app.models.monitoring_session import MonitoringSession
    from app.models.zone import Zone


class Event(Base):
    """Central domain object: A noteworthy structural observation occurred."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[EventSourceType] = mapped_column(
        Enum(EventSourceType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    magnitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    energy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    frequency_hz: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    session: Mapped["MonitoringSession"] = relationship("MonitoringSession", back_populates="events")
    zone: Mapped["Zone"] = relationship("Zone", back_populates="events")
