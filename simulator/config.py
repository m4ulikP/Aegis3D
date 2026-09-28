"""Configuration settings for Aegis3D Virtual Sensor Simulator."""

import os
from dataclasses import dataclass
from typing import Dict, Optional


# Known stable structural monitoring zones in Aegis3D
ZONE_MAIN_DECK: str = "Zone 1 - Main Deck Girder"
ZONE_SUBSTRUCTURE: str = "Zone 2 - Substructure Pier B"

# Default sensor-to-zone associations conforming to backend consistency rules
DEFAULT_SENSOR_ZONE_MAP: Dict[str, str] = {
    "PZT-Z1-01": ZONE_MAIN_DECK,
    "PZT-Z1-02": ZONE_MAIN_DECK,
    "PZT-Z2-01": ZONE_SUBSTRUCTURE,
    "PZT-Z2-02": ZONE_SUBSTRUCTURE,
}


def load_env_file(filepath: str = ".env") -> None:
    """Load key-value pairs from a simple .env file into os.environ if not already set."""
    if not os.path.isfile(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


@dataclass
class SimulatorConfig:
    """Runtime configuration for virtual sensor telemetry transmission."""

    backend_url: str = "http://localhost:8000"
    telemetry_endpoint: str = "/api/v1/telemetry"
    timeout_seconds: float = 5.0
    default_sample_rate_hz: float = 1000.0
    default_sample_count: int = 1000

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "SimulatorConfig":
        """Build configuration from environment variables with optional .env file loading."""
        if env_path:
            load_env_file(env_path)
        else:
            # Check local simulator/.env or root .env
            local_env = os.path.join(os.path.dirname(__file__), ".env")
            load_env_file(local_env)

        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
        telemetry_endpoint = os.getenv("TELEMETRY_ENDPOINT", "/api/v1/telemetry")
        if not telemetry_endpoint.startswith("/"):
            telemetry_endpoint = "/" + telemetry_endpoint

        timeout_str = os.getenv("TIMEOUT_SECONDS", "5.0")
        try:
            timeout_sec = float(timeout_str)
        except ValueError:
            timeout_sec = 5.0

        sample_rate_str = os.getenv("DEFAULT_SAMPLE_RATE_HZ", "1000.0")
        try:
            sample_rate = float(sample_rate_str)
        except ValueError:
            sample_rate = 1000.0

        sample_count_str = os.getenv("DEFAULT_SAMPLE_COUNT", "1000")
        try:
            sample_count = int(sample_count_str)
        except ValueError:
            sample_count = 1000

        return cls(
            backend_url=backend_url,
            telemetry_endpoint=telemetry_endpoint,
            timeout_seconds=timeout_sec,
            default_sample_rate_hz=sample_rate,
            default_sample_count=sample_count,
        )

    @property
    def full_telemetry_url(self) -> str:
        """Construct the complete HTTP URL for telemetry ingestion."""
        return f"{self.backend_url}{self.telemetry_endpoint}"
