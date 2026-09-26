import trimesh

GLB_FILE = "models/glb/building_demo.glb"

scene = trimesh.load(
    GLB_FILE,
    force="scene"
)

print("=" * 50)
print("AEGIS3D GLB INSPECTION")
print("=" * 50)

print(f"Geometry objects: {len(scene.geometry)}")
print(f"Scene nodes:      {len(scene.graph.nodes)}")
print()

print("SCENE NODES")
print("-" * 50)

for node in scene.graph.nodes:
    print(node)

print()
print("=" * 50)