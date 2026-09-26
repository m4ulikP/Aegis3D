import ifcopenshell
import ifcopenshell.util.element


IFC_FILE = "data/raw/bim/sample_structural.ifc"

model = ifcopenshell.open(IFC_FILE)

print("=" * 50)
print("Aegis3D IFC SUMMARY")
print("=" * 50)

print(f"Schema: {model.schema}")
print()

entity_types = [
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcColumn",
    "IfcBeam",
    "IfcSlab",
    "IfcWall",
    "IfcDoor",
    "IfcWindow",
]

print("ENTITY COUNTS")
print("-" * 50)

for entity_type in entity_types:
    print(f"{entity_type:20} {len(model.by_type(entity_type))}")

print()

print("BUILDINGS")
print("-" * 50)

for building in model.by_type("IfcBuilding"):
    print(f"Name: {building.Name}")
    print(f"GUID: {building.GlobalId}")

print()

print("STOREYS")
print("-" * 50)

for storey in model.by_type("IfcBuildingStorey"):
    print(
        f"{storey.Name:25}"
        f" Elevation: {storey.Elevation}"
        f" GUID: {storey.GlobalId}"
    )

print()

print("COLUMN COUNT BY STOREY")
print("-" * 50)

for storey in model.by_type("IfcBuildingStorey"):
    columns = [
        c for c in model.by_type("IfcColumn")
        if ifcopenshell.util.element.get_container(c) == storey
    ]

    print(f"{storey.Name:25} {len(columns)}")

print()
print("=" * 50)