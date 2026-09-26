"""Data types and result representations for the deterministic Structural Health Indicator (SHI)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.models.enums import HealthStatus, HealthTrend

# MANDATORY PROTOTYPE DISCLAIMER
SHI_PROTOTYPE_DISCLAIMER: str = (
    "SHI is a prototype evidence-based monitoring indicator derived from observed signal/event behavior. "
    "It is not a certified structural safety score and does not independently establish structural damage or failure."
)

# PROTOTYPE PENALTY DEFAULT PARAMETERS
# Note: These values are configurable prototype parameters for observational testing,
# NOT scientifically validated structural dynamics or engineering safety thresholds.
DEFAULT_BASE_SCORE: float = 100.0
DEFAULT_ANOMALY_PENALTY: float = 15.0
DEFAULT_PERSISTENCE_PENALTY: float = 20.0
DEFAULT_CROSS_SENSOR_PENALTY: float = 25.0
DEFAULT_INCREASING_TREND_PENALTY: float = 15.0

# STATUS SCORE BOUNDARIES
STATUS_THRESHOLD_MONITOR: float = 85.0
STATUS_THRESHOLD_INSPECTION_ADVISED: float = 65.0
STATUS_THRESHOLD_HIGH_PRIORITY_INSPECTION: float = 40.0


@dataclass(frozen=True)
class SHIConfig:
    """
    Configuration parameters for deterministic Structural Health Indicator scoring.

    All penalty weights represent prototype monitoring parameters, not certified engineering constants.
    """
    base_score: float = DEFAULT_BASE_SCORE
    anomaly_penalty: float = DEFAULT_ANOMALY_PENALTY
    persistence_penalty: float = DEFAULT_PERSISTENCE_PENALTY
    cross_sensor_penalty: float = DEFAULT_CROSS_SENSOR_PENALTY
    increasing_trend_penalty: float = DEFAULT_INCREASING_TREND_PENALTY

    def validate(self) -> None:
        """Validate configuration parameters."""
        from app.health.exceptions import InvalidHealthConfigError

        if self.base_score <= 0.0 or self.base_score > 100.0:
            raise InvalidHealthConfigError(f"base_score must be in (0, 100], got {self.base_score}")
        if self.anomaly_penalty < 0.0:
            raise InvalidHealthConfigError(f"anomaly_penalty must be non-negative, got {self.anomaly_penalty}")
        if self.persistence_penalty < 0.0:
            raise InvalidHealthConfigError(f"persistence_penalty must be non-negative, got {self.persistence_penalty}")
        if self.cross_sensor_penalty < 0.0:
            raise InvalidHealthConfigError(f"cross_sensor_penalty must be non-negative, got {self.cross_sensor_penalty}")
        if self.increasing_trend_penalty < 0.0:
            raise InvalidHealthConfigError(f"increasing_trend_penalty must be non-negative, got {self.increasing_trend_penalty}")


@dataclass(frozen=True)
class SHIDeductions:
    """Itemized penalty deductions applied during SHI score calculation."""
    anomaly_activity_deduction: float
    persistence_deduction: float
    cross_sensor_deduction: float
    increasing_trend_deduction: float
    total_deductions: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert itemized deductions to dictionary representation."""
        return {
            "anomaly_activity_deduction": round(self.anomaly_activity_deduction, 2),
            "persistence_deduction": round(self.persistence_deduction, 2),
            "cross_sensor_deduction": round(self.cross_sensor_deduction, 2),
            "increasing_trend_deduction": round(self.increasing_trend_deduction, 2),
            "total_deductions": round(self.total_deductions, 2),
        }


@dataclass(frozen=True)
class StructuralHealthResult:
    """
    Pure result representation of deterministic Structural Health Indicator (SHI) evaluation.

    Note:
        - SHI provides an observational prototype indicator (0-100) summarizing multi-step monitoring evidence.
        - SHI does NOT establish structural safety percentages, probability of failure, or certified damage ratings.

    Attributes:
        zone_id: Optional zone identifier under evaluation.
        timestamp: Timestamp of the evaluation.
        score: Clamped score in [0.0, 100.0].
        status: Categorical status classification (NORMAL, MONITOR, INSPECTION_ADVISED, HIGH_PRIORITY_INSPECTION).
        trend: Trend direction (STABLE, INCREASING, DECREASING, INSUFFICIENT_DATA).
        deductions: Itemized score penalties applied.
        reason: Summary explanation of score and status classification.
        evidence_summary: Tuple of human-readable explainable evidence statements.
        disclaimer: Safety disclaimer statement.
    """
    zone_id: Optional[int]
    timestamp: datetime
    score: float
    status: HealthStatus
    trend: str
    deductions: SHIDeductions
    reason: str
    evidence_summary: Tuple[str, ...]
    disclaimer: str = SHI_PROTOTYPE_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "zone_id": self.zone_id,
            "timestamp": self.timestamp.isoformat(),
            "score": round(self.score, 2),
            "status": self.status.value,
            "trend": self.trend,
            "deductions": self.deductions.to_dict(),
            "reason": self.reason,
            "evidence_summary": list(self.evidence_summary),
            "disclaimer": self.disclaimer,
        }
