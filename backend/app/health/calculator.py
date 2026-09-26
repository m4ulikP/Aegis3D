"""Pure hardware-agnostic Structural Health Indicator (SHI) calculation engine."""

from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple, Union

from app.health.types import (
    SHI_PROTOTYPE_DISCLAIMER,
    SHIConfig,
    SHIDeductions,
    StructuralHealthResult,
)
from app.models.enums import HealthStatus


def calculate_structural_health_indicator(
    is_anomalous: bool = False,
    is_persistent: bool = False,
    is_cross_sensor: bool = False,
    trend: Union[str, Any] = "STABLE",
    anomalous_event_count: int = 0,
    total_event_count: int = 0,
    zone_id: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    config: Optional[SHIConfig] = None,
    evidence_category: Optional[str] = None,
) -> StructuralHealthResult:
    """
    Calculate pure deterministic Structural Health Indicator (SHI) from multi-step monitoring evidence.

    Note:
        - SHI provides an observational prototype indicator (0-100) summarizing multi-step evidence.
        - SHI does NOT establish structural safety percentages, probability of failure, or certified damage ratings.

    Args:
        is_anomalous: True if anomaly activity is detected (Step 7 evidence).
        is_persistent: True if temporal persistence is confirmed (Step 8 evidence).
        is_cross_sensor: True if 2-PZT cross-sensor correlation is confirmed (Step 8 evidence).
        trend: Trend direction from Step 9 (STABLE, INCREASING, DECREASING, INSUFFICIENT_DATA).
        anomalous_event_count: Count of anomalous events in observation window.
        total_event_count: Total event observations in window.
        zone_id: Optional zone identifier.
        timestamp: Evaluation timestamp. Defaults to UTC now.
        config: Optional custom SHIConfig instance.
        evidence_category: Optional explicit evidence category string from Step 8.

    Returns:
        StructuralHealthResult dataclass containing score, status, itemized deductions, and explainable reasons.

    Raises:
        InvalidHealthConfigError: If config parameters are out of valid bounds.
    """
    cfg = config or SHIConfig()
    cfg.validate()

    eval_time = timestamp or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    # Normalize trend string
    if hasattr(trend, "value"):
        trend_str = str(trend.value).upper()
    else:
        trend_str = str(trend).upper()

    # Determine individual anomaly activity
    has_anomaly_activity = is_anomalous or (anomalous_event_count > 0)
    if evidence_category in ("INDIVIDUAL_ANOMALY", "PERSISTENT_ANOMALY", "CROSS_SENSOR_CORRELATED", "PERSISTENT_AND_CROSS_SENSOR_CORRELATED"):
        has_anomaly_activity = True

    # 1. Anomaly activity penalty
    anomaly_deduction = cfg.anomaly_penalty if has_anomaly_activity else 0.0

    # 2. Temporal persistence penalty
    has_persistence = is_persistent or (evidence_category in ("PERSISTENT_ANOMALY", "PERSISTENT_AND_CROSS_SENSOR_CORRELATED"))
    persistence_deduction = cfg.persistence_penalty if has_persistence else 0.0

    # 3. Cross-sensor correlation penalty
    has_cross_sensor = is_cross_sensor or (evidence_category in ("CROSS_SENSOR_CORRELATED", "PERSISTENT_AND_CROSS_SENSOR_CORRELATED"))
    cross_sensor_deduction = cfg.cross_sensor_penalty if has_cross_sensor else 0.0

    # 4. Increasing trend penalty
    if trend_str == "INCREASING":
        increasing_trend_deduction = cfg.increasing_trend_penalty
    else:
        increasing_trend_deduction = 0.0  # 0 penalty for STABLE, DECREASING, or INSUFFICIENT_DATA

    total_deductions = anomaly_deduction + persistence_deduction + cross_sensor_deduction + increasing_trend_deduction
    deductions_obj = SHIDeductions(
        anomaly_activity_deduction=anomaly_deduction,
        persistence_deduction=persistence_deduction,
        cross_sensor_deduction=cross_sensor_deduction,
        increasing_trend_deduction=increasing_trend_deduction,
        total_deductions=total_deductions,
    )

    # Calculate raw score and clamp strictly between 0.0 and 100.0
    raw_score = cfg.base_score - total_deductions
    score = max(0.0, min(100.0, raw_score))

    # Map score to HealthStatus
    if score >= 90.0:
        status = HealthStatus.NORMAL
    elif score >= 70.0:
        status = HealthStatus.MONITOR
    elif score >= 45.0:
        status = HealthStatus.INSPECTION_ADVISED
    else:
        status = HealthStatus.HIGH_PRIORITY_INSPECTION

    # Generate explainable reasons
    reasons: List[str] = [
        f"Base reference score: {cfg.base_score:.1f}"
    ]

    if has_anomaly_activity:
        reasons.append(f"Individual anomaly activity detected: -{anomaly_deduction:.1f} pts penalty applied")
    else:
        reasons.append("No individual anomaly activity detected (0 pts penalty)")

    if has_persistence:
        reasons.append(f"Step 8 temporal persistence confirmed: -{persistence_deduction:.1f} pts penalty applied")
    else:
        reasons.append("No temporal persistence confirmed (0 pts penalty)")

    if has_cross_sensor:
        reasons.append(f"Step 8 cross-sensor correlation confirmed: -{cross_sensor_deduction:.1f} pts penalty applied")
    else:
        reasons.append("No cross-sensor correlation confirmed (0 pts penalty)")

    if trend_str == "INCREASING":
        reasons.append(f"Step 9 anomaly trend is INCREASING: -{increasing_trend_deduction:.1f} pts penalty applied")
    elif trend_str == "INSUFFICIENT_DATA":
        reasons.append("Step 9 trend status: INSUFFICIENT_DATA (0 pts penalty applied, preserving data uncertainty)")
    elif trend_str == "DECREASING":
        reasons.append("Step 9 anomaly trend is DECREASING (0 pts penalty applied)")
    else:
        reasons.append("Step 9 anomaly trend is STABLE (0 pts penalty applied)")

    reasons.append(
        f"Total deductions: -{total_deductions:.1f} pts -> Calculated SHI score: {score:.1f}/100 -> Status: {status.value}"
    )

    reason_summary = (
        f"Zone SHI evaluated as {score:.1f}/100 ({status.value}) based on accumulated evidence "
        f"(deductions: -{total_deductions:.1f} pts)."
    )

    return StructuralHealthResult(
        zone_id=zone_id,
        timestamp=eval_time,
        score=score,
        status=status,
        trend=trend_str,
        deductions=deductions_obj,
        reason=reason_summary,
        evidence_summary=tuple(reasons),
        disclaimer=SHI_PROTOTYPE_DISCLAIMER,
    )
