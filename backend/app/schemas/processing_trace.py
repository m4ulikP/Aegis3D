"""Pydantic schemas for the Telemetry Processing Inspector trace."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AlertSeverity, AlertStatus, EventSeverity, HealthStatus


class TraceMetadata(BaseModel):
    """Metadata identifying the telemetry acquisition and processing trace."""

    trace_id: str = Field(..., description="Unique identifier for the processing trace")
    event_id: Optional[int] = Field(None, description="Primary event database ID if an event was detected")
    sensor_id: str = Field(..., description="Transducer/sensor identifier (e.g. 'PZT-Z1-01')")
    zone_id: int = Field(..., description="Target structural monitoring zone ID")
    zone_name: str = Field(..., description="Target structural monitoring zone name")
    timestamp: datetime = Field(..., description="Acquisition timestamp in UTC")
    sequence: Optional[int] = Field(None, description="Monotonic sequence counter from telemetry packet")
    sample_rate_hz: float = Field(..., description="Sampling frequency in Hertz")
    samples_count: int = Field(..., description="Total count of raw discrete samples ingested")
    session_id: Optional[int] = Field(None, description="Associated monitoring session ID")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RawTelemetryTrace(BaseModel):
    """Raw telemetry ingestion parameters and bounded sample window."""

    sensor_id: str
    zone_name: str
    timestamp: datetime
    sample_rate_hz: float
    samples_count: int
    sequence: Optional[int] = None
    samples_bounded: List[float] = Field(
        default_factory=list,
        description="Bounded sample array (up to 500 points) for visual representation",
    )
    peak_amplitude: float = Field(..., description="Maximum absolute amplitude in raw samples")
    rms_amplitude: float = Field(..., description="Root mean square amplitude of raw samples")
    is_bounded: bool = Field(True, description="True if sample array was bounded/downsampled for display")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConditioningTrace(BaseModel):
    """Actual signal conditioning operations applied to the raw signal."""

    dc_removal_applied: bool = Field(True, description="Whether mean-subtraction DC offset removal was applied")
    dc_offset_removed: Optional[float] = Field(None, description="Calculated DC offset subtracted from raw samples")
    filter_applied: bool = Field(False, description="Whether digital smoothing filter was applied")
    filter_type: Optional[str] = Field(None, description="Type of filter applied (e.g. 'MOVING_AVERAGE', 'BUTTERWORTH')")
    filter_window_size: Optional[int] = Field(None, description="Filter window size in samples")
    conditioned_samples_bounded: Optional[List[float]] = Field(
        None,
        description="Bounded sample array after DC removal and filtering",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DetectedWindowTrace(BaseModel):
    """Details of a single detected activity window."""

    start_index: int
    end_index: int
    start_time_ms: float
    end_time_ms: float
    duration_ms: float
    peak_amplitude: float
    rms_amplitude: float
    sample_count: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventDetectionTrace(BaseModel):
    """Event window detection stage results."""

    detection_threshold: float = Field(..., description="Amplitude threshold used for event triggering")
    events_detected_count: int = Field(0, description="Total count of distinct activity windows detected")
    events_detected: bool = Field(False, description="True if at least one activity window exceeded threshold")
    min_duration_samples: int = Field(1, description="Minimum duration constraint in samples")
    merge_gap_samples: int = Field(2, description="Gap bridging size constraint in samples")
    detected_windows: List[DetectedWindowTrace] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FeatureExtractionTrace(BaseModel):
    """Temporal and spectral features extracted from detected activity."""

    event_id: Optional[int] = None
    peak_amplitude: Optional[float] = None
    rms_amplitude: Optional[float] = None
    energy: Optional[float] = Field(None, description="Discrete signal energy (sum(x[n]^2))")
    duration_ms: Optional[float] = None
    frequency_hz: Optional[float] = Field(None, description="Dominant frequency from FFT spectrum analysis")
    sample_count: Optional[int] = None
    features_dict: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BaselineTrace(BaseModel):
    """Zone statistical baseline parameters used for anomaly evaluation."""

    baseline_id: Optional[int] = None
    zone_id: int
    mean_magnitude: Optional[float] = None
    std_magnitude: Optional[float] = None
    mean_energy: Optional[float] = None
    std_energy: Optional[float] = None
    normal_event_rate: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    baseline_available: bool = Field(False, description="True if a valid historical baseline was available for the zone")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AnomalyEvaluationTrace(BaseModel):
    """Rule-based statistical anomaly detection evaluation."""

    evaluated: bool = Field(False, description="True if anomaly evaluation was executed (requires detected event and baseline)")
    is_anomalous: bool = False
    magnitude_z_score: Optional[float] = None
    energy_z_score: Optional[float] = None
    magnitude_anomalous: Optional[bool] = None
    energy_anomalous: Optional[bool] = None
    z_threshold: float = Field(3.0, description="Standardized deviation threshold (|z| >= 3.0 sigma)")
    severity: Optional[EventSeverity] = None
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PersistenceTrace(BaseModel):
    """Rolling temporal persistence evaluation across zone events."""

    evaluated: bool = Field(False, description="True if persistence evaluation was executed")
    is_persistent: bool = False
    total_events_in_window: int = 0
    anomalous_events_in_window: int = 0
    anomaly_ratio: float = 0.0
    max_consecutive_anomalies: int = 0
    window_duration_seconds: float = 300.0
    min_anomaly_count_required: int = 3
    min_anomaly_ratio_required: float = 0.50
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CorrelationTrace(BaseModel):
    """Two-PZT cross-sensor time-difference-of-arrival (TDOA) correlation."""

    evaluated: bool = Field(False, description="True if cross-sensor correlation evaluation was executed")
    is_cross_sensor_correlated: bool = False
    correlated_group_id: Optional[str] = None
    participating_sensors: List[str] = Field(default_factory=list)
    event_ids: List[int] = Field(default_factory=list)
    temporal_spread_ms: Optional[float] = None
    tolerance_seconds: float = 0.025
    relative_source_hint: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrendTrace(BaseModel):
    """Deterministic sub-period zone trend analysis."""

    evaluated: bool = Field(False, description="True if trend evaluation was executed")
    overall_trend: Optional[str] = Field(None, description="STABLE, INCREASING, DECREASING, or INSUFFICIENT_DATA")
    rate_delta: Optional[float] = None
    magnitude_delta: Optional[float] = None
    earlier_period_events: Optional[int] = None
    later_period_events: Optional[int] = None
    earlier_period_anomaly_rate: Optional[float] = None
    later_period_anomaly_rate: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HealthTrace(BaseModel):
    """Deterministic Structural Health Indicator (SHI) score and deductions."""

    evaluated: bool = Field(False, description="True if health evaluation was executed")
    health_score: Optional[float] = Field(None, description="Prototype 0-100 monitoring score")
    health_status: Optional[HealthStatus] = None
    trend: Optional[str] = None
    deductions: Optional[Dict[str, float]] = Field(
        None,
        description="Itemized score penalty deductions (anomaly, persistence, correlation, trend)",
    )
    reason: Optional[str] = None
    evidence_summary: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "SHI is a prototype evidence-based monitoring indicator derived from observed signal/event behavior. "
        "It is not a certified structural safety score and does not independently establish structural damage or failure."
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertTrace(BaseModel):
    """System alert generation information."""

    alert_generated: bool = False
    alert_id: Optional[int] = None
    alert_severity: Optional[AlertSeverity] = None
    alert_status: Optional[AlertStatus] = None
    alert_title: Optional[str] = None
    alert_message: Optional[str] = None
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProcessingTraceResponse(BaseModel):
    """
    Complete, end-to-end telemetry processing trace exposing verified evidence from ingestion through alert.
    """

    metadata: TraceMetadata
    ingestion: RawTelemetryTrace
    conditioning: ConditioningTrace
    event_detection: EventDetectionTrace
    features: Optional[FeatureExtractionTrace] = None
    baseline: BaselineTrace
    anomaly: AnomalyEvaluationTrace
    persistence: PersistenceTrace
    correlation: CorrelationTrace
    trend: TrendTrace
    health: HealthTrace
    alert: AlertTrace

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
