"""Pydantic schemas for telemetry ingestion contract and processing pipeline responses."""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AlertSeverity, EventSeverity, HealthStatus


class TelemetryIngestRequest(BaseModel):
    """Incoming sensor telemetry payload contract."""

    sensor_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Stable sensor identifier (e.g. 'PZT-Z1-01', 'PZT-Z2-01')",
    )
    zone_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Stable zone name (e.g. 'Zone 1 - Main Deck Girder', 'Zone 2 - Substructure Pier B')",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Acquisition timestamp in UTC",
    )
    sample_rate_hz: float = Field(
        ...,
        gt=0,
        le=1_000_000,
        description="Sampling frequency in Hertz (> 0)",
        validation_alias=AliasChoices("sample_rate_hz", "sample_rate"),
    )
    sequence: Optional[int] = Field(
        None,
        ge=0,
        description="Optional monotonic sequence packet counter",
    )
    samples: List[float] = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="1D discrete raw sensor sample values",
    )
    detection_threshold: Optional[float] = Field(
        None,
        gt=0,
        description="Optional custom event detection amplitude threshold override",
    )
    session_id: Optional[int] = Field(
        None,
        ge=1,
        description="Optional monitoring session ID override",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("samples")
    @classmethod
    def validate_samples_finite(cls, samples: List[float]) -> List[float]:
        """Ensure all samples are finite real numbers."""
        for idx, val in enumerate(samples):
            if val is None or math.isnan(val) or math.isinf(val):
                raise ValueError(f"Sample at index {idx} contains non-finite value: {val}")
        return samples


class ExtractedFeaturesSchema(BaseModel):
    """Summary of features extracted from a detected activity window."""

    peak_amplitude: float
    rms_amplitude: float
    energy: float
    duration_ms: float
    frequency_hz: Optional[float] = None
    sample_count: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TelemetryEventResult(BaseModel):
    """Details of a single structural event detected within the telemetry signal."""

    event_id: int
    magnitude: float
    energy: float
    duration_ms: float
    frequency_hz: Optional[float] = None
    severity: EventSeverity
    is_anomalous: bool = False
    magnitude_z_score: Optional[float] = None
    energy_z_score: Optional[float] = None
    anomaly_reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TelemetryIngestResponse(BaseModel):
    """Structured response returned by the telemetry ingestion pipeline."""

    status: str
    telemetry_accepted: bool = True
    sensor_id: str
    zone_id: int
    zone_name: str
    timestamp: datetime
    samples_count: int
    sample_rate_hz: float
    sequence: Optional[int] = None
    events_detected: int = 0
    events: List[TelemetryEventResult] = Field(default_factory=list)
    extracted_features: Optional[ExtractedFeaturesSchema] = None
    temporal_persistence_confirmed: Optional[bool] = None
    cross_sensor_correlation_confirmed: Optional[bool] = None
    health_score: Optional[float] = None
    health_status: Optional[HealthStatus] = None
    health_trend: Optional[str] = None
    alert_generated: bool = False
    alert_id: Optional[int] = None
    alert_severity: Optional[AlertSeverity] = None
    alert_title: Optional[str] = None
    message: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TelemetryLatestResponse(TelemetryIngestResponse):
    """Latest ingested telemetry snapshot with bounded sample window for UI visualization."""

    samples: List[float] = Field(
        default_factory=list,
        description="Bounded raw/filtered sample window for visual representation",
    )
    detection_threshold: Optional[float] = None
