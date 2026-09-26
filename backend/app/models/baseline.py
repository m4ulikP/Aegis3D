from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.zone import Zone


class Baseline(Base):
    """Represents the normal statistical behavior of a monitored zone."""
    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mean_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    std_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    mean_energy: Mapped[float] = mapped_column(Float, nullable=False)
    std_energy: Mapped[float] = mapped_column(Float, nullable=False)
    normal_event_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    zone: Mapped["Zone"] = relationship("Zone", back_populates="baselines")
