import ifcopenshell
import trimesh
from collections import defaultdict


IFC_FILE = "data/raw/bim/sample_structural.ifc"
GLB_FILE = "models/glb/building_demo.glb"


# --------------------------------------------------
# Load files
# --------------------------------------------------

model = ifcopenshell.open(IFC_FILE)

scene = trimesh.load(
    GLB_FILE,
    force="scene"
)


# --------------------------------------------------
# Build IFC Tag → element mapping
# --------------------------------------------------

tag_map = defaultdict(list)

for element in model.by_type("IfcProduct"):

    tag = getattr(element, "Tag", None)

    if tag:
        tag_map[str(tag)].append(element)


# --------------------------------------------------
# Inspect GLB nodes
# --------------------------------------------------

matched = []
unmatched = []

for node_name in scene.graph.nodes:

    if node_name == "world":
        continue

    # GLB names generally look like:
    #
    # IfcColumn/M_Concrete-Round-Column:450mm:151990
    #
    # The final section is the IFC Tag.

    parts = node_name.split(":")

    if not parts:
        continue

    tag = parts[-1]

    matches = tag_map.get(tag, [])

    if matches:
        matched.append(
            (node_name, tag, matches)
        )
    else:
        unmatched.append(
            (node_name, tag)
        )


# --------------------------------------------------
# Results
# --------------------------------------------------

print("=" * 60)
print("AEGIS3D GLB ↔ IFC MAPPING TEST")
print("=" * 60)

print(f"GLB nodes:             {len(scene.graph.nodes)}")
print(f"Matched to IFC Tag:    {len(matched)}")
print(f"Unmatched:             {len(unmatched)}")

print()

print("SAMPLE MATCHES")
print("-" * 60)

for node_name, tag, elements in matched[:10]:

    element = elements[0]

    print()
    print(f"GLB node:    {node_name}")
    print(f"IFC type:    {element.is_a()}")
    print(f"IFC Tag:     {tag}")
    print(f"IFC GlobalId:{element.GlobalId}")
    print(f"IFC Name:    {element.Name}")


print()
print("UNMATCHED SAMPLE")
print("-" * 60)

for node_name, tag in unmatched[:10]:
    print(node_name)


print()
print("=" * 60)