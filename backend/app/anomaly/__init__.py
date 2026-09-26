"""Rule-based statistical anomaly detection package."""

from app.anomaly.calculator import (
    DEFAULT_ANOMALY_Z_THRESHOLD,
    analyze_event,
    analyze_event_against_baseline,
    calculate_z_score,
)
from app.anomaly.exceptions import (
    AnomalyError,
    BaselineNotFoundError,
    InvalidBaselineError,
    InvalidEventDataError,
    InvalidThresholdError,
)
from app.anomaly.types import AnomalyAnalysisResult

__all__ = [
    "DEFAULT_ANOMALY_Z_THRESHOLD",
    "AnomalyAnalysisResult",
    "calculate_z_score",
    "analyze_event_against_baseline",
    "analyze_event",
    "AnomalyError",
    "InvalidEventDataError",
    "InvalidBaselineError",
    "InvalidThresholdError",
    "BaselineNotFoundError",
]
