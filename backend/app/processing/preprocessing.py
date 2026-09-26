import numpy as np

from app.processing.types import SampledSignal


def remove_dc_offset(signal: SampledSignal) -> SampledSignal:
    """Removes DC offset from a signal by subtracting the mean sample value.

    Args:
        signal (SampledSignal): Input sampled signal.

    Returns:
        SampledSignal: Preprocessed signal with zero mean.
    """
    mean_val = np.mean(signal.samples)
    centered_samples = signal.samples - mean_val
    return SampledSignal(
        samples=centered_samples,
        sample_rate_hz=signal.sample_rate_hz,
        timestamp=signal.timestamp,
        source_id=signal.source_id,
    )


def normalize_amplitude(signal: SampledSignal, target_peak: float = 1.0) -> SampledSignal:
    """Deterministically normalizes signal amplitude so peak absolute value equals target_peak.

    Args:
        signal (SampledSignal): Input sampled signal.
        target_peak (float): Desired peak absolute amplitude (> 0).

    Returns:
        SampledSignal: Scaled signal with maximum absolute amplitude equal to target_peak.
    """
    if target_peak <= 0:
        raise ValueError(f"target_peak must be positive, got {target_peak}")

    max_abs = np.max(np.abs(signal.samples))
    if max_abs == 0:
        scaled_samples = np.copy(signal.samples)
    else:
        scaled_samples = (signal.samples / max_abs) * target_peak

    return SampledSignal(
        samples=scaled_samples,
        sample_rate_hz=signal.sample_rate_hz,
        timestamp=signal.timestamp,
        source_id=signal.source_id,
    )
