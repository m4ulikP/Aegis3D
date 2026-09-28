"""
Enrich the fixed Aegis3D propagation network with IFC components.

The propagation routes are derived from sensor geometry. Structural
components are selected when their world-space bounding boxes come
sufficiently close to the sensor-to-sensor propagation corridor.

This is a reduced-order simulation abstraction. It does NOT claim
explicit IFC connectivity.
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

NETWORK_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "propagation_network.json"
)

OUTPUT_PATH = NETWORK_PATH

# Maximum distance from the propagation corridor for a component
# to be considered part of the reduced-order route.
CORRIDOR_TOLERANCE_M = 1.5

# Don't include extremely tiny/irrelevant components just because
# their center happens to be near the line.
MIN_COMPONENT_LENGTH_M = 0.25


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def vector_subtract(a, b):
    return (
        a[0] - b[0],
        a[1] - b[1],
        a[2] - b[2],
    )


def vector_add(a, b):
    return (
        a[0] + b[0],
        a[1] + b[1],
        a[2] + b[2],
    )


def vector_scale(v, scalar):
    return (
        v[0] * scalar,
        v[1] * scalar,
        v[2] * scalar,
    )


def dot(a, b):
    return (
        a[0] * b[0]
        + a[1] * b[1]
        + a[2] * b[2]
    )


def magnitude(v):
    return math.sqrt(dot(v, v))


def distance(a, b):
    return magnitude(vector_subtract(a, b))


def point_to_segment_distance(point, start, end):
    """
    Return:

        distance from point to line segment,
        projection parameter t.

    t = 0 -> start
    t = 1 -> end
    """

    segment = vector_subtract(end, start)
    segment_length_sq = dot(segment, segment)

    if segment_length_sq == 0:
        return distance(point, start), 0.0

    relative = vector_subtract(point, start)

    t = dot(relative, segment) / segment_length_sq
    t = max(0.0, min(1.0, t))

    projection = vector_add(
        start,
        vector_scale(segment, t),
    )

    return distance(point, projection), t


def bbox_size(bbox_min, bbox_max):
    return (
        abs(bbox_max[0] - bbox_min[0]),
        abs(bbox_max[1] - bbox_min[1]),
        abs(bbox_max[2] - bbox_min[2]),
    )


def component_is_relevant(component):
    """
    Keep structural components with a meaningful physical extent.

    This avoids tiny geometry artifacts becoming propagation nodes.
    """

    sizes = bbox_size(
        component["bbox_min"],
        component["bbox_max"],
    )

    return max(sizes) >= MIN_COMPONENT_LENGTH_M


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
        actuator_id = path["actuator_id"]
        receiver_id = path["receiver_id"]

        if actuator_id not in sensors:
            raise ValueError(
                f"Unknown actuator sensor: {actuator_id}"
            )

        if receiver_id not in sensors:
            raise ValueError(
                f"Unknown receiver sensor: {receiver_id}"
            )

        actuator = sensors[actuator_id]
        receiver = sensors[receiver_id]

        start = tuple(actuator["position"])
        end = tuple(receiver["position"])

        candidates = []

        for guid, component in components.items():

            if not component_is_relevant(component):
                continue

            center = tuple(component["center"])

            corridor_distance, t = point_to_segment_distance(
                center,
                start,
                end,
            )

            if t <= 0.0 or t >= 1.0:
                continue

            if corridor_distance > CORRIDOR_TOLERANCE_M:
                continue

            candidates.append(
                {
                    "guid": guid,
                    "distance_to_path_m": corridor_distance,
                    "path_position": t,
                }
            )

        # Deterministic ordering along the propagation direction.
        candidates.sort(
            key=lambda item: (
                item["path_position"],
                item["guid"],
            )
        )

        # Avoid adding the same component multiple times.
        intermediate_guids = []
        seen = set()

        for candidate in candidates:
            guid = candidate["guid"]

            if guid in seen:
                continue

            seen.add(guid)
            intermediate_guids.append(guid)

        endpoint_guids = [
            actuator["component_guid"],
            receiver["component_guid"],
        ]

        # Build the complete route.
        #
        # Endpoint components remain first/last.
        # Intermediate components are actual IFC GUIDs.
        component_guids = [
            actuator["component_guid"],
            *[
                guid
                for guid in intermediate_guids
                if guid not in endpoint_guids
            ],
            receiver["component_guid"],
        ]

        enriched_path = dict(path)

        enriched_path["component_guids"] = component_guids

        enriched_path["route_metadata"] = {
            "derivation": "geometry_corridor",
            "corridor_tolerance_m": CORRIDOR_TOLERANCE_M,
            "intermediate_component_count": len(
                [
                    guid
                    for guid in component_guids
                    if guid not in endpoint_guids
                ]
            ),
            "note": (
                "Intermediate components are selected from IFC "
                "world-space geometry near the reduced-order "
                "propagation corridor. They do not represent "
                "explicit IFC connectivity relationships."
            ),
        }

        enriched_paths.append(enriched_path)

    output = dict(network)

    output["paths"] = enriched_paths
    output["path_count"] = len(enriched_paths)

    output["route_model"] = {
        "type": "geometry_derived_reduced_order_network",
        "corridor_tolerance_m": CORRIDOR_TOLERANCE_M,
        "intermediate_components": (
            "IFC components whose world-space centers fall "
            "within the propagation corridor"
        ),
        "connectivity_claim": (
            "No explicit IFC connectivity is inferred."
        ),
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Propagation network enriched.")
    print(f"Paths: {len(enriched_paths)}")
    print()

    for path in enriched_paths:
        intermediate_count = path["route_metadata"][
            "intermediate_component_count"
        ]

        print(
            f"{path['path_id']} | "
            f"{path['actuator_id']} -> {path['receiver_id']} | "
            f"{path['distance_m']:.2f} m | "
            f"intermediate components: {intermediate_count}"
        )

    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()