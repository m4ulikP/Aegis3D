from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import HealthStatus, HealthTrend

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.monitoring_session import MonitoringSession
    from app.models.zone import Zone


class HealthSnapshot(Base):
    """Represents the structural-health state at a point in time."""
    __tablename__ = "health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[HealthStatus] = mapped_column(
        Enum(HealthStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    trend: Mapped[HealthTrend] = mapped_column(
        Enum(HealthTrend, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    session: Mapped["MonitoringSession"] = relationship("MonitoringSession", back_populates="health_snapshots")
    zone: Mapped["Zone"] = relationship("Zone", back_populates="health_snapshots")
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="health_snapshot", cascade="all, delete-orphan"
    )
