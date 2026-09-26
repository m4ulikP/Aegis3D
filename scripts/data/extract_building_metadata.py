import json
from pathlib import Path

import ifcopenshell


IFC_FILE = Path("data/raw/bim/sample_structural.ifc")
OUTPUT_FILE = Path("data/processed/bim/building_metadata.json")

model = ifcopenshell.open(IFC_FILE)


def safe_attr(obj, attr, default=None):
    try:
        value = getattr(obj, attr, default)
        return value if value is not None else default
    except Exception:
        return default


# --------------------------------------------------
# Building
# --------------------------------------------------

buildings = model.by_type("IfcBuilding")

building = buildings[0] if buildings else None


# --------------------------------------------------
# Storeys
# --------------------------------------------------

storeys = []

for storey in model.by_type("IfcBuildingStorey"):

    storeys.append({
        "guid": storey.GlobalId,
        "name": safe_attr(storey, "Name", ""),
        "elevation_mm": safe_attr(storey, "Elevation"),
    })


storeys.sort(
    key=lambda x: (
        x["elevation_mm"]
        if x["elevation_mm"] is not None
        else 0
    )
)


# --------------------------------------------------
# Component counts
# --------------------------------------------------

component_types = [
    "IfcColumn",
    "IfcBeam",
    "IfcSlab",
    "IfcWall",
]

component_counts = {}

for component_type in component_types:
    component_counts[component_type] = len(
        model.by_type(component_type)
    )


# --------------------------------------------------
# Metadata
# --------------------------------------------------

metadata = {
    "ifc_schema": model.schema,

    "building": {
        "guid": (
            building.GlobalId
            if building
            else None
        ),
        "name": (
            safe_attr(building, "Name", "")
            if building
            else None
        ),
    },

    "storeys": storeys,

    "component_counts": component_counts,

    "total_structural_components": sum(
        component_counts.values()
    ),
}


# --------------------------------------------------
# Write
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        metadata,
        f,
        indent=2,
        ensure_ascii=False
    )


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("=" * 50)
print("AEGIS3D BUILDING METADATA")
print("=" * 50)

print(f"IFC Schema: {metadata['ifc_schema']}")

print(
    f"Building GUID: "
    f"{metadata['building']['guid']}"
)

print(
    f"Storeys: "
    f"{len(metadata['storeys'])}"
)

print(
    f"Structural components: "
    f"{metadata['total_structural_components']}"
)

print()

for storey in metadata["storeys"]:
    print(
        f"{storey['name']:25} "
        f"Elevation: {storey['elevation_mm']}"
    )

print()

print(f"Output: {OUTPUT_FILE}")
print("Extraction complete.")