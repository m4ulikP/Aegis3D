from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import HealthStatus, HealthTrend


class ZoneResponse(BaseModel):
    """Schema for basic Zone information."""

    id: int
    name: str
    floor: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ZoneDetailResponse(BaseModel):
    """Schema for detailed Zone metadata including counts and status."""

    id: int
    name: str
    floor: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    event_count: int = 0
    active_alert_count: int = 0
    latest_health_status: Optional[HealthStatus] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


SHI_DISCLAIMER_TEXT = (
    "SHI is a prototype evidence-based monitoring indicator derived from observed signal/event behavior. "
    "It is not a certified structural safety score and does not independently establish structural damage or failure."
)


class ZoneHealthResponse(BaseModel):
    """Schema for Structural Health Indicator response for a zone."""

    zone_id: int
    score: float
    status: HealthStatus
    trend: HealthTrend
    reason: str
    timestamp: datetime
    evidence: Optional[Dict[str, Any]] = None
    disclaimer: str = SHI_DISCLAIMER_TEXT

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PeriodMetricsSchema(BaseModel):
    """Sub-schema for trend metrics during a specific analysis sub-period."""

    total_events: int
    anomalous_events: int
    anomaly_rate: float
    mean_magnitude: Optional[float] = 0.0
    persistent_anomaly_count: int
    cross_sensor_event_count: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ZoneTrendResponse(BaseModel):
    """Schema for zone trend analysis results."""

    zone_id: int
    overall_trend_direction: str
    event_rate_change_ratio: float
    magnitude_delta: float
    is_statistically_significant: bool
    reason: str
    earlier_period: PeriodMetricsSchema
    later_period: PeriodMetricsSchema

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CorrelatedGroupSchema(BaseModel):
    """Sub-schema for a two-PZT correlated event group."""

    group_id: str
    event_ids: List[int]
    temporal_spread_ms: float
    is_cross_sensor: bool
    relative_source_hint: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TemporalPersistenceSchema(BaseModel):
    """Sub-schema for temporal persistence evaluation metrics."""

    is_persistent: bool
    total_events: int
    anomalous_events: int
    anomaly_ratio: float
    window_duration_seconds: float

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


CORRELATION_NOTE_TEXT = "Provides two-PZT relative source indication. Precise 2D/3D localization is not supported."


class ZoneCorrelationResponse(BaseModel):
    """Schema for zone temporal persistence and cross-sensor correlation results."""

    zone_id: int
    temporal_persistence: TemporalPersistenceSchema
    correlated_groups_count: int
    cross_sensor_groups_count: int
    correlated_groups: List[CorrelatedGroupSchema]
    note: str = CORRELATION_NOTE_TEXT

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
