from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertSeverity, AlertStatus


class AlertResponse(BaseModel):
    """Schema for returning an actionable alert instance."""

    id: int
    health_snapshot_id: int
    zone_id: int
    timestamp: datetime
    severity: AlertSeverity
    title: str
    message: str
    status: AlertStatus
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
