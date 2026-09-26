"""
Aegis3D Step 9: Deterministic Zone Trend Analysis Module.

Provides pure hardware-agnostic functions and data types to evaluate whether zone anomaly behavior
is increasing, decreasing, or remaining stable over time.
"""

from app.trend.evaluator import evaluate_zone_trend
from app.trend.exceptions import (
    InsufficientTrendDataError,
    InvalidTrendConfigError,
    TrendError,
)
from app.trend.types import (
    DEFAULT_MAGNITUDE_DELTA_THRESHOLD,
    DEFAULT_MIN_EVENTS_PER_PERIOD,
    DEFAULT_TREND_DELTA_THRESHOLD,
    DEFAULT_TREND_WINDOW_SECONDS,
    PeriodMetrics,
    TrendDirection,
    ZoneTrendResult,
)

__all__ = [
    "evaluate_zone_trend",
    "TrendDirection",
    "PeriodMetrics",
    "ZoneTrendResult",
    "TrendError",
    "InvalidTrendConfigError",
    "InsufficientTrendDataError",
    "DEFAULT_TREND_WINDOW_SECONDS",
    "DEFAULT_TREND_DELTA_THRESHOLD",
    "DEFAULT_MIN_EVENTS_PER_PERIOD",
    "DEFAULT_MAGNITUDE_DELTA_THRESHOLD",
]
