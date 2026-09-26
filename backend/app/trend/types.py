"""Data types and result representations for deterministic zone trend analysis."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

# PROTOTYPE CONFIGURATION PARAMETERS
# Note: These values are configurable engineering defaults for prototype testing,
# NOT scientifically validated structural safety or structural dynamics thresholds.
DEFAULT_TREND_WINDOW_SECONDS: float = 3600.0  # 1-hour total observation window (2x 30-min comparison periods)
DEFAULT_TREND_DELTA_THRESHOLD: float = 0.10   # 10% change in anomaly rate required for directional trend
DEFAULT_MIN_EVENTS_PER_PERIOD: int = 2        # Minimum events required per sub-period for statistical comparison
DEFAULT_MAGNITUDE_DELTA_THRESHOLD: float = 0.5 # Change in mean anomaly magnitude or z-score needed for magnitude trend


class TrendDirection(str, Enum):
    """Directional trend classification for monitored structural zone behavior."""
    STABLE = "STABLE"
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class PeriodMetrics:
    """
    Summary metrics for a single observation sub-period (earlier or later).

    Attributes:
        start_time: Start timestamp of the sub-period.
        end_time: End timestamp of the sub-period.
        total_events: Total event observations in the sub-period.
        anomalous_events: Count of anomalous events in the sub-period.
        anomaly_rate: Proportion of anomalous events to total events (0.0 to 1.0).
        mean_magnitude: Average magnitude/z-score of events in sub-period (None if no events).
        persistent_anomaly_count: Count of events exhibiting temporal persistence (Step 8 evidence).
        cross_sensor_event_count: Count of events exhibiting cross-sensor correlation (Step 8 evidence).
    """
    start_time: datetime
    end_time: datetime
    total_events: int
    anomalous_events: int
    anomaly_rate: float
    mean_magnitude: Optional[float]
    persistent_anomaly_count: int
    cross_sensor_event_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert sub-period metrics to dictionary representation."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_events": self.total_events,
            "anomalous_events": self.anomalous_events,
            "anomaly_rate": round(self.anomaly_rate, 4),
            "mean_magnitude": round(self.mean_magnitude, 4) if self.mean_magnitude is not None else None,
            "persistent_anomaly_count": self.persistent_anomaly_count,
            "cross_sensor_event_count": self.cross_sensor_event_count,
        }


@dataclass(frozen=True)
class ZoneTrendResult:
    """
    Pure numerical result of deterministic trend analysis comparing two contiguous time periods.

    Note:
        - Trend analysis identifies statistical/observational trends over time.
        - This output does NOT diagnose structural damage, produce a health index (SHI), or issue alerts.

    Attributes:
        zone_id: Optional zone identifier under analysis.
        analysis_window_seconds: Total time duration under analysis.
        earlier_period: Metrics for the earlier sub-period.
        later_period: Metrics for the later sub-period.
        anomaly_rate_delta: Difference in anomaly rate (later - earlier).
        rate_trend_direction: Directional trend based on anomaly rate change.
        magnitude_delta: Difference in mean magnitude (later - earlier), or None.
        magnitude_trend_direction: Directional trend based on magnitude change.
        persistent_count_delta: Difference in persistent anomaly count.
        cross_sensor_count_delta: Difference in cross-sensor correlated event count.
        overall_trend_direction: Combined deterministic overall trend direction.
        trend_delta_threshold_used: Minimum anomaly rate change threshold configured.
        min_events_per_period_used: Minimum events per sub-period threshold configured.
        reasons: Tuple of explainable, observational rationale statements.
    """
    zone_id: Optional[int]
    analysis_window_seconds: float
    earlier_period: PeriodMetrics
    later_period: PeriodMetrics
    anomaly_rate_delta: float
    rate_trend_direction: TrendDirection
    magnitude_delta: Optional[float]
    magnitude_trend_direction: TrendDirection
    persistent_count_delta: int
    cross_sensor_count_delta: int
    overall_trend_direction: TrendDirection
    trend_delta_threshold_used: float
    min_events_per_period_used: int
    reasons: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Convert trend result to dictionary representation."""
        return {
            "zone_id": self.zone_id,
            "analysis_window_seconds": self.analysis_window_seconds,
            "earlier_period": self.earlier_period.to_dict(),
            "later_period": self.later_period.to_dict(),
            "anomaly_rate_delta": round(self.anomaly_rate_delta, 4),
            "rate_trend_direction": self.rate_trend_direction.value,
            "magnitude_delta": round(self.magnitude_delta, 4) if self.magnitude_delta is not None else None,
            "magnitude_trend_direction": self.magnitude_trend_direction.value,
            "persistent_count_delta": self.persistent_count_delta,
            "cross_sensor_count_delta": self.cross_sensor_count_delta,
            "overall_trend_direction": self.overall_trend_direction.value,
            "trend_delta_threshold_used": self.trend_delta_threshold_used,
            "min_events_per_period_used": self.min_events_per_period_used,
            "reasons": list(self.reasons),
        }
