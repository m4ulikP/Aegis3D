"""
Add deterministic component influence metadata to the fixed
Aegis3D propagation network.

Influence is derived from the distance between an IFC component's
center and the sensor-to-sensor propagation corridor.

This is an internal simulation parameter. It is NOT a structural
damage severity classification.
"""

import json
import math
from pathlib import Path


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

NETWORK_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "propagation_network.json"
)

# Influence is considered negligible beyond this distance.
INFLUENCE_RADIUS_M = 1.5


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


def point_to_segment_distance(point, start, end):
    segment = (
        end[0] - start[0],
        end[1] - start[1],
        end[2] - start[2],
    )

    relative = (
        point[0] - start[0],
        point[1] - start[1],
        point[2] - start[2],
    )

    segment_length_sq = (
        segment[0] ** 2
        + segment[1] ** 2
        + segment[2] ** 2
    )

    if segment_length_sq == 0:
        return distance(point, start), 0.0

    t = (
        relative[0] * segment[0]
        + relative[1] * segment[1]
        + relative[2] * segment[2]
    ) / segment_length_sq

    t = max(0.0, min(1.0, t))

    projection = (
        start[0] + segment[0] * t,
        start[1] + segment[1] * t,
        start[2] + segment[2] * t,
    )

    return distance(point, projection), t


def calculate_influence(distance_m):
    """
    Convert corridor distance into a deterministic influence factor.

    1.0 = directly on the propagation corridor.
    0.0 = at or beyond the influence radius.

    This is only a simulation weighting factor.
    """

    if distance_m >= INFLUENCE_RADIUS_M:
        return 0.0

    influence = 1.0 - (
        distance_m / INFLUENCE_RADIUS_M
    )

    return max(0.0, min(1.0, influence))


def main():
    registry = load_json(REGISTRY_PATH)
    geometry = load_json(GEOMETRY_PATH)
    network = load_json(NETWORK_PATH)

    sensors = {
        sensor["sensor_id"]: sensor
        for sensor in registry["sensors"]
    }

    components = geometry["components"]

    enriched_paths = []

    for path in network["paths"]:
        actuator = sensors[path["actuator_id"]]
        receiver = sensors[path["receiver_id"]]

        start = tuple(actuator["position"])
        end = tuple(receiver["position"])

        component_influences = []

        for guid in path["component_guids"]:
            component = components[guid]
            center = tuple(component["center"])

            corridor_distance, path_position = (
                point_to_segment_distance(
                    center,
                    start,
                    end,
                )
            )

            influence = calculate_influence(
                corridor_distance
            )

            component_influences.append(
                {
                    "ifc_guid": guid,
                    "distance_to_path_m": round(
                        corridor_distance,
                        6,
                    ),
                    "path_position": round(
                        path_position,
                        6,
                    ),
                    "influence_factor": round(
                        influence,
                        6,
                    ),
                }
            )

        enriched_path = dict(path)

        enriched_path["component_influences"] = (
            component_influences
        )

        enriched_paths.append(enriched_path)

    output = dict(network)

    output["paths"] = enriched_paths

    output["influence_model"] = {
        "type": "distance_based_corridor_influence",
        "radius_m": INFLUENCE_RADIUS_M,
        "maximum_influence": 1.0,
        "minimum_influence": 0.0,
        "note": (
            "Influence factor is an internal reduced-order "
            "simulation weighting. It is not a user-facing "
            "damage severity or structural condition score."
        ),
    }

    with NETWORK_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Path influence metadata added.")
    print(f"Paths: {len(enriched_paths)}")
    print()

    for path in enriched_paths:
        print(
            f"{path['path_id']} | "
            f"{path['actuator_id']} -> "
            f"{path['receiver_id']}"
        )

        for influence in path["component_influences"]:
            print(
                f"    "
                f"{influence['ifc_guid']} | "
                f"distance="
                f"{influence['distance_to_path_m']:.3f} m | "
                f"influence="
                f"{influence['influence_factor']:.3f}"
            )

        print()


if __name__ == "__main__":
    main()