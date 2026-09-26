"""Pure hardware-agnostic trend analysis calculation engine."""

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, Tuple, Union

from app.trend.exceptions import InvalidTrendConfigError
from app.trend.types import (
    DEFAULT_MAGNITUDE_DELTA_THRESHOLD,
    DEFAULT_MIN_EVENTS_PER_PERIOD,
    DEFAULT_TREND_DELTA_THRESHOLD,
    DEFAULT_TREND_WINDOW_SECONDS,
    PeriodMetrics,
    TrendDirection,
    ZoneTrendResult,
)


def _extract_event_metrics(item: Any) -> Tuple[datetime, Optional[int], bool, Optional[float], bool, bool]:
    """
    Extract standardized event metrics tuple from an Event, dict, or result object.

    Returns:
        (timestamp, zone_id, is_anomalous, magnitude, is_persistent, is_cross_sensor)
    """
    ts = getattr(item, "timestamp", None)
    if ts is None and isinstance(item, dict):
        ts = item.get("timestamp")

    if ts is None:
        raise ValueError(f"Event item missing 'timestamp' attribute: {item}")

    if isinstance(ts, datetime) and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    zone_id = getattr(item, "zone_id", None)
    if zone_id is None and isinstance(item, dict):
        zone_id = item.get("zone_id")

    is_anom = getattr(item, "is_anomalous", None)
    if is_anom is None and isinstance(item, dict):
        is_anom = item.get("is_anomalous")
    if is_anom is None and hasattr(item, "magnitude_anomalous"):
        is_anom = getattr(item, "magnitude_anomalous") or getattr(item, "energy_anomalous", False)
    if is_anom is None:
        is_anom = True

    mag = getattr(item, "magnitude", None)
    if mag is None and isinstance(item, dict):
        mag = item.get("magnitude")
    if mag is None and hasattr(item, "max_z_score"):
        mag = getattr(item, "max_z_score")

    is_pers = getattr(item, "is_persistent", None)
    if is_pers is None and isinstance(item, dict):
        is_pers = item.get("is_persistent")

    is_cross = getattr(item, "is_cross_sensor", None)
    if is_cross is None and isinstance(item, dict):
        is_cross = item.get("is_cross_sensor")

    category = getattr(item, "category", None)
    if category is None and isinstance(item, dict):
        category = item.get("category")
    if category is not None:
        cat_str = str(getattr(category, "value", category))
        if cat_str in ("PERSISTENT_ANOMALY", "PERSISTENT_AND_CROSS_SENSOR_CORRELATED"):
            is_pers = True
        if cat_str in ("CROSS_SENSOR_CORRELATED", "PERSISTENT_AND_CROSS_SENSOR_CORRELATED"):
            is_cross = True

    return (
        ts,
        zone_id,
        bool(is_anom),
        float(mag) if mag is not None else None,
        bool(is_pers) if is_pers is not None else False,
        bool(is_cross) if is_cross is not None else False,
    )


def evaluate_zone_trend(
    events: Sequence[Any],
    analysis_window_seconds: float = DEFAULT_TREND_WINDOW_SECONDS,
    trend_delta_threshold: float = DEFAULT_TREND_DELTA_THRESHOLD,
    min_events_per_period: int = DEFAULT_MIN_EVENTS_PER_PERIOD,
    magnitude_delta_threshold: float = DEFAULT_MAGNITUDE_DELTA_THRESHOLD,
    reference_time: Union[datetime, None] = None,
    target_zone_id: Optional[int] = None,
) -> ZoneTrendResult:
    """
    Evaluate deterministic zone trend by comparing two contiguous sub-periods across an observation window.

    Note:
        - Step 9 trend analysis identifies observational changes in anomaly frequency/magnitude over time.
        - Trend classification does NOT diagnose structural damage or calculate a Structural Health Indicator (SHI).

    Args:
        events: Sequence of event objects, dicts, or analysis result instances.
        analysis_window_seconds: Total time window duration in seconds (default 3600.0).
        trend_delta_threshold: Minimum anomaly rate delta (later - earlier) to classify trend direction (default 0.10).
        min_events_per_period: Minimum events required per sub-period for statistical comparison (default 2).
        magnitude_delta_threshold: Minimum magnitude delta to trigger magnitude trend direction (default 0.5).
        reference_time: Optional end timestamp for observation window. Defaults to latest event or current UTC time.
        target_zone_id: Optional zone filter to restrict trend evaluation to a specific zone.

    Returns:
        ZoneTrendResult dataclass containing sub-period metrics, trend deltas, and explainable reasons.

    Raises:
        InvalidTrendConfigError: If configuration parameters are invalid.
    """
    if analysis_window_seconds <= 0:
        raise InvalidTrendConfigError(
            f"analysis_window_seconds must be positive, got {analysis_window_seconds}"
        )

    if trend_delta_threshold < 0.0 or trend_delta_threshold > 1.0:
        raise InvalidTrendConfigError(
            f"trend_delta_threshold must be between 0.0 and 1.0, got {trend_delta_threshold}"
        )

    if min_events_per_period < 1:
        raise InvalidTrendConfigError(
            f"min_events_per_period must be at least 1, got {min_events_per_period}"
        )

    if magnitude_delta_threshold < 0.0:
        raise InvalidTrendConfigError(
            f"magnitude_delta_threshold must be non-negative, got {magnitude_delta_threshold}"
        )

    # Extract event metrics tuples
    raw_extracted = [_extract_event_metrics(item) for item in events]

    # Filter by target_zone_id if provided
    if target_zone_id is not None:
        extracted = [item for item in raw_extracted if item[1] is None or item[1] == target_zone_id]
    else:
        extracted = raw_extracted

    extracted.sort(key=lambda x: x[0])

    if reference_time is not None:
        ref_t = reference_time
        if ref_t.tzinfo is None:
            ref_t = ref_t.replace(tzinfo=timezone.utc)
    elif extracted:
        ref_t = extracted[-1][0]
    else:
        ref_t = datetime.now(timezone.utc)

    window_end = ref_t
    window_start = ref_t - timedelta(seconds=analysis_window_seconds)
    half_duration = analysis_window_seconds / 2.0
    midpoint = window_start + timedelta(seconds=half_duration)

    # Filter events within window boundary [window_start, window_end]
    in_window = [
        item for item in extracted if window_start <= item[0] <= window_end
    ]

    # Split into earlier sub-period [window_start, midpoint) and later sub-period [midpoint, window_end]
    earlier_events = [item for item in in_window if window_start <= item[0] < midpoint]
    later_events = [item for item in in_window if midpoint <= item[0] <= window_end]

    earlier_metrics = _build_period_metrics(window_start, midpoint, earlier_events)
    later_metrics = _build_period_metrics(midpoint, window_end, later_events)

    earlier_total = earlier_metrics.total_events
    later_total = later_metrics.total_events

    # Check for INSUFFICIENT_DATA condition
    if earlier_total < min_events_per_period or later_total < min_events_per_period:
        reasons: List[str] = []
        if not in_window:
            reasons.append("No event observations available within the analysis window")
        else:
            reasons.append(
                f"Insufficient event observations for trend evaluation: earlier period has {earlier_total} event(s), "
                f"later period has {later_total} event(s) (minimum required per period: {min_events_per_period})"
            )

        return ZoneTrendResult(
            zone_id=target_zone_id,
            analysis_window_seconds=analysis_window_seconds,
            earlier_period=earlier_metrics,
            later_period=later_metrics,
            anomaly_rate_delta=0.0,
            rate_trend_direction=TrendDirection.INSUFFICIENT_DATA,
            magnitude_delta=None,
            magnitude_trend_direction=TrendDirection.INSUFFICIENT_DATA,
            persistent_count_delta=later_metrics.persistent_anomaly_count - earlier_metrics.persistent_anomaly_count,
            cross_sensor_count_delta=later_metrics.cross_sensor_event_count - earlier_metrics.cross_sensor_event_count,
            overall_trend_direction=TrendDirection.INSUFFICIENT_DATA,
            trend_delta_threshold_used=trend_delta_threshold,
            min_events_per_period_used=min_events_per_period,
            reasons=tuple(reasons),
        )

    # Sufficient data for deterministic trend analysis
    anomaly_rate_delta = round(later_metrics.anomaly_rate - earlier_metrics.anomaly_rate, 6)

    # Anomaly rate trend direction
    if anomaly_rate_delta >= trend_delta_threshold:
        rate_trend = TrendDirection.INCREASING
    elif anomaly_rate_delta <= -trend_delta_threshold:
        rate_trend = TrendDirection.DECREASING
    else:
        rate_trend = TrendDirection.STABLE

    # Magnitude delta and trend direction
    if earlier_metrics.mean_magnitude is not None and later_metrics.mean_magnitude is not None:
        mag_delta: Optional[float] = round(later_metrics.mean_magnitude - earlier_metrics.mean_magnitude, 6)
        if mag_delta >= magnitude_delta_threshold:
            mag_trend = TrendDirection.INCREASING
        elif mag_delta <= -magnitude_delta_threshold:
            mag_trend = TrendDirection.DECREASING
        else:
            mag_trend = TrendDirection.STABLE
    else:
        mag_delta = None
        mag_trend = TrendDirection.STABLE

    persistent_delta = later_metrics.persistent_anomaly_count - earlier_metrics.persistent_anomaly_count
    cross_sensor_delta = later_metrics.cross_sensor_event_count - earlier_metrics.cross_sensor_event_count

    # Deterministic overall trend calculation
    if rate_trend == TrendDirection.INCREASING:
        overall_trend = TrendDirection.INCREASING
    elif rate_trend == TrendDirection.DECREASING:
        overall_trend = TrendDirection.DECREASING
    else:
        # Rate is STABLE: check component secondary evidence (magnitude or Step 8 persistent/cross-sensor counts)
        if mag_trend == TrendDirection.INCREASING or persistent_delta > 0 or cross_sensor_delta > 0:
            overall_trend = TrendDirection.INCREASING
        elif mag_trend == TrendDirection.DECREASING:
            overall_trend = TrendDirection.DECREASING
        else:
            overall_trend = TrendDirection.STABLE

    # Formulate safety-compliant, explainable reasons
    reasons_list: List[str] = []

    rate_pct_change = anomaly_rate_delta * 100.0
    reasons_list.append(
        f"Zone trend evaluated as {overall_trend.value}: earlier anomaly rate {earlier_metrics.anomaly_rate:.2f} "
        f"({earlier_metrics.anomalous_events}/{earlier_total}) vs later anomaly rate {later_metrics.anomaly_rate:.2f} "
        f"({later_metrics.anomalous_events}/{later_total}) -> delta: {anomaly_rate_delta:+.2f} ({rate_pct_change:+.1f}%)"
    )

    if rate_trend != TrendDirection.STABLE:
        reasons_list.append(
            f"Anomaly rate change ({anomaly_rate_delta:+.2f}) exceeds configured trend threshold ({trend_delta_threshold:.2f})"
        )

    if mag_delta is not None:
        reasons_list.append(
            f"Mean anomaly magnitude changed from {earlier_metrics.mean_magnitude:.2f} to {later_metrics.mean_magnitude:.2f} "
            f"(delta: {mag_delta:+.2f}, magnitude trend: {mag_trend.value})"
        )

    # Document divergent/conflicting component trends if present
    if rate_trend == TrendDirection.INCREASING and mag_trend == TrendDirection.DECREASING:
        reasons_list.append(
            f"Divergent trend components: anomaly rate is INCREASING ({anomaly_rate_delta:+.2f}) while mean magnitude is DECREASING ({mag_delta:+.2f}). "
            "Overall trend follows anomaly rate change."
        )
    elif rate_trend == TrendDirection.DECREASING and mag_trend == TrendDirection.INCREASING:
        reasons_list.append(
            f"Divergent trend components: anomaly rate is DECREASING ({anomaly_rate_delta:+.2f}) while mean magnitude is INCREASING ({mag_delta:+.2f}). "
            "Overall trend follows anomaly rate change."
        )

    if persistent_delta != 0 or cross_sensor_delta != 0:
        reasons_list.append(
            f"Step 8 evidence changes: persistent anomaly delta = {persistent_delta:+d}, "
            f"cross-sensor correlated event delta = {cross_sensor_delta:+d}"
        )

    if overall_trend == TrendDirection.INCREASING:
        reasons_list.append("Observed abnormal event activity is becoming more frequent; continued monitoring or structural inspection advised.")
    elif overall_trend == TrendDirection.DECREASING:
        reasons_list.append("Observed abnormal event activity is declining toward baseline levels.")
    else:
        reasons_list.append("Observed event activity remains stable over the analysis window.")

    return ZoneTrendResult(
        zone_id=target_zone_id,
        analysis_window_seconds=analysis_window_seconds,
        earlier_period=earlier_metrics,
        later_period=later_metrics,
        anomaly_rate_delta=anomaly_rate_delta,
        rate_trend_direction=rate_trend,
        magnitude_delta=mag_delta,
        magnitude_trend_direction=mag_trend,
        persistent_count_delta=persistent_delta,
        cross_sensor_count_delta=cross_sensor_delta,
        overall_trend_direction=overall_trend,
        trend_delta_threshold_used=trend_delta_threshold,
        min_events_per_period_used=min_events_per_period,
        reasons=tuple(reasons_list),
    )


def _build_period_metrics(start_t: datetime, end_t: datetime, items: Sequence[Tuple[datetime, Optional[int], bool, Optional[float], bool, bool]]) -> PeriodMetrics:
    """Helper to construct PeriodMetrics for a sub-period."""
    total = len(items)
    if total == 0:
        return PeriodMetrics(
            start_time=start_t,
            end_time=end_t,
            total_events=0,
            anomalous_events=0,
            anomaly_rate=0.0,
            mean_magnitude=None,
            persistent_anomaly_count=0,
            cross_sensor_event_count=0,
        )

    anomalous = sum(1 for item in items if item[2])
    rate = float(anomalous / total)

    mags = [item[3] for item in items if item[3] is not None]
    mean_mag = float(sum(mags) / len(mags)) if mags else None

    pers_count = sum(1 for item in items if item[4])
    cross_count = sum(1 for item in items if item[5])

    return PeriodMetrics(
        start_time=start_t,
        end_time=end_t,
        total_events=total,
        anomalous_events=anomalous,
        anomaly_rate=rate,
        mean_magnitude=mean_mag,
        persistent_anomaly_count=pers_count,
        cross_sensor_event_count=cross_count,
    )
