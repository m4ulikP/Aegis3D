"""
Fixed virtual PZT sensor registry loader.

The registry is generated once from the IFC model and remains stable
across simulator/demo runs.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "sensor_registry.json"
)


@dataclass(frozen=True)
class SensorDefinition:
    """Fixed identity and BIM association for a virtual sensor."""

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


class SensorRegistry:
    """Load and access the fixed virtual sensor registry."""

    def __init__(
        self,
        registry_path: Optional[Path] = None,
    ) -> None:
        self.registry_path = registry_path or REGISTRY_PATH
        self._sensors: Dict[str, SensorDefinition] = {}

        self._load()

    def _load(self) -> None:
        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"Sensor registry not found: {self.registry_path}"
            )

        with self.registry_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for raw in data["sensors"]:
            sensor = SensorDefinition(
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

    @property
    def sensors(self) -> List[SensorDefinition]:
        return list(self._sensors.values())

    @property
    def sensor_count(self) -> int:
        return len(self._sensors)

    def get_sensor(
        self,
        sensor_id: str,
    ) -> Optional[SensorDefinition]:
        return self._sensors.get(sensor_id)

    def get_sensors_by_storey(
        self,
        storey: str,
    ) -> List[SensorDefinition]:
        return [
            sensor
            for sensor in self._sensors.values()
            if sensor.storey == storey
        ]