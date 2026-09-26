from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SessionMode, SessionStatus

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.health import HealthSnapshot


class MonitoringSession(Base):
    """Represents one period of structural monitoring or testing."""
    __tablename__ = "monitoring_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mode: Mapped[SessionMode] = mapped_column(
        Enum(SessionMode, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="session", cascade="all, delete-orphan"
    )
    health_snapshots: Mapped[List["HealthSnapshot"]] = relationship(
        "HealthSnapshot", back_populates="session", cascade="all, delete-orphan"
    )
