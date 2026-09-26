from datetime import datetime, timezone
import os
import sys
from pathlib import Path
import numpy as np

# Set matplotlib backend to headless-safe Agg before importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure backend root directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.processing import (
    SampledSignal,
    detect_events,
    extract_features,
    moving_average_filter,
    process_signal_pipeline,
    remove_dc_offset,
)


def generate_synthetic_demo_signal() -> SampledSignal:
    """Generates a deterministic synthetic signal containing noise, DC offset, and two bursts."""
    sample_rate_hz = 10000.0
    duration_s = 1.0
    num_samples = int(sample_rate_hz * duration_s)
    t = np.linspace(0, duration_s, num_samples, endpoint=False)

    # Deterministic background noise with fixed seed
    rng = np.random.RandomState(42)
    noise = rng.normal(loc=0.0, scale=0.1, size=num_samples)

    # Constant DC offset
    dc_offset = 5.0
    samples = np.full(num_samples, dc_offset) + noise

    # Burst 1: ~0.20s to 0.30s (samples 2000..3000), 200 Hz tone, amplitude 3.5
    burst1_mask = (t >= 0.20) & (t < 0.30)
    samples[burst1_mask] += 3.5 * np.sin(2 * np.pi * 200.0 * t[burst1_mask])

    # Burst 2: ~0.65s to 0.75s (samples 6500..7500), 450 Hz tone, amplitude 5.0
    burst2_mask = (t >= 0.65) & (t < 0.75)
    samples[burst2_mask] += 5.0 * np.sin(2 * np.pi * 450.0 * t[burst2_mask])

    return SampledSignal(
        samples=samples,
        sample_rate_hz=sample_rate_hz,
        timestamp=datetime.now(timezone.utc),
        source_id="SIM-DEMO-01",
    )


def main():
    print("=" * 60)
    print("       AEGIS3D SIGNAL PROCESSING DEMONSTRATION")
    print("=" * 60)

    # 1. INPUT STAGE
    raw_signal = generate_synthetic_demo_signal()
    dt = 1.0 / raw_signal.sample_rate_hz
    duration = len(raw_signal.samples) * dt

    print("\nINPUT")
    print("-" * 60)
    print(f"Source ID:       {raw_signal.source_id}")
    print(f"Sample Rate:     {raw_signal.sample_rate_hz:,.0f} Hz")
    print(f"Duration:        {duration:.3f} s")
    print(f"Sample Count:    {len(raw_signal.samples):,}")
    print(f"Timestamp:       {raw_signal.timestamp.isoformat()}")
    print("\nInput Signal Characteristics:")
    print("  - Deterministic synthetic signal with fixed random seed (42)")
    print("  - Low-amplitude background noise (std = 0.1)")
    print("  - DC offset bias (+5.0 V)")
    print("  - Synthetic Burst 1: ~0.20s - 0.30s (200 Hz tone, peak 3.5)")
    print("  - Synthetic Burst 2: ~0.65s - 0.75s (450 Hz tone, peak 5.0)")

    sample_preview = [round(float(v), 3) for v in raw_signal.samples[:10]]
    print(f"\nRaw Samples Preview (first 10 samples):\n  {sample_preview}")

    # 2. PROCESSING STAGE
    print("\nPROCESSING STAGE")
    print("-" * 60)
    mean_before = float(np.mean(raw_signal.samples))

    # Stage 1: DC Offset Removal
    dc_removed_signal = remove_dc_offset(raw_signal)
    mean_after = float(np.mean(dc_removed_signal.samples))
    print(f"1. DC Offset Removal       [OK] (Mean: {mean_before:.3f} -> {mean_after:.3f})")

    # Stage 2: Low-pass Smoothing Filter
    window_size = 5
    filtered_signal = moving_average_filter(dc_removed_signal, window_size=window_size)
    print(f"2. Moving Average Filter   [OK] (Window size: {window_size} samples)")

    # Stage 3: Event Detection
    detection_threshold = 1.5
    min_duration_samples = 50
    merge_gap_samples = 20

    windows = detect_events(
        filtered_signal,
        threshold=detection_threshold,
        min_duration_samples=min_duration_samples,
        merge_gap_samples=merge_gap_samples,
    )
    print(f"3. Event Detection         [OK] (Threshold: {detection_threshold}, Detected Windows: {len(windows)})")

    # Stage 4: Feature Extraction
    processed_events = [extract_features(filtered_signal, win) for win in windows]
    print(f"4. Feature Extraction      [OK] (Extracted features for {len(processed_events)} event(s))")

    # 3. OUTPUT STAGE
    print("\nOUTPUT")
    print("-" * 60)
    print(f"Detected Events Count: {len(processed_events)}\n")

    for idx, event in enumerate(processed_events, start=1):
        win = windows[idx - 1]
        start_sec = win.start_index * dt
        end_sec = (win.end_index + 1) * dt
        freq_str = f"{event.frequency_hz:.2f} Hz" if event.frequency_hz is not None else "N/A"

        print(f"Event #{idx}:")
        print(f"  Start Time:          {start_sec:.3f} s (Index {win.start_index})")
        print(f"  End Time:            {end_sec:.3f} s (Index {win.end_index})")
        print(f"  Duration:            {event.duration_ms:.2f} ms")
        print(f"  Peak Amplitude:      {event.magnitude:.4f}")
        print(f"  RMS Amplitude:       {event.rms_amplitude:.4f}")
        print(f"  Signal Energy:       {event.energy:.4f}")
        print(f"  Sample Count:        {event.sample_count}")
        print(f"  Dominant Frequency:  {freq_str}\n")

    # Compact Overview Table
    print("COMPACT SUMMARY TABLE")
    print("-" * 75)
    print(f"{'Event':<7} | {'Start(s)':<8} | {'End(s)':<8} | {'Dur(ms)':<8} | {'Peak':<7} | {'RMS':<7} | {'Energy':<8} | {'Freq(Hz)':<8}")
    print("-" * 75)
    for idx, (event, win) in enumerate(zip(processed_events, windows), start=1):
        start_sec = win.start_index * dt
        end_sec = (win.end_index + 1) * dt
        freq_val = f"{event.frequency_hz:.1f}" if event.frequency_hz is not None else "N/A"
        print(
            f"#{idx:<6} | {start_sec:<8.3f} | {end_sec:<8.3f} | {event.duration_ms:<8.2f} | "
            f"{event.magnitude:<7.3f} | {event.rms_amplitude:<7.3f} | {event.energy:<8.2f} | {freq_val:<8}"
        )
    print("-" * 75)

    print("\nDisclaimer:")
    print("  These are signal-processing measurements from the synthetic test signal.")
    print("  They are not structural safety or physical material assessments.")

    # 4. VISUALIZATION STAGE
    project_root = backend_dir.parent
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_plot_path = output_dir / "step5_signal_demo.png"

    time_axis = np.linspace(0, duration, len(raw_signal.samples), endpoint=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(time_axis, dc_removed_signal.samples, label="DC-Removed Signal", alpha=0.5)
    ax.plot(time_axis, filtered_signal.samples, label="Smoothed Filtered Signal", linewidth=1.5)

    # Plot detection threshold lines
    ax.axhline(y=detection_threshold, color="r", linestyle="--", label=f"Threshold (+{detection_threshold})")
    ax.axhline(y=-detection_threshold, color="r", linestyle="--", label=f"Threshold (-{detection_threshold})")

    # Highlight detected event regions
    for idx, win in enumerate(windows, start=1):
        t_start = win.start_index * dt
        t_end = (win.end_index + 1) * dt
        ax.axvspan(t_start, t_end, color="yellow", alpha=0.3, label=f"Detected Event #{idx}" if idx == 1 else "")

    ax.set_title("Aegis3D Step 5 — Signal Processing & Event Detection Demo", fontsize=14)
    ax.set_xlabel("Time (seconds)", fontsize=12)
    ax.set_ylabel("Amplitude", fontsize=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(output_plot_path, dpi=150)
    plt.close(fig)

    print(f"\nVisualization saved to:")
    print(f"  {output_plot_path.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
