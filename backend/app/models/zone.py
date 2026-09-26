from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.baseline import Baseline
    from app.models.event import Event
    from app.models.health import HealthSnapshot


class Zone(Base):
    """Represents a logical/physical area of the monitored structure."""
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    floor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="zone", cascade="all, delete-orphan"
    )
    baselines: Mapped[List["Baseline"]] = relationship(
        "Baseline", back_populates="zone", cascade="all, delete-orphan"
    )
    health_snapshots: Mapped[List["HealthSnapshot"]] = relationship(
        "HealthSnapshot", back_populates="zone", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="zone", cascade="all, delete-orphan"
    )
