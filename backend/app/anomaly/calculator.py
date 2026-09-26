"""Hardware-agnostic pure rule-based statistical anomaly detection engine."""

import math
from typing import Any, List

from app.anomaly.exceptions import (
    InvalidBaselineError,
    InvalidEventDataError,
    InvalidThresholdError,
)
from app.anomaly.types import DEFAULT_ANOMALY_Z_THRESHOLD, AnomalyAnalysisResult


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """
    Calculate the standardized z-score deviation of a value from a baseline mean and std dev.

    Zero standard-deviation handling (std == 0.0):
    - When std == 0.0, standardized z-score is defined as 0.0 (finite).
    - Anomaly evaluation for a zero-variance baseline is handled explicitly based on whether
      the event value equals the baseline mean (normal) or differs from it (anomalous).
    """
    if std == 0.0:
        return 0.0
    return (value - mean) / std


def analyze_event_against_baseline(
    magnitude: float,
    energy: float,
    baseline_mean_magnitude: float,
    baseline_std_magnitude: float,
    baseline_mean_energy: float,
    baseline_std_energy: float,
    z_threshold: float = DEFAULT_ANOMALY_Z_THRESHOLD,
) -> AnomalyAnalysisResult:
    """
    Compare event features against baseline statistics using deterministic z-score thresholds.

    Note:
        - An anomaly indicates that an event is statistically unusual relative to the historical baseline.
        - This calculation does NOT signify structural damage, cracks, or failure prediction.
        - Magnitude and energy features are evaluated independently. An anomaly is flagged if EITHER feature exceeds the threshold.

    Args:
        magnitude: Physical event magnitude measurement.
        energy: Physical event signal energy measurement.
        baseline_mean_magnitude: Mean magnitude from zone baseline.
        baseline_std_magnitude: Standard deviation of magnitude from zone baseline.
        baseline_mean_energy: Mean energy from zone baseline.
        baseline_std_energy: Standard deviation of energy from zone baseline.
        z_threshold: Configurable statistical z-score threshold (default 3.0).

    Returns:
        AnomalyAnalysisResult containing boolean flags, z-scores, and explainable evidence strings.

    Raises:
        InvalidThresholdError: If z_threshold <= 0 or non-finite.
        InvalidEventDataError: If magnitude or energy are None or non-finite.
        InvalidBaselineError: If baseline stats are None, negative std dev, or non-finite.
    """
    # 1. Validate threshold
    if z_threshold is None or math.isnan(z_threshold) or math.isinf(z_threshold) or z_threshold <= 0:
        raise InvalidThresholdError(f"Anomaly threshold must be a positive finite number, got {z_threshold}")

    # 2. Validate event data
    if magnitude is None or energy is None:
        raise InvalidEventDataError("Event magnitude and energy must not be None")

    try:
        mag_val = float(magnitude)
        eng_val = float(energy)
    except (TypeError, ValueError) as err:
        raise InvalidEventDataError(f"Event magnitude and energy must be numeric floats: {err}") from err

    if math.isnan(mag_val) or math.isinf(mag_val) or math.isnan(eng_val) or math.isinf(eng_val):
        raise InvalidEventDataError(f"Event magnitude ({mag_val}) and energy ({eng_val}) must be finite numbers")

    # 3. Validate baseline data
    if (
        baseline_mean_magnitude is None
        or baseline_std_magnitude is None
        or baseline_mean_energy is None
        or baseline_std_energy is None
    ):
        raise InvalidBaselineError("Baseline statistics must not be None")

    try:
        b_mean_mag = float(baseline_mean_magnitude)
        b_std_mag = float(baseline_std_magnitude)
        b_mean_eng = float(baseline_mean_energy)
        b_std_eng = float(baseline_std_energy)
    except (TypeError, ValueError) as err:
        raise InvalidBaselineError(f"Baseline statistics must be numeric floats: {err}") from err

    if b_std_mag < 0 or b_std_eng < 0:
        raise InvalidBaselineError(
            f"Baseline std dev cannot be negative: std_magnitude={b_std_mag}, std_energy={b_std_eng}"
        )

    for stat_name, stat_val in [
        ("mean_magnitude", b_mean_mag),
        ("std_magnitude", b_std_mag),
        ("mean_energy", b_mean_eng),
        ("std_energy", b_std_eng),
    ]:
        if math.isnan(stat_val) or math.isinf(stat_val):
            raise InvalidBaselineError(f"Baseline stat '{stat_name}' must be a finite number, got {stat_val}")

    # 4. Perform z-score and zero-variance anomaly evaluation
    z_mag = calculate_z_score(mag_val, b_mean_mag, b_std_mag)
    z_eng = calculate_z_score(eng_val, b_mean_eng, b_std_eng)

    mag_anomalous = (mag_val != b_mean_mag) if b_std_mag == 0.0 else (abs(z_mag) >= z_threshold)
    eng_anomalous = (eng_val != b_mean_eng) if b_std_eng == 0.0 else (abs(z_eng) >= z_threshold)
    is_anomalous = mag_anomalous or eng_anomalous

    # 5. Generate explainable evidence
    reasons: List[str] = []
    if mag_anomalous:
        if b_std_mag == 0.0:
            reasons.append(
                f"Magnitude ({mag_val:.2f}) deviated from zero-variance baseline mean ({b_mean_mag:.2f})"
            )
        else:
            reasons.append(
                f"Magnitude deviation (|z| = {abs(z_mag):.2f}σ) exceeded statistical threshold ({z_threshold:.2f}σ)"
            )

    if eng_anomalous:
        if b_std_eng == 0.0:
            reasons.append(
                f"Energy ({eng_val:.2f}) deviated from zero-variance baseline mean ({b_mean_eng:.2f})"
            )
        else:
            reasons.append(
                f"Energy deviation (|z| = {abs(z_eng):.2f}σ) exceeded statistical threshold ({z_threshold:.2f}σ)"
            )

    if not is_anomalous:
        mag_str = f"{abs(z_mag):.2f}"
        eng_str = f"{abs(z_eng):.2f}"
        reasons.append(
            f"Event magnitude (|z| = {mag_str}σ) and energy (|z| = {eng_str}σ) are within normal statistical threshold ({z_threshold:.2f}σ)"
        )

    return AnomalyAnalysisResult(
        is_anomalous=is_anomalous,
        magnitude_z_score=z_mag,
        energy_z_score=z_eng,
        magnitude_anomalous=mag_anomalous,
        energy_anomalous=eng_anomalous,
        threshold_used=z_threshold,
        reasons=tuple(reasons),
    )


def analyze_event(
    event: Any,
    baseline: Any,
    z_threshold: float = DEFAULT_ANOMALY_Z_THRESHOLD,
) -> AnomalyAnalysisResult:
    """
    Convenience wrapper to analyze an Event or ProcessedEvent against a Baseline or BaselineStatistics.
    """
    if event is None:
        raise InvalidEventDataError("Event object must not be None")
    if baseline is None:
        raise InvalidBaselineError("Baseline object must not be None")

    mag = getattr(event, "magnitude", None)
    if mag is None and isinstance(event, dict):
        mag = event.get("magnitude")
    if mag is None and hasattr(event, "peak_amplitude"):
        mag = getattr(event, "peak_amplitude")

    eng = getattr(event, "energy", None)
    if eng is None and isinstance(event, dict):
        eng = event.get("energy")
    if eng is None and hasattr(event, "signal_energy"):
        eng = getattr(event, "signal_energy")

    b_mean_mag = getattr(baseline, "mean_magnitude", None)
    if b_mean_mag is None and isinstance(baseline, dict):
        b_mean_mag = baseline.get("mean_magnitude")

    b_std_mag = getattr(baseline, "std_magnitude", None)
    if b_std_mag is None and isinstance(baseline, dict):
        b_std_mag = baseline.get("std_magnitude")

    b_mean_eng = getattr(baseline, "mean_energy", None)
    if b_mean_eng is None and isinstance(baseline, dict):
        b_mean_eng = baseline.get("mean_energy")

    b_std_eng = getattr(baseline, "std_energy", None)
    if b_std_eng is None and isinstance(baseline, dict):
        b_std_eng = baseline.get("std_energy")

    return analyze_event_against_baseline(
        magnitude=mag,
        energy=eng,
        baseline_mean_magnitude=b_mean_mag,
        baseline_std_magnitude=b_std_mag,
        baseline_mean_energy=b_mean_eng,
        baseline_std_energy=b_std_eng,
        z_threshold=z_threshold,
    )
