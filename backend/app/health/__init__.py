"""
Aegis3D Step 10: Deterministic Structural Health Indicator (SHI) Module.

Provides pure hardware-agnostic functions and data types to summarize accumulated multi-step evidence
(anomaly detection, temporal persistence, cross-sensor correlation, and trend analysis) into a
deterministic prototype monitoring score (0-100) and HealthStatus classification.
"""

from app.health.calculator import calculate_structural_health_indicator
from app.health.exceptions import HealthError, InvalidHealthConfigError
from app.health.types import (
    DEFAULT_ANOMALY_PENALTY,
    DEFAULT_BASE_SCORE,
    DEFAULT_CROSS_SENSOR_PENALTY,
    DEFAULT_INCREASING_TREND_PENALTY,
    DEFAULT_PERSISTENCE_PENALTY,
    SHI_PROTOTYPE_DISCLAIMER,
    SHIConfig,
    SHIDeductions,
    StructuralHealthResult,
)
from app.models.enums import HealthStatus, HealthTrend

__all__ = [
    "calculate_structural_health_indicator",
    "StructuralHealthResult",
    "SHIDeductions",
    "SHIConfig",
    "HealthStatus",
    "HealthTrend",
    "HealthError",
    "InvalidHealthConfigError",
    "SHI_PROTOTYPE_DISCLAIMER",
    "DEFAULT_BASE_SCORE",
    "DEFAULT_ANOMALY_PENALTY",
    "DEFAULT_PERSISTENCE_PENALTY",
    "DEFAULT_CROSS_SENSOR_PENALTY",
    "DEFAULT_INCREASING_TREND_PENALTY",
]
