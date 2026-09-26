from typing import List
import numpy as np

from app.processing.types import DetectedWindow, SampledSignal


def detect_events(
    signal: SampledSignal,
    threshold: float,
    min_duration_samples: int = 1,
    merge_gap_samples: int = 0,
) -> List[DetectedWindow]:
    """Detects active signal event windows where signal amplitude exceeds threshold.

    Note:
        Detected event windows represent regions of physical/simulated signal activity.
        They do not classify structural failure or safety conditions.

    Args:
        signal (SampledSignal): Input sampled signal.
        threshold (float): Absolute amplitude threshold (> 0).
        min_duration_samples (int): Minimum required duration in samples (>= 1).
        merge_gap_samples (int): Maximum gap in samples between active regions to merge (>= 0).

    Returns:
        List[DetectedWindow]: List of detected event windows.
    """
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold}")

    if min_duration_samples < 1:
        raise ValueError(f"min_duration_samples must be >= 1, got {min_duration_samples}")

    if merge_gap_samples < 0:
        raise ValueError(f"merge_gap_samples cannot be negative, got {merge_gap_samples}")

    abs_samples = np.abs(signal.samples)
    above_threshold = abs_samples >= threshold

    if not np.any(above_threshold):
        return []

    # Identify contiguous active indices
    active_indices = np.where(above_threshold)[0]
    if len(active_indices) == 0:
        return []

    raw_windows = []
    win_start = active_indices[0]
    win_end = active_indices[0]

    for idx in active_indices[1:]:
        if idx == win_end + 1:
            win_end = idx
        else:
            raw_windows.append((win_start, win_end))
            win_start = idx
            win_end = idx
    raw_windows.append((win_start, win_end))

    # Merge windows separated by <= merge_gap_samples
    merged_windows = []
    if raw_windows:
        curr_start, curr_end = raw_windows[0]
        for next_start, next_end in raw_windows[1:]:
            if next_start - curr_end - 1 <= merge_gap_samples:
                curr_end = next_end
            else:
                merged_windows.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_windows.append((curr_start, curr_end))

    dt_ms = 1000.0 / signal.sample_rate_hz
    detected_windows: List[DetectedWindow] = []

    for start_idx, end_idx in merged_windows:
        sample_cnt = end_idx - start_idx + 1
        if sample_cnt < min_duration_samples:
            continue

        win_samples = signal.samples[start_idx : end_idx + 1]
        peak_amp = float(np.max(np.abs(win_samples)))
        rms_amp = float(np.sqrt(np.mean(win_samples**2)))
        start_t_ms = start_idx * dt_ms
        end_t_ms = (end_idx + 1) * dt_ms
        duration_ms = sample_cnt * dt_ms

        detected_windows.append(
            DetectedWindow(
                start_index=start_idx,
                end_index=end_idx,
                start_time_ms=start_t_ms,
                end_time_ms=end_t_ms,
                duration_ms=duration_ms,
                peak_amplitude=peak_amp,
                rms_amplitude=rms_amp,
                sample_count=sample_cnt,
            )
        )

    return detected_windows
