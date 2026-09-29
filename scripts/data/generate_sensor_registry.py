"""
Generate the fixed virtual PZT sensor registry for Aegis3D.

Sensor placement is computed once from the real IFC-derived geometry.
The resulting registry is committed to the project and reused for
every simulator/demo run.

This script should only be rerun deliberately when the BIM model or
sensor layout is intentionally changed.
"""

import json
import math
import sys
from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from simulator.physics.structure import StructuralComponent, StructuralModel

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "sensor_registry.json"
)

ZONE_MAPPING_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bim"
    / "zone_bim_mapping.json"
)

TARGET_STOREYS = [
    "01 - Entry Level",
    "02 - Floor",
    "03 - Floor",
]

SENSORS_PER_STOREY = 4


def distance_2d(
    a: StructuralComponent,
    b: StructuralComponent,
) -> float:
    """Calculate horizontal distance between two components."""
    return math.hypot(
        a.x - b.x,
        a.y - b.y,
    )


def select_spatially_distributed(
    components: List[StructuralComponent],
    count: int,
) -> List[StructuralComponent]:
    """
    Select a deterministic, spatially distributed subset.

    The first component is deterministic. Each subsequent component is
    the candidate farthest from the already-selected set.

    This function is only used during registry generation.
    """
    if len(components) < count:
        raise ValueError(
            f"Need {count} components, but only {len(components)} available"
        )

    remaining = sorted(
        components,
        key=lambda c: (c.x, c.y, c.ifc_guid),
    )

    selected = [remaining[0]]
    remaining.remove(remaining[0])

    while len(selected) < count:
        next_component = max(
            remaining,
            key=lambda candidate: (
                min(
                    distance_2d(candidate, chosen)
                    for chosen in selected
                ),
                candidate.ifc_guid,
            ),
        )

        selected.append(next_component)
        remaining.remove(next_component)

    return selected


def main() -> None:
    model = StructuralModel()

    storey_to_zone = {}
    if ZONE_MAPPING_PATH.exists():
        with ZONE_MAPPING_PATH.open("r", encoding="utf-8") as f:
            zone_map = json.load(f)
            for z in zone_map.get("zones", []):
                s_name = z.get("mapping_rule", {}).get("storey_name")
                if s_name:
                    storey_to_zone[s_name] = (z.get("zone_id"), z.get("zone_name"))

    sensors = []

    sensor_number = 1

    for storey in TARGET_STOREYS:
        columns = [
            component
            for component in model.get_components_by_type("IfcColumn")
            if component.storey == storey
        ]

        selected = select_spatially_distributed(
            columns,
            SENSORS_PER_STOREY,
        )

        for component in selected:
            zone_info = storey_to_zone.get(component.storey, (None, None))
            sensors.append(
                {
                    "sensor_id": f"PZT-Z{sensor_number:02d}",
                    "component_guid": component.ifc_guid,
                    "component_type": component.ifc_type,
                    "component_name": component.name,
                    "storey": component.storey,
                    "zone_id": zone_info[0],
                    "zone_name": zone_info[1],
                    "position": list(component.center),
                    "role": "receiver",
                    "status": "NORMAL",
                }
            )

            sensor_number += 1

    output = {
        "version": 1,
        "description": (
            "Fixed virtual PZT sensor registry generated from the "
            "IFC structural model."
        ),
        "source": (
            "data/raw/bim/sample_structural.ifc → "
            "data/processed/bim/structural_geometry.json"
        ),
        "sensor_count": len(sensors),
        "sensors": sensors,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(sensors)} fixed sensors")
    print(f"Output: {OUTPUT_PATH}")
    print()

    for sensor in sensors:
        print(
            f"{sensor['sensor_id']} | "
            f"{sensor['storey']} | "
            f"{sensor['component_guid']} | "
            f"{tuple(round(v, 2) for v in sensor['position'])}"
        )


if __name__ == "__main__":
    main()