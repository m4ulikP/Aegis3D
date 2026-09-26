from typing import List, Optional

from app.processing.event_detection import detect_events
from app.processing.feature_extraction import extract_features
from app.processing.filters import lowpass_filter, moving_average_filter
from app.processing.preprocessing import normalize_amplitude, remove_dc_offset
from app.processing.types import DetectedWindow, ProcessedEvent, SampledSignal


def process_signal_pipeline(
    signal: SampledSignal,
    detection_threshold: float,
    remove_dc: bool = True,
    filter_window_size: Optional[int] = None,
    min_duration_samples: int = 1,
    merge_gap_samples: int = 0,
) -> List[ProcessedEvent]:
    """Executes the end-to-end signal processing pipeline on a SampledSignal.

    Flow: raw signal -> preprocessing -> filtering -> event detection -> feature extraction

    Args:
        signal (SampledSignal): Input sampled signal.
        detection_threshold (float): Event detection amplitude threshold (> 0).
        remove_dc (bool): Whether to subtract DC mean offset.
        filter_window_size (Optional[int]): Optional moving average smoothing window size.
        min_duration_samples (int): Minimum required event duration in samples.
        merge_gap_samples (int): Gap size in samples to merge adjacent event windows.

    Returns:
        List[ProcessedEvent]: List of extracted processed events.
    """
    proc_signal = signal
    if remove_dc:
        proc_signal = remove_dc_offset(proc_signal)

    if filter_window_size is not None and filter_window_size >= 1:
        proc_signal = moving_average_filter(proc_signal, window_size=filter_window_size)

    windows = detect_events(
        proc_signal,
        threshold=detection_threshold,
        min_duration_samples=min_duration_samples,
        merge_gap_samples=merge_gap_samples,
    )

    processed_events: List[ProcessedEvent] = []
    for win in windows:
        p_event = extract_features(proc_signal, win)
        processed_events.append(p_event)

    return processed_events


__all__ = [
    "SampledSignal",
    "DetectedWindow",
    "ProcessedEvent",
    "remove_dc_offset",
    "normalize_amplitude",
    "moving_average_filter",
    "lowpass_filter",
    "detect_events",
    "extract_features",
    "process_signal_pipeline",
]
