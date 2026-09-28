"""
Diagnostic test for reduced-order damage propagation.

This test verifies that selecting a damaged IFC component changes
the propagated waveform along a path that intersects that component.

It does not contact the backend. It only validates the simulator-side
physics model.
"""

import sys
from pathlib import Path

import numpy as np

# Ensure the project root is importable when this script is executed
# directly from scripts/data/.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator.physics import DamageModel, PropagationPath
from simulator.signal_generator import generate_pzt_tone_burst


PATH_ID = "PATH-007"

ACTUATOR_ID = "PZT-Z04"
RECEIVER_ID = "PZT-Z05"

DISTANCE_M = 16.30
WAVE_VELOCITY_M_S = 3200.0
ATTENUATION_DB_PER_M = 0.8

SAMPLE_RATE_HZ = 100_000.0
SAMPLE_COUNT = 10_000

DAMAGED_COMPONENT_GUID = "1WrzGm1SD2ev45B_OWQ3El"

COMPONENT_GUIDS = (
    "18YHwga450Mw4Fy6M5t_8h",
    "1WrzGm1SD2ev45B_OWQ3El",
    "01U2Ox69TF78CjGAzXHDlb",
    "1WrzGm1SD2ev45B_OWQ3Eg",
    "2UD3D7uxP8kecbbBCRtzBI",
)

COMPONENT_INFLUENCES = [
    {
        "ifc_guid": "18YHwga450Mw4Fy6M5t_8h",
        "distance_to_path_m": 0.0,
        "influence_factor": 1.0,
    },
    {
        "ifc_guid": "1WrzGm1SD2ev45B_OWQ3El",
        "distance_to_path_m": 0.487,
        "influence_factor": 0.6958,
    },
    {
        "ifc_guid": "01U2Ox69TF78CjGAzXHDlb",
        "distance_to_path_m": 1.374,
        "influence_factor": 0.0840,
    },
    {
        "ifc_guid": "1WrzGm1SD2ev45B_OWQ3Eg",
        "distance_to_path_m": 1.407,
        "influence_factor": 0.0620,
    },
    {
        "ifc_guid": "2UD3D7uxP8kecbbBCRtzBI",
        "distance_to_path_m": 0.0,
        "influence_factor": 1.0,
    },
]


def build_path() -> PropagationPath:
    """Construct the fixed PATH-007 propagation path."""

    return PropagationPath(
        actuator_id=ACTUATOR_ID,
        receiver_id=RECEIVER_ID,
        component_guids=COMPONENT_GUIDS,
        distance_m=DISTANCE_M,
        wave_velocity_m_s=WAVE_VELOCITY_M_S,
        attenuation_db_per_m=ATTENUATION_DB_PER_M,
    )


def main() -> None:
    path = build_path()

    source_signal = generate_pzt_tone_burst(
        sample_count=SAMPLE_COUNT,
        sample_rate_hz=SAMPLE_RATE_HZ,
        frequency_hz=10_000.0,
        amplitude=0.8,
        cycles=5,
    )

    # ---------------------------------------------------------
    # Healthy propagation
    # ---------------------------------------------------------

    healthy_signal = np.asarray(
        path.propagate(
            source_signal,
            sample_rate_hz=SAMPLE_RATE_HZ,
        ),
        dtype=float,
    )

    # ---------------------------------------------------------
    # Damaged propagation
    # ---------------------------------------------------------

    damage_model = DamageModel()

    damage_model.set_damaged_component(
        DAMAGED_COMPONENT_GUID
    )

    effect = damage_model.get_path_effect(
        COMPONENT_INFLUENCES,
        sample_rate_hz=SAMPLE_RATE_HZ,
    )

    damaged_signal = np.asarray(
        path.propagate(
            source_signal,
            sample_rate_hz=SAMPLE_RATE_HZ,
            damage_effect=effect,
        ),
        dtype=float,
    )

    # ---------------------------------------------------------
    # Basic measurements
    # ---------------------------------------------------------

    healthy_peak_index = int(
        np.argmax(np.abs(healthy_signal))
    )

    damaged_peak_index = int(
        np.argmax(np.abs(damaged_signal))
    )

    healthy_peak = float(
        np.max(np.abs(healthy_signal))
    )

    damaged_peak = float(
        np.max(np.abs(damaged_signal))
    )

    print("Damage propagation test")
    print("-----------------------")
    print(f"Path: {path.actuator_id} -> {path.receiver_id}")
    print(f"Path ID: {PATH_ID}")
    print(
        f"Damaged component: "
        f"{DAMAGED_COMPONENT_GUID}"
    )

    print(
        f"Influence: "
        f"{effect.attenuation_multiplier:.4f} "
        f"attenuation multiplier"
    )

    print(
        f"Delay shift: "
        f"{effect.delay_shift_samples} samples"
    )

    print(
        f"Scattering amplitude: "
        f"{effect.scattering_amplitude:.4f}"
    )

    print(
        f"Scattering delay: "
        f"{effect.scattering_delay_samples} samples "
        f"({effect.scattering_delay_samples / SAMPLE_RATE_HZ * 1000.0:.3f} ms)"
    )

    print()
    print(
        f"Healthy peak: "
        f"{healthy_peak:.6f}"
    )

    print(
        f"Damaged peak: "
        f"{damaged_peak:.6f}"
    )

    print(
        f"Healthy peak index: "
        f"{healthy_peak_index}"
    )

    print(
        f"Damaged peak index: "
        f"{damaged_peak_index}"
    )

    print(
        f"Output lengths: "
        f"{len(healthy_signal)} / "
        f"{len(damaged_signal)}"
    )

    print()

    # ---------------------------------------------------------
    # Secondary-arrival diagnostics
    # ---------------------------------------------------------

    primary_start = int(
        round(path.propagation_delay_s * SAMPLE_RATE_HZ)
    )

    secondary_start = (
        primary_start
        + effect.delay_shift_samples
        + effect.scattering_delay_samples
    )

    secondary_end = min(
        secondary_start + len(source_signal),
        len(damaged_signal),
    )

    if secondary_start < len(damaged_signal):
        secondary_region = damaged_signal[
            secondary_start:secondary_end
        ]

        secondary_peak = float(
            np.max(np.abs(secondary_region))
        )
    else:
        secondary_peak = 0.0

    print(
        f"Primary arrival index: "
        f"{primary_start}"
    )

    print(
        f"Secondary arrival index: "
        f"{secondary_start}"
    )

    print(
        f"Secondary-region peak: "
        f"{secondary_peak:.6f}"
    )


if __name__ == "__main__":
    main()