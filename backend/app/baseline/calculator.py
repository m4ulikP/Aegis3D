"""Hardware-agnostic pure statistical calculation engine for Aegis3D baselines."""

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np

from app.baseline.exceptions import InsufficientDataError, InvalidTimeWindowError

DEFAULT_MIN_EVENTS: int = 10


@dataclass(frozen=True)
class BaselineStatistics:
    """
    Pure numerical result of baseline statistical calculation.

    Attributes:
        mean_magnitude: Mean magnitude of qualifying historical events.
        std_magnitude: Population standard deviation of magnitude.
        mean_energy: Mean signal energy of qualifying historical events.
        std_energy: Population standard deviation of signal energy.
        normal_event_rate: Event frequency in events per second over the observation window.
        event_count: Number of qualifying events used in calculation.
        valid_from: Start of historical observation period.
        valid_until: End of historical observation period.
    """
    mean_magnitude: float
    std_magnitude: float
    mean_energy: float
    std_energy: float
    normal_event_rate: float
    event_count: int
    valid_from: datetime
    valid_until: datetime


def calculate_baseline_statistics(
    magnitudes: Sequence[float],
    energies: Sequence[float],
    valid_from: datetime,
    valid_until: datetime,
    min_events: int = DEFAULT_MIN_EVENTS,
    ddof: int = 0,
) -> BaselineStatistics:
    """
    Compute baseline statistics from event magnitude and energy values over a time window.

    Note:
        - Baseline represents normal statistical behavior for a monitoring zone over an observation period.
        - Baseline is a statistical reference, NOT a certified structural safety threshold.
        - Standard deviation uses population standard deviation by default (ddof=0).
        - For datasets with identical magnitude or energy values, std dev evaluates to 0.0.

    Args:
        magnitudes: Sequence of event magnitude physical values.
        energies: Sequence of event signal energy physical values.
        valid_from: Start of historical observation window.
        valid_until: End of historical observation window.
        min_events: Minimum qualifying events required to construct baseline (default 10).
        ddof: Delta degrees of freedom for standard deviation calculation (0 for population std dev).

    Returns:
        BaselineStatistics dataclass.

    Raises:
        InvalidTimeWindowError: If valid_until <= valid_from or duration is non-positive.
        InsufficientDataError: If qualifying event count < min_events.
        ValueError: If magnitudes and energies sequences differ in length.
    """
    if valid_until <= valid_from:
        raise InvalidTimeWindowError("valid_until must be strictly after valid_from")

    duration_seconds = (valid_until - valid_from).total_seconds()
    if duration_seconds <= 0:
        raise InvalidTimeWindowError("Observation window duration must be greater than zero seconds")

    if len(magnitudes) != len(energies):
        raise ValueError(f"Magnitudes count ({len(magnitudes)}) and energies count ({len(energies)}) must match")

    event_count = len(magnitudes)
    if event_count < min_events:
        raise InsufficientDataError(
            f"Insufficient qualifying events for baseline calculation: "
            f"found {event_count}, minimum required is {min_events}"
        )

    mag_arr = np.array(magnitudes, dtype=np.float64)
    eng_arr = np.array(energies, dtype=np.float64)

    mean_mag = float(np.mean(mag_arr))
    std_mag = float(np.std(mag_arr, ddof=ddof))
    mean_eng = float(np.mean(eng_arr))
    std_eng = float(np.std(eng_arr, ddof=ddof))

    normal_event_rate = float(event_count / duration_seconds)

    return BaselineStatistics(
        mean_magnitude=mean_mag,
        std_magnitude=std_mag,
        mean_energy=mean_eng,
        std_energy=std_eng,
        normal_event_rate=normal_event_rate,
        event_count=event_count,
        valid_from=valid_from,
        valid_until=valid_until,
    )
