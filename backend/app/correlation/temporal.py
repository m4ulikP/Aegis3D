"""Pure hardware-agnostic temporal persistence calculation module."""

from datetime import datetime, timezone
from typing import Any, List, Sequence, Tuple, Union

from app.correlation.exceptions import InvalidWindowError
from app.correlation.types import (
    DEFAULT_MIN_ANOMALY_COUNT,
    DEFAULT_MIN_ANOMALY_RATIO,
    DEFAULT_PERSISTENCE_WINDOW_SECONDS,
    TemporalPersistenceResult,
)


def _extract_event_info(item: Any) -> Tuple[datetime, bool]:
    """Extract (timestamp, is_anomalous) tuple from an Event, dict, or result object."""
    ts = getattr(item, "timestamp", None)
    if ts is None and isinstance(item, dict):
        ts = item.get("timestamp")

    if ts is None:
        raise ValueError(f"Event item missing 'timestamp' attribute: {item}")

    # Ensure tz-aware datetime for comparison
    if isinstance(ts, datetime) and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    is_anom = getattr(item, "is_anomalous", None)
    if is_anom is None and isinstance(item, dict):
        is_anom = item.get("is_anomalous")
    if is_anom is None and hasattr(item, "magnitude_anomalous"):
        is_anom = getattr(item, "magnitude_anomalous") or getattr(item, "energy_anomalous", False)
    if is_anom is None:
        is_anom = True  # Default if item passed is an anomaly result or event flagged as anomaly

    return ts, bool(is_anom)


def evaluate_temporal_persistence(
    events: Sequence[Any],
    window_duration_seconds: float = DEFAULT_PERSISTENCE_WINDOW_SECONDS,
    min_anomaly_count: int = DEFAULT_MIN_ANOMALY_COUNT,
    min_anomaly_ratio: float = DEFAULT_MIN_ANOMALY_RATIO,
    reference_time: Union[datetime, None] = None,
) -> TemporalPersistenceResult:
    """
    Evaluate a sequence of event anomaly results within a configurable temporal window.

    Note:
        - Temporal persistence provides evidence of repeated anomalous activity over time.
        - Temporal persistence is an evidence accumulation metric, NOT proof of structural damage.

    Args:
        events: Sequence of objects or dicts representing events. Must contain timestamp and anomaly status.
        window_duration_seconds: Duration of temporal observation window in seconds (default 300.0).
        min_anomaly_count: Minimum anomalous event count to trigger persistence (default 3).
        min_anomaly_ratio: Minimum ratio of anomalous events to total events (default 0.5).
        reference_time: Optional reference end time for window calculation. Defaults to latest event timestamp.

    Returns:
        TemporalPersistenceResult dataclass containing persistence metrics and explainable evidence.

    Raises:
        InvalidWindowError: If window_duration_seconds <= 0.
        ValueError: If min_anomaly_count < 1 or min_anomaly_ratio not in [0.0, 1.0].
    """
    if window_duration_seconds <= 0:
        raise InvalidWindowError(f"Observation window duration must be positive, got {window_duration_seconds}")

    if min_anomaly_count < 1:
        raise ValueError(f"min_anomaly_count must be at least 1, got {min_anomaly_count}")

    if min_anomaly_ratio < 0.0 or min_anomaly_ratio > 1.0:
        raise ValueError(f"min_anomaly_ratio must be between 0.0 and 1.0, got {min_anomaly_ratio}")

    if not events:
        return TemporalPersistenceResult(
            is_persistent=False,
            total_events=0,
            anomalous_events=0,
            anomaly_ratio=0.0,
            max_consecutive_anomalies=0,
            time_span_seconds=0.0,
            window_duration_seconds=window_duration_seconds,
            min_anomaly_count_used=min_anomaly_count,
            min_anomaly_ratio_used=min_anomaly_ratio,
            reasons=("No events present in temporal observation window",),
        )

    # Extract tuples and sort by timestamp
    event_tuples = [_extract_event_info(item) for item in events]
    event_tuples.sort(key=lambda x: x[0])

    if reference_time is not None:
        ref_t = reference_time
        if ref_t.tzinfo is None:
            ref_t = ref_t.replace(tzinfo=timezone.utc)
    else:
        ref_t = event_tuples[-1][0]

    window_start = ref_t.timestamp() - window_duration_seconds
    window_end = ref_t.timestamp()

    # Filter events within window [ref_t - window_duration_seconds, ref_t]
    filtered = [
        (ts, is_anom) for ts, is_anom in event_tuples if window_start <= ts.timestamp() <= window_end
    ]

    total_events = len(filtered)
    if total_events == 0:
        return TemporalPersistenceResult(
            is_persistent=False,
            total_events=0,
            anomalous_events=0,
            anomaly_ratio=0.0,
            max_consecutive_anomalies=0,
            time_span_seconds=0.0,
            window_duration_seconds=window_duration_seconds,
            min_anomaly_count_used=min_anomaly_count,
            min_anomaly_ratio_used=min_anomaly_ratio,
            reasons=("No events present within the specified temporal window boundary",),
        )

    anomalous_events = sum(1 for _, is_anom in filtered if is_anom)
    anomaly_ratio = float(anomalous_events / total_events)

    max_consecutive = 0
    current_consecutive = 0
    for _, is_anom in filtered:
        if is_anom:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0

    time_span_seconds = float((filtered[-1][0] - filtered[0][0]).total_seconds())

    is_persistent = (anomalous_events >= min_anomaly_count) and (anomaly_ratio >= min_anomaly_ratio)

    reasons: List[str] = []
    if is_persistent:
        reasons.append(
            f"Temporal persistence confirmed: {anomalous_events} anomalous events out of {total_events} total "
            f"in {window_duration_seconds:.0f}s window (ratio: {anomaly_ratio:.2f} >= {min_anomaly_ratio:.2f}, "
            f"max consecutive: {max_consecutive})"
        )
    else:
        reasons.append(
            f"No temporal persistence: {anomalous_events} anomalous events out of {total_events} total "
            f"in {window_duration_seconds:.0f}s window (requires >= {min_anomaly_count} anomalies and ratio >= {min_anomaly_ratio:.2f})"
        )

    return TemporalPersistenceResult(
        is_persistent=is_persistent,
        total_events=total_events,
        anomalous_events=anomalous_events,
        anomaly_ratio=anomaly_ratio,
        max_consecutive_anomalies=max_consecutive,
        time_span_seconds=time_span_seconds,
        window_duration_seconds=window_duration_seconds,
        min_anomaly_count_used=min_anomaly_count,
        min_anomaly_ratio_used=min_anomaly_ratio,
        reasons=tuple(reasons),
    )
