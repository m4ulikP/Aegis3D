"""Temporal persistence, 2-PZT event correlation, and aggregated evidence package."""

from app.correlation.evidence import aggregate_event_evidence
from app.correlation.exceptions import (
    InvalidToleranceError,
    InvalidWindowError,
    TemporalCorrelationError,
)
from app.correlation.sensor_correlation import correlate_two_pzt_events
from app.correlation.temporal import evaluate_temporal_persistence
from app.correlation.types import (
    DEFAULT_CORRELATION_TOLERANCE_SECONDS,
    DEFAULT_MIN_ANOMALY_COUNT,
    DEFAULT_MIN_ANOMALY_RATIO,
    DEFAULT_PERSISTENCE_WINDOW_SECONDS,
    AggregatedEvidenceResult,
    CorrelatedEventGroup,
    EvidenceCategory,
    TemporalPersistenceResult,
)

__all__ = [
    "DEFAULT_PERSISTENCE_WINDOW_SECONDS",
    "DEFAULT_MIN_ANOMALY_COUNT",
    "DEFAULT_MIN_ANOMALY_RATIO",
    "DEFAULT_CORRELATION_TOLERANCE_SECONDS",
    "EvidenceCategory",
    "TemporalPersistenceResult",
    "CorrelatedEventGroup",
    "AggregatedEvidenceResult",
    "evaluate_temporal_persistence",
    "correlate_two_pzt_events",
    "aggregate_event_evidence",
    "TemporalCorrelationError",
    "InvalidWindowError",
    "InvalidToleranceError",
]
