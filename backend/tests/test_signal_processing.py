from datetime import datetime, timezone
import numpy as np
import pytest

from app.processing import (
    DetectedWindow,
    ProcessedEvent,
    SampledSignal,
    detect_events,
    extract_features,
    lowpass_filter,
    moving_average_filter,
    normalize_amplitude,
    process_signal_pipeline,
    remove_dc_offset,
)


def test_sampled_signal_valid():
    """Verify valid SampledSignal creation and array conversion."""
    sig = SampledSignal(samples=[1.0, 2.0, 3.0], sample_rate_hz=1000.0, source_id="SIM-01")
    assert isinstance(sig.samples, np.ndarray)
    assert len(sig.samples) == 3
    assert sig.sample_rate_hz == 1000.0
    assert sig.source_id == "SIM-01"


def test_sampled_signal_invalid_sample_rate():
    """Verify invalid sample rate <= 0 raises ValueError."""
    with pytest.raises(ValueError, match="Sample rate must be positive"):
        SampledSignal(samples=[1.0, 2.0], sample_rate_hz=0.0)

    with pytest.raises(ValueError, match="Sample rate must be positive"):
        SampledSignal(samples=[1.0, 2.0], sample_rate_hz=-100.0)


def test_sampled_signal_empty_samples():
    """Verify empty samples array raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        SampledSignal(samples=[], sample_rate_hz=1000.0)


def test_sampled_signal_nan_or_inf():
    """Verify NaN or Infinite sample values raise ValueError."""
    with pytest.raises(ValueError, match="NaN or Infinite"):
        SampledSignal(samples=[1.0, np.nan, 3.0], sample_rate_hz=1000.0)

    with pytest.raises(ValueError, match="NaN or Infinite"):
        SampledSignal(samples=[1.0, np.inf, 3.0], sample_rate_hz=1000.0)


def test_dc_offset_removal():
    """Verify DC offset removal subtracts mean sample value."""
    raw_samples = np.array([10.0, 12.0, 8.0, 10.0])  # mean = 10.0
    sig = SampledSignal(samples=raw_samples, sample_rate_hz=1000.0)

    dc_removed = remove_dc_offset(sig)
    assert np.isclose(np.mean(dc_removed.samples), 0.0, atol=1e-12)
    assert np.allclose(dc_removed.samples, [0.0, 2.0, -2.0, 0.0])


def test_normalize_amplitude():
    """Verify normalize_amplitude scales maximum peak amplitude."""
    sig = SampledSignal(samples=[-4.0, 2.0, 1.0], sample_rate_hz=1000.0)
    norm = normalize_amplitude(sig, target_peak=1.0)
    assert np.max(np.abs(norm.samples)) == pytest.approx(1.0)
    assert norm.samples[0] == pytest.approx(-1.0)


def test_moving_average_filter():
    """Verify moving_average_filter smooths samples and preserves length."""
    raw_samples = np.array([0.0, 0.0, 10.0, 0.0, 0.0])
    sig = SampledSignal(samples=raw_samples, sample_rate_hz=1000.0)

    filtered = moving_average_filter(sig, window_size=3)
    assert len(filtered.samples) == len(raw_samples)
    assert filtered.sample_rate_hz == sig.sample_rate_hz
    # Center element at index 2 average over [0, 10, 0] = 3.3333
    assert filtered.samples[2] == pytest.approx(10.0 / 3.0)


def test_moving_average_filter_invalid_window():
    """Verify invalid window_size raises ValueError."""
    sig = SampledSignal(samples=[1.0, 2.0, 3.0], sample_rate_hz=1000.0)
    with pytest.raises(ValueError, match="window_size must be >= 1"):
        moving_average_filter(sig, window_size=0)

    with pytest.raises(ValueError, match="cannot exceed signal sample count"):
        moving_average_filter(sig, window_size=10)


def test_lowpass_filter():
    """Verify Butterworth lowpass filter attenuates high frequencies."""
    t = np.linspace(0, 1.0, 1000, endpoint=False)
    # Signal composed of 5 Hz low frequency + 200 Hz high frequency noise
    sig_5hz = np.sin(2 * np.pi * 5 * t)
    sig_200hz = 0.5 * np.sin(2 * np.pi * 200 * t)
    combined = sig_5hz + sig_200hz

    sig = SampledSignal(samples=combined, sample_rate_hz=1000.0)
    filtered = lowpass_filter(sig, cutoff_hz=20.0, order=2)

    assert len(filtered.samples) == len(combined)
    # High frequency 200Hz component should be significantly attenuated
    assert np.std(filtered.samples - sig_5hz) < np.std(combined - sig_5hz)


def test_lowpass_filter_invalid_cutoff():
    """Verify cutoff_hz >= Nyquist frequency raises ValueError."""
    sig = SampledSignal(samples=np.ones(100), sample_rate_hz=1000.0)  # Nyquist = 500 Hz
    with pytest.raises(ValueError, match="less than Nyquist frequency"):
        lowpass_filter(sig, cutoff_hz=500.0)


def test_event_detection_quiet_signal():
    """Verify quiet signal below threshold produces no detected event windows."""
    samples = np.random.RandomState(42).normal(0, 0.01, 1000)
    sig = SampledSignal(samples=samples, sample_rate_hz=1000.0)

    windows = detect_events(sig, threshold=0.1)
    assert len(windows) == 0


def test_event_detection_single_burst():
    """Verify signal with single amplitude burst detects exactly 1 event window."""
    samples = np.zeros(1000)
    samples[300:350] = 5.0  # Burst of 50 samples
    sig = SampledSignal(samples=samples, sample_rate_hz=1000.0)

    windows = detect_events(sig, threshold=1.0)
    assert len(windows) == 1
    win = windows[0]
    assert win.start_index == 300
    assert win.end_index == 349
    assert win.sample_count == 50
    assert win.peak_amplitude == pytest.approx(5.0)
    assert win.duration_ms == pytest.approx(50.0)  # 50 samples at 1000Hz = 50ms


def test_event_detection_multiple_bursts_and_gap_merging():
    """Verify multiple bursts detection and gap merging functionality."""
    samples = np.zeros(1000)
    samples[100:150] = 3.0
    samples[155:200] = 4.0  # Gap of 4 samples (151 to 154)
    samples[500:550] = 3.0  # Far away burst

    sig = SampledSignal(samples=samples, sample_rate_hz=1000.0)

    # Without merging (merge_gap_samples=0)
    windows_no_merge = detect_events(sig, threshold=1.0, merge_gap_samples=0)
    assert len(windows_no_merge) == 3

    # With merging (merge_gap_samples=5)
    windows_merged = detect_events(sig, threshold=1.0, merge_gap_samples=5)
    assert len(windows_merged) == 2
    assert windows_merged[0].start_index == 100
    assert windows_merged[0].end_index == 199


def test_event_detection_invalid_threshold():
    """Verify threshold <= 0 raises ValueError."""
    sig = SampledSignal(samples=[1.0, 2.0], sample_rate_hz=1000.0)
    with pytest.raises(ValueError, match="threshold must be positive"):
        detect_events(sig, threshold=0.0)


def test_feature_extraction():
    """Verify feature extraction computes peak, RMS, energy, duration, and dominant frequency."""
    # 50 Hz sine wave for 0.1 second (100 samples at 1000Hz)
    sample_rate = 1000.0
    t = np.linspace(0, 0.1, 100, endpoint=False)
    sine_samples = 2.0 * np.sin(2 * np.pi * 50 * t)

    sig = SampledSignal(samples=sine_samples, sample_rate_hz=sample_rate, source_id="SIM-SINE")
    win = DetectedWindow(
        start_index=0,
        end_index=99,
        start_time_ms=0.0,
        end_time_ms=100.0,
        duration_ms=100.0,
        peak_amplitude=2.0,
        rms_amplitude=float(np.sqrt(np.mean(sine_samples**2))),
        sample_count=100,
    )

    processed_event = extract_features(sig, win)
    assert isinstance(processed_event, ProcessedEvent)
    assert processed_event.source_id == "SIM-SINE"
    assert processed_event.magnitude == pytest.approx(2.0, rel=1e-2)
    assert processed_event.energy == pytest.approx(np.sum(sine_samples**2))
    assert processed_event.duration_ms == pytest.approx(100.0)
    assert processed_event.sample_count == 100
    assert processed_event.frequency_hz == pytest.approx(50.0, abs=1.0)


def test_end_to_end_process_signal_pipeline():
    """Test full signal processing pipeline from raw signal to ProcessedEvent list."""
    t = np.linspace(0, 1.0, 1000, endpoint=False)
    # Raw signal: DC offset (10.0) + quiet noise + one 100 Hz burst
    raw = np.full(1000, 10.0)
    raw[400:500] += 5.0 * np.sin(2 * np.pi * 100 * t[400:500])

    sig = SampledSignal(samples=raw, sample_rate_hz=1000.0, source_id="SIM-BURST-01")

    events = process_signal_pipeline(
        signal=sig,
        detection_threshold=2.0,
        remove_dc=True,
        filter_window_size=3,
        min_duration_samples=10,
        merge_gap_samples=5,
    )


    assert len(events) == 1
    event = events[0]
    assert event.source_id == "SIM-BURST-01"
    assert event.magnitude > 4.0
    assert event.duration_ms >= 90.0
    assert event.frequency_hz is not None
    assert event.frequency_hz == pytest.approx(100.0, abs=5.0)
