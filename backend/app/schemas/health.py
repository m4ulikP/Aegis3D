from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict


class HealthSummaryResponse(BaseModel):
    """Schema for high-level dashboard monitoring health summary."""

    total_zones: int
    health_status_counts: Dict[str, int]
    active_alerts_count: int
    recent_events_count: int
    latest_timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
