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
    ) -> None:
        if not sensor_id:
            raise ValueError("sensor_id cannot be empty")

        if sample_rate_hz <= 0:
            raise ValueError(
                f"sample_rate_hz must be positive, got {sample_rate_hz}"
            )

        self.sensor_id = sensor_id

        self.zone_name = (
            zone_name
            or DEFAULT_SENSOR_ZONE_MAP.get(sensor_id)
            or ZONE_MAIN_DECK
        )

        self.sample_rate_hz = sample_rate_hz
        self.sequence = 0

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
            5. Receiver/acquisition scaling

        This is a physics-inspired simulation, not an experimentally
        calibrated structural model.
        """

        # Generate the actuator excitation.
        #
        # The current internal physics simulation uses:
        #   - 100 kHz sampling
        #   - 10 kHz carrier
        #   - 5-cycle tone burst
        #   - amplitude = 0.8
        #
        # This is intentionally separate from the existing 1 kHz
        # backend telemetry generator.
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
        session_id: Optional[str] = None,
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

        if sample_count <= 0:
            raise ValueError(
                f"sample_count must be positive, got {sample_count}"
            )

        if mode in {"normal", "healthy"}:
            samples = self.generate_healthy_signal(
                sample_count=sample_count,
                seed=seed,
            )

        elif mode in {"transient", "event"}:
            samples = generate_transient_signal(
                sample_count=sample_count,
                sample_rate_hz=self.sample_rate_hz,
                seed=seed,
            )

        elif mode == "anomaly":
            samples = generate_anomaly_signal(
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
        if not all(math.isfinite(float(value)) for value in samples):
            raise ValueError(
                "Generated signal contains non-finite values"
            )

        payload: Dict[str, Any] = {
            "sensor_id": self.sensor_id,
            "zone_name": self.zone_name,
            "sample_rate_hz": self.sample_rate_hz,
            "samples": samples,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": self._next_sequence(),
        }

        if threshold is not None:
            payload["threshold"] = float(threshold)

        if session_id is not None:
            payload["session_id"] = session_id

        return payload