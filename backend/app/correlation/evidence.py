"""Pure module for aggregating individual anomaly, temporal persistence, and sensor correlation evidence."""

from typing import Any, List, Optional, Sequence

from app.correlation.types import (
    AggregatedEvidenceResult,
    CorrelatedEventGroup,
    EvidenceCategory,
    TemporalPersistenceResult,
)


def aggregate_event_evidence(
    is_anomalous: bool,
    persistence_result: TemporalPersistenceResult,
    correlation_group: Optional[CorrelatedEventGroup] = None,
    primary_event_id: Optional[Any] = None,
    anomaly_reasons: Optional[Sequence[str]] = None,
) -> AggregatedEvidenceResult:
    """
    Combine individual anomaly status, temporal persistence, and sensor correlation into unified evidence.

    Note:
        - Aggregated evidence informs higher-level structural health observation.
        - This output represents evidence accumulation, NOT a severity rating or structural safety score.

    Args:
        is_anomalous: True if primary event was flagged as anomalous.
        persistence_result: TemporalPersistenceResult from persistence evaluation.
        correlation_group: Optional CorrelatedEventGroup from 2-PZT sensor correlation.
        primary_event_id: Optional ID of primary target event.
        anomaly_reasons: Optional reasons from individual anomaly analysis.

    Returns:
        AggregatedEvidenceResult containing category classification and explainable evidence summary.
    """
    is_persistent = persistence_result.is_persistent if persistence_result else False
    is_cross_sensor = correlation_group.is_cross_sensor if correlation_group is not None else False

    if not is_anomalous:
        category = EvidenceCategory.NORMAL_OBSERVATION
    else:
        if is_persistent and is_cross_sensor:
            category = EvidenceCategory.PERSISTENT_AND_CROSS_SENSOR_CORRELATED
        elif is_persistent and not is_cross_sensor:
            category = EvidenceCategory.PERSISTENT_ANOMALY
        elif not is_persistent and is_cross_sensor:
            category = EvidenceCategory.CROSS_SENSOR_CORRELATED
        else:
            category = EvidenceCategory.INDIVIDUAL_ANOMALY

    summary: List[str] = []
    if anomaly_reasons:
        summary.extend(anomaly_reasons)

    if persistence_result and persistence_result.reasons:
        summary.extend(persistence_result.reasons)

    if correlation_group:
        summary.append(correlation_group.relative_source_hint)

    corr_group_id = correlation_group.group_id if correlation_group else None

    return AggregatedEvidenceResult(
        category=category,
        is_anomalous=is_anomalous,
        is_persistent=is_persistent,
        is_cross_sensor=is_cross_sensor,
        primary_event_id=primary_event_id,
        correlation_group_id=corr_group_id,
        evidence_summary=tuple(summary),
    )
