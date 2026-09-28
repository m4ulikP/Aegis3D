"""
Generate the fixed reduced-order propagation network for Aegis3D.

The IFC model provides the real component identities and world-space
geometry. This script derives a deterministic sensor-to-sensor propagation
network from that geometry.

This is a simulation abstraction, not an IFC connectivity graph.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "sensor_registry.json"
)

GEOMETRY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "structural_geometry.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "propagation_network.json"
)


WAVE_VELOCITY_M_S = 3200.0
ATTENUATION_DB_PER_M = 0.8

# Number of nearest structural sensor links generated per sensor.
NEIGHBORS_PER_SENSOR = 2


def distance(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> float:
    """Euclidean distance between two 3D points."""
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    registry = load_json(REGISTRY_PATH)
    geometry = load_json(GEOMETRY_PATH)

    sensors = registry["sensors"]
    components = geometry["components"]

    if not sensors:
        raise ValueError("Sensor registry contains no sensors")

    paths: List[dict] = []
    seen_pairs = set()

    for sensor in sensors:
        sensor_id = sensor["sensor_id"]
        position = tuple(sensor["position"])
        component_guid = sensor["component_guid"]

        candidates = []

        for other in sensors:
            other_id = other["sensor_id"]

            if other_id == sensor_id:
                continue

            other_position = tuple(other["position"])

            d = distance(position, other_position)

            candidates.append(
                (
                    d,
                    other_id,
                    other,
                )
            )

        # Deterministic ordering:
        # distance first, sensor ID second.
        candidates.sort(key=lambda item: (item[0], item[1]))

        for d, other_id, other in candidates[:NEIGHBORS_PER_SENSOR]:
            pair = tuple(sorted((sensor_id, other_id)))

            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)

            other_guid = other["component_guid"]

            # At this stage the propagation path consists of the
            # two real IFC components occupied by the endpoint sensors.
            #
            # Intermediate components can be introduced later once
            # we have a validated reduced-order routing rule.
            component_guids = [
                component_guid,
                other_guid,
            ]

            paths.append(
                {
                    "path_id": f"PATH-{len(paths) + 1:03d}",
                    "actuator_id": sensor_id,
                    "receiver_id": other_id,
                    "component_guids": component_guids,
                    "distance_m": round(d, 6),
                    "wave_velocity_m_s": WAVE_VELOCITY_M_S,
                    "attenuation_db_per_m": ATTENUATION_DB_PER_M,
                }
            )

    output = {
        "version": 1,
        "description": (
            "Fixed reduced-order structural propagation network derived "
            "from IFC world-space geometry. This is a simulation "
            "abstraction and does not represent explicit IFC connectivity."
        ),
        "source": {
            "sensor_registry": str(REGISTRY_PATH.relative_to(PROJECT_ROOT)),
            "structural_geometry": str(GEOMETRY_PATH.relative_to(PROJECT_ROOT)),
        },
        "model": {
            "wave_velocity_m_s": WAVE_VELOCITY_M_S,
            "attenuation_db_per_m": ATTENUATION_DB_PER_M,
            "neighbors_per_sensor": NEIGHBORS_PER_SENSOR,
        },
        "sensor_count": len(sensors),
        "component_count": len(components),
        "path_count": len(paths),
        "paths": paths,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Propagation network generated.")
    print(f"Sensors:    {len(sensors)}")
    print(f"Components: {len(components)}")
    print(f"Paths:      {len(paths)}")
    print(f"Output:     {OUTPUT_PATH}")

    print("\nPaths:")
    for path in paths:
        print(
            f"{path['path_id']} | "
            f"{path['actuator_id']} -> {path['receiver_id']} | "
            f"{path['distance_m']:.2f} m"
        )


if __name__ == "__main__":
    main()