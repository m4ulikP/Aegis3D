"""
End-to-end diagnostic test of the Aegis3D physics-inspired PZT simulator.

This test:

1. Loads a real BIM-derived propagation path.
2. Generates a deterministic PZT tone burst.
3. Propagates it through the healthy structural model.
4. Propagates it through the damaged structural model.
5. Applies the receiver/acquisition stage.
6. Sends both signals to the existing Aegis3D backend.
7. Uses the backend's normal detection threshold.
8. Compares the backend's downstream processing results.

IMPORTANT:

- The backend is not modified.
- No simulator-specific anomaly information is sent to the backend.
- No detection_threshold override is sent.
- The simulator only sends raw telemetry samples.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ------------------------------------------------------------------
# Project paths
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------------------
# Simulator imports
# ------------------------------------------------------------------

from simulator.physics import (
    DamageModel,
    PropagationPath,
    ReceiverAcquisition,
)
from simulator.signal_generator import generate_pzt_tone_burst


# ------------------------------------------------------------------
# Backend configuration
# ------------------------------------------------------------------

BACKEND_URL = "http://127.0.0.1:8000"

TELEMETRY_ENDPOINT = (
    f"{BACKEND_URL}/api/v1/telemetry"
)


# ------------------------------------------------------------------
# BIM propagation network
# ------------------------------------------------------------------

NETWORK_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "propagation_network.json"
)


# ------------------------------------------------------------------
# Test configuration
# ------------------------------------------------------------------

# PATH-007 was already validated by the damage propagation test.
PATH_ID = "PATH-007"

# Real BIM/IFC component selected as damaged.
DAMAGED_COMPONENT_GUID = (
    "1WrzGm1SD2ev45B_OWQ3El"
)

# The canonical sensor for Zone 2 (Substructure Pier B).
BACKEND_SENSOR_ID = "PZT-Z07"

BACKEND_ZONE_NAME = (
    "Zone 2 - Substructure Pier B"
)

# PZT excitation parameters.
SAMPLE_RATE_HZ = 100_000.0
SAMPLE_COUNT = 10_000
FREQUENCY_HZ = 10_000.0

# Receiver/acquisition stage.
#
# This is the simulator-side scaling that represents the receiving
# and acquisition chain after structural propagation.
RECEIVER_GAIN = 5.0


# ------------------------------------------------------------------
# Load propagation path
# ------------------------------------------------------------------

def load_path(
    path_id: str,
) -> PropagationPath:
    """Load one propagation path from the generated BIM network."""

    with NETWORK_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        network = json.load(f)

    for raw_path in network["paths"]:
        if raw_path["path_id"] != path_id:
            continue

        return PropagationPath(
            actuator_id=raw_path["actuator_id"],
            receiver_id=raw_path["receiver_id"],
            component_guids=tuple(
                raw_path["component_guids"]
            ),
            distance_m=float(
                raw_path["distance_m"]
            ),
            wave_velocity_m_s=float(
                raw_path["wave_velocity_m_s"]
            ),
            attenuation_db_per_m=float(
                raw_path["attenuation_db_per_m"]
            ),
        )

    raise ValueError(
        f"Propagation path not found: {path_id}"
    )


# ------------------------------------------------------------------
# Load component influence metadata
# ------------------------------------------------------------------

def get_damage_influences(
    path_id: str,
) -> list[dict]:
    """
    Load component influence metadata for a propagation path.
    """

    with NETWORK_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        network = json.load(f)

    for raw_path in network["paths"]:
        if raw_path["path_id"] == path_id:
            return raw_path.get(
                "component_influences",
                [],
            )

    raise ValueError(
        f"Propagation path not found: {path_id}"
    )


# ------------------------------------------------------------------
# Build backend telemetry payload
# ------------------------------------------------------------------

def build_payload(
    sensor_id: str,
    zone_name: str,
    samples: list[float],
    sequence: int,
) -> dict:
    """
    Build the existing Aegis3D telemetry contract.

    No detection_threshold is supplied.

    This means the existing backend calculates its own threshold
    using its normal baseline logic.
    """

    return {
        "sensor_id": sensor_id,
        "zone_name": zone_name,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "sequence": sequence,
        "samples": samples,
    }


# ------------------------------------------------------------------
# Send telemetry
# ------------------------------------------------------------------

def send_telemetry(
    payload: dict,
) -> dict:
    """
    Send telemetry to the real Aegis3D backend.

    Uses Python's standard library so the test does not require
    an additional requests dependency.
    """

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        TELEMETRY_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:

            response_body = (
                response
                .read()
                .decode("utf-8")
            )

            return json.loads(
                response_body
            )

    except urllib.error.HTTPError as error:

        error_body = (
            error
            .read()
            .decode("utf-8")
        )

        print()
        print("=" * 60)
        print("BACKEND ERROR")
        print("=" * 60)
        print(
            f"HTTP status: {error.code}"
        )
        print(error_body)

        raise


# ------------------------------------------------------------------
# Print backend result
# ------------------------------------------------------------------

def print_result(
    label: str,
    result: dict,
) -> None:
    """Print important fields from a backend response."""

    print()
    print("=" * 60)
    print(label)
    print("=" * 60)

    fields = [
        "status",
        "telemetry_accepted",
        "sensor_id",
        "zone_id",
        "zone_name",
        "samples_count",
        "sample_rate_hz",
        "sequence",
        "events_detected",
        "temporal_persistence_confirmed",
        "cross_sensor_correlation_confirmed",
        "health_score",
        "health_status",
        "health_trend",
        "alert_generated",
        "alert_id",
        "alert_severity",
        "alert_title",
        "message",
    ]

    for field in fields:
        print(
            f"{field}: "
            f"{result.get(field)}"
        )

    # --------------------------------------------------------------
    # Events
    # --------------------------------------------------------------

    events = result.get(
        "events",
        [],
    )

    if events:
        print()
        print("Events:")

        for event in events:
            print(
                json.dumps(
                    event,
                    indent=2,
                )
            )

    # --------------------------------------------------------------
    # Extracted features
    # --------------------------------------------------------------

    features = result.get(
        "extracted_features"
    )

    if features:
        print()
        print(
            "Extracted features:"
        )

        print(
            json.dumps(
                features,
                indent=2,
            )
        )


# ------------------------------------------------------------------
# Main test
# ------------------------------------------------------------------

def main() -> None:

    print(
        "Aegis3D damage telemetry diagnostic test"
    )

    print(
        "-" * 60
    )

    print(
        "Detection threshold: "
        "BACKEND DEFAULT"
    )

    print(
        "Receiver gain: "
        f"{RECEIVER_GAIN:.1f}x"
    )

    print(
        "No detection_threshold override "
        "will be sent."
    )

    # --------------------------------------------------------------
    # Load BIM-derived propagation path
    # --------------------------------------------------------------

    path = load_path(
        PATH_ID
    )

    influences = (
        get_damage_influences(
            PATH_ID
        )
    )

    print()
    print(
        path.describe()
    )

    print(
        f"Damaged component: "
        f"{DAMAGED_COMPONENT_GUID}"
    )

    print(
        f"Simulator path: "
        f"{path.actuator_id} -> "
        f"{path.receiver_id}"
    )

    print(
        f"Backend sensor identity: "
        f"{BACKEND_SENSOR_ID}"
    )

    print(
        f"Backend zone: "
        f"{BACKEND_ZONE_NAME}"
    )

    # --------------------------------------------------------------
    # Receiver/acquisition stage
    # --------------------------------------------------------------

    receiver = ReceiverAcquisition(
        gain=RECEIVER_GAIN
    )

    # --------------------------------------------------------------
    # 1. Generate PZT actuator excitation
    # --------------------------------------------------------------

    excitation = (
        generate_pzt_tone_burst(
            sample_count=SAMPLE_COUNT,
            sample_rate_hz=SAMPLE_RATE_HZ,
            frequency_hz=FREQUENCY_HZ,
            amplitude=0.8,
            cycles=5,
        )
    )

    print()
    print(
        f"Excitation: "
        f"{len(excitation)} samples @ "
        f"{SAMPLE_RATE_HZ:.0f} Hz"
    )

    # --------------------------------------------------------------
    # 2. Healthy structural propagation
    # --------------------------------------------------------------

    healthy_propagated = (
        path.propagate(
            excitation,
            sample_rate_hz=SAMPLE_RATE_HZ,
        )
    )

    healthy_signal = (
        receiver.apply(
            healthy_propagated
        )
    )

    # --------------------------------------------------------------
    # 3. Damaged structural propagation
    # --------------------------------------------------------------

    damage_model = DamageModel()

    damage_model.set_damaged_component(
        DAMAGED_COMPONENT_GUID
    )

    damage_effect = (
        damage_model.get_path_effect(
            influences,
            sample_rate_hz=SAMPLE_RATE_HZ,
        )
    )

    damaged_propagated = (
        path.propagate(
            excitation,
            sample_rate_hz=SAMPLE_RATE_HZ,
            damage_effect=damage_effect,
        )
    )

    damaged_signal = (
        receiver.apply(
            damaged_propagated
        )
    )

    # --------------------------------------------------------------
    # Print physics results
    # --------------------------------------------------------------

    import numpy as np

    healthy_array = np.asarray(
        healthy_signal,
        dtype=float,
    )

    damaged_array = np.asarray(
        damaged_signal,
        dtype=float,
    )

    print()
    print(
        f"Healthy signal: "
        f"{len(healthy_signal)} samples"
    )

    print(
        f"Damaged signal: "
        f"{len(damaged_signal)} samples"
    )

    print()
    print(
        "Receiver-scaled signal peaks:"
    )

    print(
        f"  healthy peak: "
        f"{np.max(np.abs(healthy_array)):.6f}"
    )

    print(
        f"  damaged peak: "
        f"{np.max(np.abs(damaged_array)):.6f}"
    )

    print()
    print(
        "Damage effect:"
    )

    print(
        f"  attenuation multiplier: "
        f"{damage_effect.attenuation_multiplier:.4f}"
    )

    print(
        f"  delay shift: "
        f"{damage_effect.delay_shift_samples} samples"
    )

    print(
        f"  scattering amplitude: "
        f"{damage_effect.scattering_amplitude:.4f}"
    )

    print(
        f"  scattering delay: "
        f"{damage_effect.scattering_delay_samples} samples "
        f"("
        f"{damage_effect.scattering_delay_samples / SAMPLE_RATE_HZ * 1000.0:.3f}"
        f" ms)"
    )

    # --------------------------------------------------------------
    # 4. Send healthy telemetry
    # --------------------------------------------------------------

    healthy_payload = build_payload(
        sensor_id=BACKEND_SENSOR_ID,
        zone_name=BACKEND_ZONE_NAME,
        samples=healthy_signal,
        sequence=1,
    )

    print()
    print(
        "Sending HEALTHY telemetry..."
    )

    healthy_result = (
        send_telemetry(
            healthy_payload
        )
    )

    print_result(
        "HEALTHY BACKEND RESPONSE",
        healthy_result,
    )

    # --------------------------------------------------------------
    # 5. Send damaged telemetry
    # --------------------------------------------------------------

    damaged_payload = build_payload(
        sensor_id=BACKEND_SENSOR_ID,
        zone_name=BACKEND_ZONE_NAME,
        samples=damaged_signal,
        sequence=2,
    )

    print()
    print(
        "Sending DAMAGED telemetry..."
    )

    damaged_result = (
        send_telemetry(
            damaged_payload
        )
    )

    print_result(
        "DAMAGED BACKEND RESPONSE",
        damaged_result,
    )

    # --------------------------------------------------------------
    # 6. Compare results
    # --------------------------------------------------------------

    print()
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)

    print()

    print(
        "Healthy status :",
        healthy_result.get(
            "status"
        ),
    )

    print(
        "Damaged status :",
        damaged_result.get(
            "status"
        ),
    )

    print()

    print(
        "Healthy events :",
        healthy_result.get(
            "events_detected"
        ),
    )

    print(
        "Damaged events :",
        damaged_result.get(
            "events_detected"
        ),
    )

    print()

    print(
        "Healthy health score :",
        healthy_result.get(
            "health_score"
        ),
    )

    print(
        "Damaged health score :",
        damaged_result.get(
            "health_score"
        ),
    )

    print()

    print(
        "Healthy health status :",
        healthy_result.get(
            "health_status"
        ),
    )

    print(
        "Damaged health status :",
        damaged_result.get(
            "health_status"
        ),
    )

    print()

    print(
        "Healthy alert generated :",
        healthy_result.get(
            "alert_generated"
        ),
    )

    print(
        "Damaged alert generated :",
        damaged_result.get(
            "alert_generated"
        ),
    )


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    main()