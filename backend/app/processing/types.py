from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np


@dataclass
class SampledSignal:
    """Hardware-agnostic representation of a discrete sampled physical or simulated signal.

    Attributes:
        samples (np.ndarray): 1D array of floating-point sample values.
        sample_rate_hz (float): Sampling frequency in Hertz (> 0).
        timestamp (datetime): Acquisition timestamp (UTC).
        source_id (str): Generic source identifier (e.g. SIM-01, SENSOR-01).
    """

    samples: np.ndarray
    sample_rate_hz: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_id: str = "SIG-01"

    def __post_init__(self) -> None:
        """Validate signal attributes for numerical safety and domain constraints."""
        if not isinstance(self.samples, np.ndarray):
            self.samples = np.asarray(self.samples, dtype=np.float64)
        else:
            self.samples = self.samples.astype(np.float64)

        if self.samples.ndim != 1:
            raise ValueError(f"Signal samples must be 1-dimensional, got shape {self.samples.shape}")

        if len(self.samples) == 0:
            raise ValueError("Signal samples array cannot be empty")

        if not np.isfinite(self.samples).all():
            raise ValueError("Signal samples contain invalid NaN or Infinite values")

        if self.sample_rate_hz <= 0:
            raise ValueError(f"Sample rate must be positive, got {self.sample_rate_hz}")

        if not self.source_id or not isinstance(self.source_id, str):
            raise ValueError("source_id must be a non-empty string")


@dataclass
class DetectedWindow:
    """Represents a detected activity region within a SampledSignal.

    Attributes:
        start_index (int): Starting sample index (inclusive).
        end_index (int): Ending sample index (inclusive).
        start_time_ms (float): Start time in milliseconds relative to acquisition.
        end_time_ms (float): End time in milliseconds relative to acquisition.
        duration_ms (float): Duration of the window in milliseconds.
        peak_amplitude (float): Peak absolute amplitude within the window.
        rms_amplitude (float): Root mean square amplitude within the window.
        sample_count (int): Total number of samples in the window.
    """

    start_index: int
    end_index: int
    start_time_ms: float
    end_time_ms: float
    duration_ms: float
    peak_amplitude: float
    rms_amplitude: float
    sample_count: int

    def __post_init__(self) -> None:
        if self.start_index < 0 or self.end_index < self.start_index:
            raise ValueError(f"Invalid window index boundaries: [{self.start_index}, {self.end_index}]")
        if self.duration_ms < 0:
            raise ValueError(f"Window duration_ms cannot be negative, got {self.duration_ms}")


@dataclass
class ProcessedEvent:
    """Pure Python representation of a detected structural event observation and its features.

    Note:
        Features such as peak amplitude, energy, and dominant frequency are generic signal
        metrics and do not constitute certified engineering safety or failure measurements.
    """

    timestamp: datetime
    source_id: str
    magnitude: float
    energy: float
    duration_ms: float
    frequency_hz: Optional[float]
    rms_amplitude: float
    sample_count: int
    features: Dict[str, Any] = field(default_factory=dict)
