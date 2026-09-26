"""Data types and result representations for temporal persistence and 2-PZT event correlation."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PERSISTENCE_WINDOW_SECONDS: float = 300.0  # 5-minute rolling window
DEFAULT_MIN_ANOMALY_COUNT: int = 3
DEFAULT_MIN_ANOMALY_RATIO: float = 0.5
DEFAULT_CORRELATION_TOLERANCE_SECONDS: float = 0.025  # 25 milliseconds


class EvidenceCategory(str, Enum):
    """Categories of aggregated evidence for structural anomaly observations."""
    NORMAL_OBSERVATION = "NORMAL_OBSERVATION"
    INDIVIDUAL_ANOMALY = "INDIVIDUAL_ANOMALY"
    PERSISTENT_ANOMALY = "PERSISTENT_ANOMALY"
    CROSS_SENSOR_CORRELATED = "CROSS_SENSOR_CORRELATED"
    PERSISTENT_AND_CROSS_SENSOR_CORRELATED = "PERSISTENT_AND_CROSS_SENSOR_CORRELATED"


@dataclass(frozen=True)
class TemporalPersistenceResult:
    """
    Pure numerical result of temporal persistence evaluation over an observation window.

    Attributes:
        is_persistent: True if anomaly sequence meets or exceeds persistence criteria.
        total_events: Total number of events in the time window.
        anomalous_events: Number of anomalous events in the time window.
        anomaly_ratio: Proportion of anomalous events in the window (0.0 to 1.0).
        max_consecutive_anomalies: Maximum consecutive anomalous events.
        time_span_seconds: Time difference between earliest and latest event in window.
        window_duration_seconds: Configured temporal window duration.
        min_anomaly_count_used: Minimum anomaly count threshold used.
        min_anomaly_ratio_used: Minimum anomaly ratio threshold used.
        reasons: Tuple of human-readable explainable evidence strings.
    """
    is_persistent: bool
    total_events: int
    anomalous_events: int
    anomaly_ratio: float
    max_consecutive_anomalies: int
    time_span_seconds: float
    window_duration_seconds: float
    min_anomaly_count_used: int
    min_anomaly_ratio_used: float
    reasons: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "is_persistent": self.is_persistent,
            "total_events": self.total_events,
            "anomalous_events": self.anomalous_events,
            "anomaly_ratio": self.anomaly_ratio,
            "max_consecutive_anomalies": self.max_consecutive_anomalies,
            "time_span_seconds": self.time_span_seconds,
            "window_duration_seconds": self.window_duration_seconds,
            "min_anomaly_count_used": self.min_anomaly_count_used,
            "min_anomaly_ratio_used": self.min_anomaly_ratio_used,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CorrelatedEventGroup:
    """
    Result representing two-PZT sensor event correlation across a temporal tolerance window.

    Note:
        - Aegis3D assumes a two-PZT sensor setup.
        - Two-PZT correlation indicates relative source arrival times, NOT precise 3D spatial localization.

    Attributes:
        group_id: Unique deterministic correlation identifier.
        zone_id: Zone ID of correlated events.
        participating_sensors: Tuple of unique sensor source IDs (e.g., PZT-01, PZT-02).
        event_ids: Tuple of participating event IDs (or indices).
        start_timestamp: Earliest event timestamp in correlation group.
        end_timestamp: Latest event timestamp in correlation group.
        event_count: Total event count in correlation group.
        sensor_count: Count of distinct participating sensors.
        is_cross_sensor: True if events were detected across 2 or more distinct sensors.
        temporal_spread_ms: Time spread between earliest and latest event in milliseconds.
        relative_source_hint: Human-readable relative source indication string.
    """
    group_id: str
    zone_id: int
    participating_sensors: Tuple[str, ...]
    event_ids: Tuple[Any, ...]
    start_timestamp: datetime
    end_timestamp: datetime
    event_count: int
    sensor_count: int
    is_cross_sensor: bool
    temporal_spread_ms: float
    relative_source_hint: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "group_id": self.group_id,
            "zone_id": self.zone_id,
            "participating_sensors": list(self.participating_sensors),
            "event_ids": list(self.event_ids),
            "start_timestamp": self.start_timestamp.isoformat(),
            "end_timestamp": self.end_timestamp.isoformat(),
            "event_count": self.event_count,
            "sensor_count": self.sensor_count,
            "is_cross_sensor": self.is_cross_sensor,
            "temporal_spread_ms": self.temporal_spread_ms,
            "relative_source_hint": self.relative_source_hint,
        }


@dataclass(frozen=True)
class AggregatedEvidenceResult:
    """
    Combined evidence representation aggregating individual anomaly status, temporal persistence,
    and cross-sensor correlation.

    Note:
        - Aegis3D uses aggregated evidence to inform subsequent structural health evaluation.
        - This output represents evidence accumulation, NOT a certified structural safety assessment or severity rating.

    Attributes:
        category: EvidenceCategory classification.
        is_anomalous: True if primary event was flagged anomalous.
        is_persistent: True if temporal persistence criteria was satisfied.
        is_cross_sensor: True if cross-sensor correlation was confirmed.
        primary_event_id: Optional ID of target primary event.
        correlation_group_id: Optional correlation group ID.
        evidence_summary: Tuple of human-readable explainable evidence statements.
    """
    category: EvidenceCategory
    is_anomalous: bool
    is_persistent: bool
    is_cross_sensor: bool
    primary_event_id: Optional[Any]
    correlation_group_id: Optional[str]
    evidence_summary: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "category": self.category.value,
            "is_anomalous": self.is_anomalous,
            "is_persistent": self.is_persistent,
            "is_cross_sensor": self.is_cross_sensor,
            "primary_event_id": self.primary_event_id,
            "correlation_group_id": self.correlation_group_id,
            "evidence_summary": list(self.evidence_summary),
        }
