import json
from pathlib import Path

import ifcopenshell
import trimesh


# --------------------------------------------------
# Paths
# --------------------------------------------------

IFC_FILE = Path("data/raw/bim/sample_structural.ifc")
GLB_FILE = Path("models/glb/building_demo.glb")
OUTPUT_FILE = Path("data/processed/bim/glb_mapping.json")


# --------------------------------------------------
# Load files
# --------------------------------------------------

model = ifcopenshell.open(IFC_FILE)

scene = trimesh.load(
    GLB_FILE,
    force="scene"
)


# --------------------------------------------------
# Build IFC Tag → element lookup
# --------------------------------------------------

tag_map = {}

for element in model.by_type("IfcProduct"):

    tag = getattr(element, "Tag", None)

    if tag is None:
        continue

    tag_map[str(tag)] = element


# --------------------------------------------------
# Generate mapping
# --------------------------------------------------

mapping = {}

for node_name in scene.graph.nodes:

    if node_name == "world":
        continue

    # Exported Bonsai names follow:
    #
    # IfcType/Name:Tag
    #
    # The final colon-separated section is the IFC Tag.

    parts = node_name.split(":")

    if not parts:
        continue

    tag = parts[-1]

    element = tag_map.get(tag)

    if element is None:
        continue

    mapping[tag] = {
        "ifc_guid": element.GlobalId,
        "ifc_type": element.is_a(),
        "name": element.Name,
        "glb_node": node_name,
    }


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
        mapping,
        f,
        indent=2,
        ensure_ascii=False
    )


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("=" * 60)
print("AEGIS3D GLB MAPPING GENERATION")
print("=" * 60)

print(f"IFC elements with tags: {len(tag_map)}")
print(f"GLB nodes:              {len(scene.graph.nodes)}")
print(f"Mappings generated:     {len(mapping)}")

print()
print(f"Output: {OUTPUT_FILE}")

print()
print("SAMPLE MAPPINGS")
print("-" * 60)

for tag, data in list(mapping.items())[:5]:

    print()
    print(f"Tag:       {tag}")
    print(f"IFC GUID:  {data['ifc_guid']}")
    print(f"IFC Type:  {data['ifc_type']}")
    print(f"Name:      {data['name']}")
    print(f"GLB Node:  {data['glb_node']}")

print()
print("=" * 60)