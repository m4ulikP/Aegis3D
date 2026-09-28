"""
Extract world-space structural component geometry from the IFC model.

This creates a lightweight geometry registry for the Aegis3D simulator.
The IFC remains the source of truth; this file is only a cached
representation used by the simulator.
"""

import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom


PROJECT_ROOT = Path(__file__).resolve().parents[2]

IFC_PATH = PROJECT_ROOT / "data" / "raw" / "bim" / "sample_structural.ifc"
COMPONENTS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "bim" / "components.json"
)
OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "bim" / "structural_geometry.json"
)


def get_world_bbox(element, settings):
    """Return world-space bounding box and center for an IFC element."""
    shape = ifcopenshell.geom.create_shape(settings, element)
    vertices = shape.geometry.verts

    xs = vertices[0::3]
    ys = vertices[1::3]
    zs = vertices[2::3]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    center = (
        (min_x + max_x) / 2.0,
        (min_y + max_y) / 2.0,
        (min_z + max_z) / 2.0,
    )

    return {
        "bbox_min": [min_x, min_y, min_z],
        "bbox_max": [max_x, max_y, max_z],
        "center": list(center),
    }


def main():
    print(f"Loading IFC: {IFC_PATH}")

    ifc = ifcopenshell.open(IFC_PATH)

    with COMPONENTS_PATH.open("r", encoding="utf-8") as f:
        components = json.load(f)

    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)

    geometry_by_guid = {}

    for index, component in enumerate(components, start=1):
        guid = component["ifc_guid"]

        element = ifc.by_guid(guid)

        if element is None:
            print(f"[WARN] IFC element not found: {guid}")
            continue

        try:
            geometry = get_world_bbox(element, settings)

            geometry_by_guid[guid] = {
                "ifc_guid": guid,
                "ifc_type": component["ifc_type"],
                "name": component["name"],
                "storey": component["storey"],
                **geometry,
            }

        except Exception as exc:
            print(f"[WARN] Geometry failed for {guid}: {exc}")

        if index % 100 == 0:
            print(f"Processed {index}/{len(components)} components")

    output = {
        "source_ifc": str(IFC_PATH.relative_to(PROJECT_ROOT)),
        "coordinate_system": "IFC world coordinates",
        "units": "metres",
        "component_count": len(geometry_by_guid),
        "components": geometry_by_guid,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Extracted: {len(geometry_by_guid)} components")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()