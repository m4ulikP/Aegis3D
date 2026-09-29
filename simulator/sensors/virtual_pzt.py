"""
Virtual PZT sensor abstraction for the Aegis3D simulator.

The virtual sensor provides:
- Normal/healthy telemetry
- Transient and anomaly test signals
- Physics-inspired PZT tone-burst excitation
- Propagation of the excitation through a structural path
- Receiver/acquisition scaling of propagated signals

The simulator is a software replacement for the eventual PZT/ESP32
sensing layer. It is not an experimentally calibrated hardware model.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

try:
    from simulator.config import (
        DEFAULT_SENSOR_ZONE_MAP,
        ZONE_MAIN_DECK,
    )
    from simulator.physics import (
        DamageModel,
        PropagationPath,
        ReceiverAcquisition,
    )
    from simulator.signal_generator import (
        generate_anomaly_signal,
        generate_normal_signal,
        generate_pzt_tone_burst,
        generate_transient_signal,
    )
except ImportError:
    from config import (
        DEFAULT_SENSOR_ZONE_MAP,
        ZONE_MAIN_DECK,
    )
    from physics import (
        DamageModel,
        PropagationPath,
        ReceiverAcquisition,
    )
    from signal_generator import (
        generate_anomaly_signal,
        generate_normal_signal,
        generate_pzt_tone_burst,
        generate_transient_signal,
    )


class VirtualPZTSensor:
    """
    Software representation of a PZT sensor.

    The sensor itself does not perform backend anomaly detection.
    It generates representative telemetry that can be sent through
    the existing Aegis3D telemetry pipeline.
    """

    def __init__(
        self,
        sensor_id: str,
        zone_name: Optional[str] = None,
        sample_rate_hz: float = 1000.0,
        initial_sequence: int = 0,
    ) -> None:
        if not sensor_id:
            raise ValueError("sensor_id cannot be empty")

        if sample_rate_hz <= 0:
            raise ValueError(
                f"sample_rate_hz must be positive, got {sample_rate_hz}"
            )

        if initial_sequence < 0:
            raise ValueError("initial_sequence cannot be negative")

        self.sensor_id = sensor_id

        self.zone_name = (
            zone_name
            or DEFAULT_SENSOR_ZONE_MAP.get(sensor_id)
            or ZONE_MAIN_DECK
        )

        self.sample_rate_hz = sample_rate_hz
        self.sequence = initial_sequence

        # Receiver/acquisition stage.
        #
        # PropagationPath models the structural propagation itself.
        # ReceiverAcquisition models the scaling introduced by the
        # receiving/acquisition chain before telemetry is produced.
        #
        # The value is intentionally a simulator parameter rather than
        # a claim about calibrated PZT/ESP32 hardware gain.
        self.receiver = ReceiverAcquisition(gain=5.0)

    def _next_sequence(self) -> int:
        sequence = self.sequence
        self.sequence += 1
        return sequence

    def generate_healthy_signal(
        self,
        sample_count: int = 1000,
        seed: Optional[int] = 42,
    ) -> List[float]:
        """
        Generate a deterministic healthy structural baseline signal.
        """
        return generate_normal_signal(
            sample_count=sample_count,
            sample_rate_hz=self.sample_rate_hz,
            seed=seed,
        )

    def generate_propagated_signal(
        self,
        path: PropagationPath,
        sample_count: int = 10000,
        sample_rate_hz: float = 100000.0,
        seed: Optional[int] = 42,
        damage_effect: Optional[object] = None,
    ) -> List[float]:
        """
        Generate a PZT tone-burst excitation and propagate it through
        a reduced-order structural path.

        The resulting signal represents what the receiving PZT would
        observe after:

            1. PZT excitation
            2. Structural propagation
            3. Propagation delay
            4. Distance-dependent attenuation
            5. Discontinuity scattering (if damage active)
            6. Receiver/acquisition scaling

        This is a physics-inspired simulation, not an experimentally
        calibrated structural model.
        """

        # Generate the actuator excitation.
        source_signal = generate_pzt_tone_burst(
            sample_count=sample_count,
            sample_rate_hz=sample_rate_hz,
            frequency_hz=10_000.0,
            amplitude=0.8,
            cycles=5,
        )

        # Propagate the excitation through the structural path.
        propagated_signal = path.propagate(
            source_signal,
            sample_rate_hz=sample_rate_hz,
            damage_effect=damage_effect,
        )

        # Model the receiving/acquisition stage after structural
        # propagation. The backend receives this scaled signal.
        received_signal = self.receiver.apply(
            propagated_signal,
        )

        return received_signal

    def generate_payload(
        self,
        mode: str = "normal",
        sample_count: int = 1000,
        seed: Optional[int] = 42,
        threshold: Optional[float] = None,
        detection_threshold: Optional[float] = None,
        session_id: Optional[Any] = None,
        samples: Optional[List[float]] = None,
        timestamp: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate a telemetry payload compatible with the existing
        Aegis3D telemetry endpoint.

        Supported modes:
            normal / healthy
            transient / event
            anomaly
        """

        mode = mode.lower().strip()

        if samples is not None:
            signal_samples = [float(x) for x in samples]
        else:
            if sample_count <= 0:
                raise ValueError(
                    f"sample_count must be positive, got {sample_count}"
                )

            if mode in {"normal", "healthy"}:
                signal_samples = self.generate_healthy_signal(
                    sample_count=sample_count,
                    seed=seed,
                )

            elif mode in {"transient", "event"}:
                signal_samples = generate_transient_signal(
                    sample_count=sample_count,
                    sample_rate_hz=self.sample_rate_hz,
                    seed=seed,
                )

            elif mode == "anomaly":
                signal_samples = generate_anomaly_signal(
                    sample_count=sample_count,
                    sample_rate_hz=self.sample_rate_hz,
                    seed=seed,
                )

            else:
                raise ValueError(
                    f"Unsupported signal mode: {mode!r}. "
                    "Expected normal, healthy, transient, event, or anomaly."
                )

        # Ensure all values are finite before they reach the backend.
        if not all(math.isfinite(float(value)) for value in signal_samples):
            raise ValueError(
                "Generated signal contains non-finite values"
            )

        if timestamp is not None:
            if isinstance(timestamp, datetime):
                ts_str = timestamp.isoformat()
            else:
                ts_str = str(timestamp)
        else:
            ts_str = datetime.now(timezone.utc).isoformat()

        payload: Dict[str, Any] = {
            "sensor_id": self.sensor_id,
            "zone_name": self.zone_name,
            "sample_rate_hz": self.sample_rate_hz,
            "samples": signal_samples,
            "timestamp": ts_str,
            "sequence": self._next_sequence(),
        }

        # Threshold handling
        effective_threshold = detection_threshold if detection_threshold is not None else threshold
        if effective_threshold is not None:
            payload["detection_threshold"] = float(effective_threshold)

        if session_id is not None:
            payload["session_id"] = session_id

        return payload

    def generate_physics_payload(
        self,
        mode: str = "normal",
        path: Optional[PropagationPath] = None,
        damaged_component_guid: Optional[str] = None,
        sample_count: int = 10000,
        sample_rate_hz: float = 100000.0,
        seed: Optional[int] = 42,
        session_id: Optional[Any] = None,
        timestamp: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate a physics-driven telemetry payload using a BIM propagation path.

        Applies:
        - Hann-windowed PZT tone burst excitation
        - Structural propagation delay and distance attenuation
        - Discontinuity/damage interaction & localized scattering (if mode == 'anomaly')
        - Receiver/acquisition scaling
        """
        import json
        from pathlib import Path

        mode = mode.lower().strip()
        damage_effect = None

        if path is None:
            # Locate default path from propagation network
            network_file = Path(__file__).resolve().parents[2] / "data" / "processed" / "bim" / "propagation_network.json"
            if network_file.exists():
                with open(network_file, "r", encoding="utf-8") as f:
                    net_data = json.load(f)
                matched_raw = None
                for p in net_data.get("paths", []):
                    if p["path_id"] == "PATH-007" and (self.sensor_id in [p["actuator_id"], p["receiver_id"], "PZT-Z01"]):
                        matched_raw = p
                        break
                if matched_raw is None:
                    for p in net_data.get("paths", []):
                        if p["actuator_id"] == self.sensor_id or p["receiver_id"] == self.sensor_id:
                            matched_raw = p
                            break
                if matched_raw is None and net_data.get("paths"):
                    matched_raw = net_data["paths"][0]

                if matched_raw:
                    path = PropagationPath(
                        actuator_id=matched_raw["actuator_id"],
                        receiver_id=matched_raw["receiver_id"],
                        component_guids=tuple(matched_raw["component_guids"]),
                        distance_m=float(matched_raw["distance_m"]),
                        wave_velocity_m_s=float(matched_raw["wave_velocity_m_s"]),
                        attenuation_db_per_m=float(matched_raw["attenuation_db_per_m"]),
                    )
                    influences = matched_raw.get("component_influences", [])
                    if mode in {"anomaly", "damaged"}:
                        dm = DamageModel()
                        dm.set_damaged_component(damaged_component_guid or "1WrzGm1SD2ev45B_OWQ3El")
                        damage_effect = dm.get_path_effect(influences, sample_rate_hz=sample_rate_hz)

        if path is None:
            # Fallback path if network json not found
            path = PropagationPath(
                actuator_id="PZT-Z04",
                receiver_id=self.sensor_id,
                component_guids=("fallback_guid",),
                distance_m=16.30,
                wave_velocity_m_s=3200.0,
                attenuation_db_per_m=0.8,
            )

        signal_samples = self.generate_propagated_signal(
            path=path,
            sample_count=sample_count,
            sample_rate_hz=sample_rate_hz,
            seed=seed,
            damage_effect=damage_effect,
        )

        if timestamp is not None:
            if isinstance(timestamp, datetime):
                ts_str = timestamp.isoformat()
            else:
                ts_str = str(timestamp)
        else:
            ts_str = datetime.now(timezone.utc).isoformat()

        payload: Dict[str, Any] = {
            "sensor_id": self.sensor_id,
            "zone_name": self.zone_name,
            "sample_rate_hz": sample_rate_hz,
            "samples": signal_samples,
            "timestamp": ts_str,
            "sequence": self._next_sequence(),
        }

        if session_id is not None:
            payload["session_id"] = session_id

        return payload