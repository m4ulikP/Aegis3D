import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element


# --------------------------------------------------
# Paths
# --------------------------------------------------

IFC_FILE = Path("data/raw/bim/sample_structural.ifc")
OUTPUT_FILE = Path("data/processed/bim/components.json")


# --------------------------------------------------
# Load IFC
# --------------------------------------------------

model = ifcopenshell.open(IFC_FILE)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def get_storey(element):
    """Return the building storey containing this element."""
    container = ifcopenshell.util.element.get_container(element)

    if container and container.is_a("IfcBuildingStorey"):
        return container

    return None


def safe_attr(obj, attr, default=None):
    """Safely get an IFC attribute."""
    try:
        value = getattr(obj, attr, default)
        return value if value is not None else default
    except Exception:
        return default


# --------------------------------------------------
# Extract structural components
# --------------------------------------------------

COMPONENT_TYPES = [
    "IfcColumn",
    "IfcBeam",
    "IfcSlab",
    "IfcWall",
]

components = []

for ifc_type in COMPONENT_TYPES:

    for element in model.by_type(ifc_type):

        storey = get_storey(element)

        component = {
            "ifc_guid": element.GlobalId,
            "name": safe_attr(element, "Name", ""),
            "ifc_type": ifc_type,

            "storey": (
                safe_attr(storey, "Name", "")
                if storey
                else None
            ),

            "storey_guid": (
                safe_attr(storey, "GlobalId")
                if storey
                else None
            ),

            "storey_elevation_mm": (
                safe_attr(storey, "Elevation")
                if storey
                else None
            ),

            "object_type": safe_attr(element, "ObjectType"),

            "predefined_type": safe_attr(
                element,
                "PredefinedType"
            ),
        }

        components.append(component)


# --------------------------------------------------
# Sort deterministically
# --------------------------------------------------

components.sort(
    key=lambda x: (
        x["ifc_type"],
        x["storey"] or "",
        x["name"] or "",
        x["ifc_guid"],
    )
)


# --------------------------------------------------
# Write output
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
        components,
        f,
        indent=2,
        ensure_ascii=False
    )


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("=" * 50)
print("AEGIS3D COMPONENT EXTRACTION")
print("=" * 50)

print(f"IFC:    {IFC_FILE}")
print(f"Output: {OUTPUT_FILE}")
print()

print(f"Components extracted: {len(components)}")
print()

for ifc_type in COMPONENT_TYPES:
    count = sum(
        1
        for c in components
        if c["ifc_type"] == ifc_type
    )

    print(f"{ifc_type:15} {count}")

print()
print("Extraction complete.")