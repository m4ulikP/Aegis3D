"""Pure hardware-agnostic two-PZT sensor event correlation module."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.correlation.exceptions import InvalidToleranceError
from app.correlation.types import DEFAULT_CORRELATION_TOLERANCE_SECONDS, CorrelatedEventGroup


def _extract_event_details(item: Any, idx: int) -> Tuple[Any, datetime, str, int]:
    """
    Extract (event_id, timestamp, source_id, zone_id) from an Event object, dict, or dataclass.
    """
    evt_id = getattr(item, "id", None)
    if evt_id is None and isinstance(item, dict):
        evt_id = item.get("id")
    if evt_id is None:
        evt_id = idx  # Fallback to index if no ID attribute exists

    ts = getattr(item, "timestamp", None)
    if ts is None and isinstance(item, dict):
        ts = item.get("timestamp")
    if ts is None:
        raise ValueError(f"Event item at index {idx} missing 'timestamp' attribute")
    if isinstance(ts, datetime) and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    src = getattr(item, "source_id", None)
    if src is None and isinstance(item, dict):
        src = item.get("source_id")
    if src is None:
        src = "UNKNOWN_SENSOR"

    zone = getattr(item, "zone_id", None)
    if zone is None and isinstance(item, dict):
        zone = item.get("zone_id")
    if zone is None:
        zone = 1  # Default fallback zone

    return evt_id, ts, str(src), int(zone)


def correlate_two_pzt_events(
    events: Sequence[Any],
    tolerance_seconds: float = DEFAULT_CORRELATION_TOLERANCE_SECONDS,
    target_zone_id: Optional[int] = None,
) -> List[CorrelatedEventGroup]:
    """
    Group events across sensors within a configurable temporal tolerance window.

    Note:
        - Aegis3D assumes two PZT sensing channels per monitored zone.
        - Cross-sensor event correlation indicates relative source arrival times, NOT 3D spatial localization.
        - Events from different zones are strictly separated and never correlated together.

    Args:
        events: Sequence of event objects or dicts.
        tolerance_seconds: Maximum time window to group events across sensors (default 0.025s / 25ms).
        target_zone_id: Optional zone ID filter. If provided, only events for target_zone_id are correlated.

    Returns:
        List of CorrelatedEventGroup objects representing correlated or single-sensor event groups.

    Raises:
        InvalidToleranceError: If tolerance_seconds <= 0.
    """
    if tolerance_seconds <= 0:
        raise InvalidToleranceError(f"Correlation tolerance_seconds must be positive, got {tolerance_seconds}")

    if not events:
        return []

    # Extract event tuples
    extracted = [_extract_event_details(item, idx) for idx, item in enumerate(events)]

    # Filter by target_zone_id if provided
    if target_zone_id is not None:
        extracted = [item for item in extracted if item[3] == target_zone_id]

    if not extracted:
        return []

    # Group extracted events by zone_id first to ensure zones are never cross-correlated
    by_zone: Dict[int, List[Tuple[Any, datetime, str, int]]] = {}
    for item in extracted:
        by_zone.setdefault(item[3], []).append(item)

    results: List[CorrelatedEventGroup] = []

    for zone_id, zone_events in by_zone.items():
        # Sort by timestamp ascending
        zone_events.sort(key=lambda x: x[1])

        # Cluster into temporal tolerance windows
        clusters: List[List[Tuple[Any, datetime, str, int]]] = []
        current_cluster: List[Tuple[Any, datetime, str, int]] = []
        cluster_start_ts: Optional[float] = None

        for item in zone_events:
            evt_ts = item[1].timestamp()
            if not current_cluster:
                current_cluster.append(item)
                cluster_start_ts = evt_ts
            else:
                assert cluster_start_ts is not None
                if evt_ts - cluster_start_ts <= tolerance_seconds:
                    current_cluster.append(item)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [item]
                    cluster_start_ts = evt_ts

        if current_cluster:
            clusters.append(current_cluster)

        # Build CorrelatedEventGroup for each cluster
        for cluster in clusters:
            start_t = cluster[0][1]
            end_t = cluster[-1][1]
            event_ids = tuple(c[0] for c in cluster)
            sensors = tuple(sorted(list(set(c[2] for c in cluster))))
            sensor_count = len(sensors)
            is_cross_sensor = sensor_count >= 2
            temporal_spread_ms = float((end_t - start_t).total_seconds() * 1000.0)

            start_ms = int(start_t.timestamp() * 1000)
            group_id = f"CORR-Z{zone_id}-{start_ms}-{sensor_count}"

            if is_cross_sensor:
                sensor_str = ", ".join(sensors)
                hint = (
                    f"Two-sensor event correlation confirmed across sensors ({sensor_str}) "
                    f"(spread: {temporal_spread_ms:.1f}ms) - relative source indication active"
                )
            else:
                sensor_name = sensors[0] if sensors else "PZT-01"
                hint = (
                    f"Single-sensor event observation ({sensor_name}) - "
                    f"no cross-sensor correlation within {tolerance_seconds * 1000.0:.1f}ms"
                )

            results.append(
                CorrelatedEventGroup(
                    group_id=group_id,
                    zone_id=zone_id,
                    participating_sensors=sensors,
                    event_ids=event_ids,
                    start_timestamp=start_t,
                    end_timestamp=end_t,
                    event_count=len(cluster),
                    sensor_count=sensor_count,
                    is_cross_sensor=is_cross_sensor,
                    temporal_spread_ms=temporal_spread_ms,
                    relative_source_hint=hint,
                )
            )

    return results
