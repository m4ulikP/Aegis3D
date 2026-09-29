"""Signal generation module for representative discrete PZT sensor telemetry."""

import math
from typing import List, Optional, Tuple
import numpy as np


def generate_normal_signal(
    sample_count: int = 1000,
    sample_rate_hz: float = 1000.0,
    noise_std: float = 0.04,
    vibration_amp: float = 0.08,
    vibration_freq: float = 25.0,
    seed: Optional[int] = None,
) -> List[float]:
    """
    Generate representative normal structural baseline signal.

    Characteristics:
    - Low-amplitude background mechanical noise
    - Subtle structural ambient vibration hum
    - Peak amplitude well below event detection thresholds (< 0.35)
    """
    if sample_count <= 0:
        raise ValueError(f"sample_count must be positive, got {sample_count}")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")

    rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()

    t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
    # Ambient structural harmonic vibration
    vibration = vibration_amp * np.sin(2.0 * np.pi * vibration_freq * t)
    # Background mechanical Gaussian noise
    noise = rng.normal(0.0, noise_std, sample_count)

    signal = vibration + noise
    return signal.astype(float).tolist()


def generate_transient_signal(
    sample_count: int = 1000,
    sample_rate_hz: float = 1000.0,
    burst_amp: float = 1.35,
    burst_freq: float = 80.0,
    burst_duration: float = 0.04,
    burst_center_fraction: float = 0.4,
    noise_std: float = 0.04,
    seed: Optional[int] = None,
) -> List[float]:
    """
    Generate representative transient event signal.

    Characteristics:
    - Normal background noise
    - Moderate amplitude burst (e.g. ambient machinery or footfall transient)
    - Reaches standard event detection threshold (~1.0 to 1.5) without severe anomaly z-scores
    """
    if sample_count <= 0:
        raise ValueError(f"sample_count must be positive, got {sample_count}")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")

    rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()

    # Base noise
    t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
    signal = rng.normal(0.0, noise_std, sample_count)

    # Transient wave packet
    center_idx = int(sample_count * burst_center_fraction)
    half_samples = int(burst_duration * sample_rate_hz / 2.0)
    start_idx = max(0, center_idx - half_samples)
    end_idx = min(sample_count, center_idx + half_samples)

    if end_idx > start_idx:
        t_burst = t[start_idx:end_idx] - t[center_idx]
        # Damped oscillatory burst with Hanning-like envelope
        envelope = np.cos(np.pi * t_burst / (burst_duration if burst_duration > 0 else 0.01)) ** 2
        carrier = np.sin(2.0 * np.pi * burst_freq * t_burst)
        signal[start_idx:end_idx] += burst_amp * envelope * carrier

    return signal.astype(float).tolist()


def generate_anomaly_signal(
    sample_count: int = 1000,
    sample_rate_hz: float = 1000.0,
    peak_amp: float = 4.5,
    burst_freq: float = 120.0,
    burst_duration: float = 0.08,
    num_bursts: int = 1,
    noise_std: float = 0.04,
    seed: Optional[int] = None,
) -> List[float]:
    """
    Generate representative structural anomaly signal.

    Characteristics:
    - High-amplitude acoustic emission / stress release burst(s)
    - Amplitude (peak ~4.5) significantly exceeds typical zone baselines (e.g. 1.20 +/- 0.15)
    - Triggers backend event detection, high energy feature extraction, and |z| >= 3.0 anomaly detection
    """
    if sample_count <= 0:
        raise ValueError(f"sample_count must be positive, got {sample_count}")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
    if num_bursts <= 0:
        raise ValueError(f"num_bursts must be positive, got {num_bursts}")

    rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()

    t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
    signal = rng.normal(0.0, noise_std, sample_count)

    # Distribute burst centers across signal window
    burst_centers = [
        int(sample_count * ((i + 1) / (num_bursts + 1))) for i in range(num_bursts)
    ]

    half_samples = int(burst_duration * sample_rate_hz / 2.0)

    for center_idx in burst_centers:
        start_idx = max(0, center_idx - half_samples)
        end_idx = min(sample_count, center_idx + half_samples)
        if end_idx > start_idx:
            t_burst = t[start_idx:end_idx] - t[center_idx]
            # Exponentially damped sinusoid simulating acoustic wave release
            decay_rate = 30.0
            envelope = np.exp(-decay_rate * np.abs(t_burst))
            carrier = np.sin(2.0 * np.pi * burst_freq * t_burst)
            signal[start_idx:end_idx] += peak_amp * envelope * carrier

    return signal.astype(float).tolist()


def generate_correlated_pair(
    sample_count: int = 1000,
    sample_rate_hz: float = 1000.0,
    peak_amp: float = 4.5,
    tdoa_seconds: float = 0.005,
    attenuation: float = 0.85,
    burst_freq: float = 120.0,
    burst_duration: float = 0.08,
    noise_std: float = 0.04,
    seed: Optional[int] = None,
) -> Tuple[List[float], List[float], float]:
    """
    Generate a synchronized pair of representative signals for two PZT sensors in the same zone.

    Simulates a mechanical stress wave propagating through a structural member:
    - Sensor 1 (e.g. PZT-Z01, nearer sensor): detects the primary burst wave first.
    - Sensor 2 (e.g. PZT-Z02, downstream sensor): detects the burst wave delayed by tdoa_seconds
      with physical geometric attenuation.

    Args:
        sample_count: Number of samples per batch.
        sample_rate_hz: Sampling frequency in Hertz.
        peak_amp: Peak amplitude of primary burst at Sensor 1.
        tdoa_seconds: Relative time difference of arrival in seconds (e.g. 0.005s / 5ms,
                      well within backend 25ms correlation tolerance).
        attenuation: Amplitude factor for secondary sensor (e.g. 0.85 = 15% acoustic attenuation).
        burst_freq: Carrier frequency of stress burst in Hertz.
        burst_duration: Duration of stress burst in seconds.
        noise_std: Gaussian noise standard deviation.
        seed: Optional RNG seed for deterministic reproduction.

    Returns:
        Tuple of (samples_sensor_1, samples_sensor_2, tdoa_seconds)
    """
    if sample_count <= 0:
        raise ValueError(f"sample_count must be positive, got {sample_count}")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
    if tdoa_seconds < 0:
        raise ValueError(f"tdoa_seconds must be non-negative, got {tdoa_seconds}")

    rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()

    t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz

    # Independent background noise for each sensor
    sig1 = rng.normal(0.0, noise_std, sample_count)
    sig2 = rng.normal(0.0, noise_std, sample_count)

    # Primary burst location at ~35% of signal
    center_idx_1 = int(sample_count * 0.35)
    # Secondary burst delayed by tdoa_samples
    tdoa_samples = int(tdoa_seconds * sample_rate_hz)
    center_idx_2 = center_idx_1 + tdoa_samples

    half_samples = int(burst_duration * sample_rate_hz / 2.0)
    decay_rate = 30.0

    # Sensor 1 wave packet
    start1 = max(0, center_idx_1 - half_samples)
    end1 = min(sample_count, center_idx_1 + half_samples)
    if end1 > start1:
        t_burst1 = t[start1:end1] - t[center_idx_1]
        env1 = np.exp(-decay_rate * np.abs(t_burst1))
        car1 = np.sin(2.0 * np.pi * burst_freq * t_burst1)
        sig1[start1:end1] += peak_amp * env1 * car1

    # Sensor 2 wave packet (delayed & attenuated)
    start2 = max(0, center_idx_2 - half_samples)
    end2 = min(sample_count, center_idx_2 + half_samples)
    if end2 > start2:
        t_burst2 = t[start2:end2] - t[center_idx_2]
        env2 = np.exp(-decay_rate * np.abs(t_burst2))
        car2 = np.sin(2.0 * np.pi * burst_freq * t_burst2)
        sig2[start2:end2] += (peak_amp * attenuation) * env2 * car2

    return sig1.astype(float).tolist(), sig2.astype(float).tolist(), float(tdoa_seconds)

def generate_pzt_tone_burst(
    sample_count: int = 10000,
    sample_rate_hz: float = 100000.0,
    frequency_hz: float = 10000.0,
    amplitude: float = 0.8,
    cycles: int = 5,
) -> List[float]:
    """
    Generate a windowed PZT tone-burst excitation.

    The excitation is a short sinusoidal burst multiplied by a Hann
    window. It represents the signal produced by a PZT actuator before
    propagation through the structure.

    This is a reduced-order, physics-inspired excitation model and is
    not experimentally calibrated.
    """
    if sample_count <= 0:
        raise ValueError(
            f"sample_count must be positive, got {sample_count}"
        )

    if sample_rate_hz <= 0:
        raise ValueError(
            f"sample_rate_hz must be positive, got {sample_rate_hz}"
        )

    if frequency_hz <= 0:
        raise ValueError(
            f"frequency_hz must be positive, got {frequency_hz}"
        )

    if amplitude < 0:
        raise ValueError(
            f"amplitude cannot be negative, got {amplitude}"
        )

    if cycles <= 0:
        raise ValueError(
            f"cycles must be positive, got {cycles}"
        )

    # Duration required for the requested number of carrier cycles.
    burst_duration_s = cycles / frequency_hz

    burst_samples = max(
        1,
        round(burst_duration_s * sample_rate_hz),
    )

    # Don't allow the burst to exceed the requested signal window.
    burst_samples = min(burst_samples, sample_count)

    signal = np.zeros(sample_count, dtype=np.float64)

    # Time vector for the burst itself.
    t = np.arange(burst_samples, dtype=np.float64) / sample_rate_hz

    # Hann-windowed sinusoidal tone burst.
    carrier = np.sin(2.0 * np.pi * frequency_hz * t)

    if burst_samples > 1:
        window = np.hanning(burst_samples)
    else:
        window = np.ones(1, dtype=np.float64)

    signal[:burst_samples] = amplitude * carrier * window

    return signal.astype(float).tolist()