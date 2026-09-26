import numpy as np
from scipy import signal as scipy_signal

from app.processing.types import SampledSignal


def moving_average_filter(signal: SampledSignal, window_size: int = 5) -> SampledSignal:
    """Applies a deterministic moving-average smoothing filter to the signal.

    Preserves original signal length, sample rate, and timestamp.

    Args:
        signal (SampledSignal): Input sampled signal.
        window_size (int): Size of the moving average window (odd integer >= 1).

    Returns:
        SampledSignal: Smoothed signal.
    """
    if window_size < 1:
        raise ValueError(f"window_size must be >= 1, got {window_size}")

    if window_size > len(signal.samples):
        raise ValueError(
            f"window_size ({window_size}) cannot exceed signal sample count ({len(signal.samples)})"
        )

    # Calculate uniform moving average convolution
    kernel = np.ones(window_size, dtype=np.float64) / window_size
    smoothed_samples = np.convolve(signal.samples, kernel, mode="same")

    return SampledSignal(
        samples=smoothed_samples,
        sample_rate_hz=signal.sample_rate_hz,
        timestamp=signal.timestamp,
        source_id=signal.source_id,
    )


def lowpass_filter(signal: SampledSignal, cutoff_hz: float, order: int = 2) -> SampledSignal:
    """Applies a Butterworth lowpass filter to the signal.

    Args:
        signal (SampledSignal): Input sampled signal.
        cutoff_hz (float): Cutoff frequency in Hertz.
        order (int): Filter order (default 2).

    Returns:
        SampledSignal: Filtered signal.
    """
    nyquist = signal.sample_rate_hz / 2.0
    if cutoff_hz <= 0 or cutoff_hz >= nyquist:
        raise ValueError(
            f"cutoff_hz ({cutoff_hz}) must be positive and less than Nyquist frequency ({nyquist} Hz)"
        )

    if order < 1:
        raise ValueError(f"Filter order must be >= 1, got {order}")

    # Use SciPy Butterworth digital filter
    normalized_cutoff = cutoff_hz / nyquist
    b, a = scipy_signal.butter(order, normalized_cutoff, btype="low", analog=False)

    # For short signals where filtfilt edge padding exceeds array length, use lfilter
    pad_len = 3 * max(len(a), len(b))
    if len(signal.samples) <= pad_len:
        filtered_samples = scipy_signal.lfilter(b, a, signal.samples)
    else:
        filtered_samples = scipy_signal.filtfilt(b, a, signal.samples)

    return SampledSignal(
        samples=filtered_samples,
        sample_rate_hz=signal.sample_rate_hz,
        timestamp=signal.timestamp,
        source_id=signal.source_id,
    )
