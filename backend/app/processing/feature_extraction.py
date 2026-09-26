from typing import Optional
import numpy as np

from app.processing.types import DetectedWindow, ProcessedEvent, SampledSignal


def extract_features(signal: SampledSignal, window: DetectedWindow) -> ProcessedEvent:
    """Calculates generic measurable features for a detected signal event window.

    Note:
        - Energy is calculated as discrete signal energy (sum of squared sample values),
          not calibrated physical Joules.
        - Dominant frequency is a signal-spectrum feature derived via FFT and does not
          imply certified structural material interpretation.

    Args:
        signal (SampledSignal): Source sampled signal.
        window (DetectedWindow): Detected event window.

    Returns:
        ProcessedEvent: Feature extraction result mapable to Event domain objects.
    """
    win_samples = signal.samples[window.start_index : window.end_index + 1]
    sample_cnt = len(win_samples)

    if sample_cnt == 0:
        raise ValueError("Cannot extract features from empty window sample slice")

    peak_amplitude = float(np.max(np.abs(win_samples)))
    rms_amplitude = float(np.sqrt(np.mean(win_samples**2)))
    discrete_energy = float(np.sum(win_samples**2))
    duration_ms = float((sample_cnt / signal.sample_rate_hz) * 1000.0)

    # Compute dominant frequency via real FFT if sample count is sufficient
    dominant_frequency_hz: Optional[float] = None
    if sample_cnt >= 4:
        fft_vals = np.abs(np.fft.rfft(win_samples))
        fft_freqs = np.fft.rfftfreq(sample_cnt, d=1.0 / signal.sample_rate_hz)
        # Exclude DC component (index 0) if multiple frequencies exist
        if len(fft_vals) > 1:
            peak_freq_idx = np.argmax(fft_vals[1:]) + 1
            dominant_frequency_hz = float(fft_freqs[peak_freq_idx])
        else:
            dominant_frequency_hz = float(fft_freqs[0])

    features_dict = {
        "sample_count": sample_cnt,
        "rms_amplitude": rms_amplitude,
        "peak_amplitude": peak_amplitude,
        "discrete_signal_energy": discrete_energy,
    }

    return ProcessedEvent(
        timestamp=signal.timestamp,
        source_id=signal.source_id,
        magnitude=peak_amplitude,
        energy=discrete_energy,
        duration_ms=duration_ms,
        frequency_hz=dominant_frequency_hz,
        rms_amplitude=rms_amplitude,
        sample_count=sample_cnt,
        features=features_dict,
    )
