"""Canonical BIM Sensor Registry service for Aegis3D.

Loads and exposes the authoritative virtual PZT sensor definitions generated
from the IFC structural model (data/processed/bim/sensor_registry.json).
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Repository root is 3 levels up from backend/app/services/
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "processed" / "bim" / "sensor_registry.json"


@dataclass(frozen=True)
class CanonicalSensorMetadata:
    """Authoritative metadata for a canonical BIM sensor."""

    sensor_id: str
    component_guid: str
    component_type: str
    component_name: str
    storey: str
    position: Tuple[float, float, float]
    role: str
    status: str
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None


class SensorRegistryService:
    """Authoritative canonical sensor registry service."""

    _instance: Optional["SensorRegistryService"] = None

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self._sensors: Dict[str, CanonicalSensorMetadata] = {}
        self._load()

    def _load(self) -> None:
        if not self.registry_path.exists():
            logger.warning(
                "Canonical sensor registry file not found at %s", self.registry_path
            )
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for raw in data.get("sensors", []):
                sensor = CanonicalSensorMetadata(
                    sensor_id=raw["sensor_id"],
                    component_guid=raw["component_guid"],
                    component_type=raw["component_type"],
                    component_name=raw["component_name"],
                    storey=raw["storey"],
                    position=tuple(raw["position"]),
                    role=raw["role"],
                    status=raw["status"],
                    zone_id=raw.get("zone_id"),
                    zone_name=raw.get("zone_name"),
                )
                self._sensors[sensor.sensor_id] = sensor

            logger.info(
                "Loaded %d canonical sensors from %s", len(self._sensors), self.registry_path
            )
        except Exception as exc:
            logger.error("Failed to load canonical sensor registry: %s", exc)

    def get_sensor(self, sensor_id: str) -> Optional[CanonicalSensorMetadata]:
        """Look up canonical sensor metadata by exact sensor identifier."""
        return self._sensors.get(sensor_id)

    def is_canonical(self, sensor_id: str) -> bool:
        """Check if a sensor identifier belongs to the canonical registry."""
        return sensor_id in self._sensors

    def get_all_sensors(self) -> List[CanonicalSensorMetadata]:
        """Return all registered canonical sensors."""
        return list(self._sensors.values())

    def get_sensors_for_zone(self, zone_id: int) -> List[CanonicalSensorMetadata]:
        """Return all canonical sensors assigned to a specific zone."""
        return [s for s in self._sensors.values() if s.zone_id == zone_id]


# Global singleton instance for backend services
_registry_instance: Optional[SensorRegistryService] = None


def get_sensor_registry() -> SensorRegistryService:
    """Return the global SensorRegistryService singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SensorRegistryService()
    return _registry_instance
