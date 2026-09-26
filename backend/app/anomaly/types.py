"""Data types and result representations for rule-based anomaly detection."""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

DEFAULT_ANOMALY_Z_THRESHOLD: float = 3.0


@dataclass(frozen=True)
class AnomalyAnalysisResult:
    """
    Pure numerical result of comparing an event's features against a zone baseline.

    Attributes:
        is_anomalous: True if any feature's absolute z-score meets or exceeds threshold.
        magnitude_z_score: Standardized deviation for magnitude.
        energy_z_score: Standardized deviation for energy.
        magnitude_anomalous: True if magnitude deviation meets or exceeds threshold.
        energy_anomalous: True if energy deviation meets or exceeds threshold.
        threshold_used: Statistical z-score threshold used for comparison.
        reasons: List of human-readable explainable evidence strings.
    """
    is_anomalous: bool
    magnitude_z_score: float
    energy_z_score: float
    magnitude_anomalous: bool
    energy_anomalous: bool
    threshold_used: float
    reasons: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "is_anomalous": self.is_anomalous,
            "magnitude_z_score": self.magnitude_z_score,
            "energy_z_score": self.energy_z_score,
            "magnitude_anomalous": self.magnitude_anomalous,
            "energy_anomalous": self.energy_anomalous,
            "threshold_used": self.threshold_used,
            "reasons": list(self.reasons),
        }
