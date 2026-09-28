"""Unit tests for simulator signal generator module."""

import math
import pytest

from simulator.signal_generator import (
    generate_anomaly_signal,
    generate_correlated_pair,
    generate_normal_signal,
    generate_transient_signal,
)


def test_generate_normal_signal_properties():
    """Verify normal signal produces low-amplitude finite baseline samples."""
    samples = generate_normal_signal(sample_count=500, sample_rate_hz=1000.0, seed=42)

    assert isinstance(samples, list)
    assert len(samples) == 500
    assert all(isinstance(x, float) for x in samples)
    assert all(not (math.isnan(x) or math.isinf(x)) for x in samples)

    # Normal signal should remain well below typical event detection thresholds (e.g. 1.0)
    peak = max(abs(x) for x in samples)
    assert peak < 0.35


def test_generate_transient_signal_properties():
    """Verify transient signal contains a moderate localized burst."""
    samples = generate_transient_signal(sample_count=800, sample_rate_hz=1000.0, burst_amp=1.4, seed=42)

    assert len(samples) == 800
    peak = max(abs(x) for x in samples)
    # Peak should approach or reach the burst amplitude
    assert 1.0 <= peak <= 1.6


def test_generate_anomaly_signal_properties():
    """Verify anomaly signal generates high-amplitude structural disturbance."""
    samples = generate_anomaly_signal(sample_count=1000, sample_rate_hz=1000.0, peak_amp=4.5, seed=42)

    assert len(samples) == 1000
    peak = max(abs(x) for x in samples)
    assert peak >= 3.5

    # Energy of anomaly signal should be substantially higher than normal signal
    normal_samples = generate_normal_signal(sample_count=1000, sample_rate_hz=1000.0, seed=42)
    normal_energy = sum(x**2 for x in normal_samples)
    anomaly_energy = sum(x**2 for x in samples)
    assert anomaly_energy > 10.0 * normal_energy


def test_deterministic_reproducibility_with_seed():
    """Verify specifying the same RNG seed reproduces identical discrete samples."""
    s1 = generate_anomaly_signal(sample_count=300, sample_rate_hz=1000.0, seed=12345)
    s2 = generate_anomaly_signal(sample_count=300, sample_rate_hz=1000.0, seed=12345)
    assert s1 == s2

    s_diff = generate_anomaly_signal(sample_count=300, sample_rate_hz=1000.0, seed=99999)
    assert s1 != s_diff


def test_generate_correlated_pair():
    """Verify 2-PZT correlated pair generates physically related waveforms with expected TDOA."""
    fs = 1000.0
    tdoa_sec = 0.005  # 5ms = 5 samples at 1000 Hz
    s1, s2, ret_tdoa = generate_correlated_pair(
        sample_count=1000,
        sample_rate_hz=fs,
        peak_amp=4.5,
        tdoa_seconds=tdoa_sec,
        attenuation=0.85,
        seed=42,
    )

    assert len(s1) == 1000
    assert len(s2) == 1000
    assert ret_tdoa == pytest.approx(0.005)

    # Peak amplitude of sensor 2 should reflect attenuation
    peak1 = max(abs(x) for x in s1)
    peak2 = max(abs(x) for x in s2)
    assert peak1 > peak2
    assert peak2 == pytest.approx(peak1 * 0.85, rel=0.1)

    # Argmax peak of sensor 2 should be delayed relative to sensor 1
    idx1 = max(range(len(s1)), key=lambda i: abs(s1[i]))
    idx2 = max(range(len(s2)), key=lambda i: abs(s2[i]))
    assert idx2 >= idx1


def test_invalid_parameters_raise_value_errors():
    """Verify parameter validation raises appropriate errors."""
    with pytest.raises(ValueError, match="sample_count must be positive"):
        generate_normal_signal(sample_count=0)

    with pytest.raises(ValueError, match="sample_rate_hz must be positive"):
        generate_anomaly_signal(sample_count=100, sample_rate_hz=-10.0)

    with pytest.raises(ValueError, match="tdoa_seconds must be non-negative"):
        generate_correlated_pair(sample_count=100, tdoa_seconds=-0.01)
