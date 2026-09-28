"""Virtual PZT Sensor abstraction for software-first structural telemetry simulation."""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

try:
    from simulator.config import DEFAULT_SENSOR_ZONE_MAP, ZONE_MAIN_DECK
    from simulator.signal_generator import (
        generate_anomaly_signal,
        generate_normal_signal,
        generate_transient_signal,
    )
except ImportError:
    from config import DEFAULT_SENSOR_ZONE_MAP, ZONE_MAIN_DECK
    from signal_generator import (
        generate_anomaly_signal,
        generate_normal_signal,
        generate_transient_signal,
    )


class VirtualPZTSensor:
    """
    Simulated Piezoelectric Transducer (PZT) sensor node.

    Maintains:
    - Stable sensor identifier (e.g. 'PZT-Z1-01')
    - Target domain zone name (e.g. 'Zone 1 - Main Deck Girder')
    - Sampling rate in Hertz
    - Monotonically increasing packet sequence counter
    """

    def __init__(
        self,
        sensor_id: str = "PZT-Z1-01",
        zone_name: Optional[str] = None,
        sample_rate_hz: float = 1000.0,
        initial_sequence: int = 1,
    ) -> None:
        if not sensor_id or not sensor_id.strip():
            raise ValueError("sensor_id cannot be empty")
        if sample_rate_hz <= 0:
            raise ValueError(f"sample_rate_hz must be positive, got {sample_rate_hz}")
        if initial_sequence < 0:
            raise ValueError(f"initial_sequence cannot be negative, got {initial_sequence}")

        self.sensor_id = sensor_id.strip()
        # Auto-infer zone from default mapping if not explicitly provided
        if zone_name and zone_name.strip():
            self.zone_name = zone_name.strip()
        else:
            self.zone_name = DEFAULT_SENSOR_ZONE_MAP.get(self.sensor_id, ZONE_MAIN_DECK)

        self.sample_rate_hz = float(sample_rate_hz)
        self.sequence = int(initial_sequence)

    def generate_payload(
        self,
        mode: str = "normal",
        sample_count: int = 1000,
        seed: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        samples: Optional[List[float]] = None,
        detection_threshold: Optional[float] = None,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a telemetry dictionary payload adhering strictly to backend TelemetryIngestRequest.

        The simulator sends ONLY signal samples and metadata.
        It does NOT specify event flags, anomaly decisions, health scores, or alerts.

        Args:
            mode: Signal generation mode ('normal', 'transient', 'anomaly').
            sample_count: Number of discrete samples to generate if custom samples not provided.
            seed: Optional RNG seed for deterministic reproduction.
            timestamp: UTC datetime; defaults to datetime.now(timezone.utc).
            samples: Pre-generated sample array override (useful for coordinated multi-sensor tests).
            detection_threshold: Optional amplitude detection threshold override.
            session_id: Optional monitoring session ID override.

        Returns:
            Dict conforming strictly to backend TelemetryIngestRequest schema.
        """
        # Determine sample values
        if samples is not None:
            raw_samples = list(samples)
        elif mode.lower() == "normal":
            raw_samples = generate_normal_signal(
                sample_count=sample_count,
                sample_rate_hz=self.sample_rate_hz,
                seed=seed,
            )
        elif mode.lower() in ("transient", "event"):
            raw_samples = generate_transient_signal(
                sample_count=sample_count,
                sample_rate_hz=self.sample_rate_hz,
                seed=seed,
            )
        elif mode.lower() == "anomaly":
            raw_samples = generate_anomaly_signal(
                sample_count=sample_count,
                sample_rate_hz=self.sample_rate_hz,
                seed=seed,
            )
        else:
            raise ValueError(f"Unsupported signal mode '{mode}'. Choose 'normal', 'transient', or 'anomaly'.")

        # Validate finite values
        for idx, val in enumerate(raw_samples):
            if val is None or math.isnan(val) or math.isinf(val):
                raise ValueError(f"Sample at index {idx} is non-finite: {val}")

        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        seq = self.sequence
        self.sequence += 1

        payload: Dict[str, Any] = {
            "sensor_id": self.sensor_id,
            "zone_name": self.zone_name,
            "timestamp": ts.isoformat(),
            "sample_rate_hz": self.sample_rate_hz,
            "sequence": seq,
            "samples": raw_samples,
        }

        if detection_threshold is not None:
            payload["detection_threshold"] = float(detection_threshold)

        if session_id is not None:
            payload["session_id"] = int(session_id)

        return payload
