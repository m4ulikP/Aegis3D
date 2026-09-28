import json

path = "data/processed/bim/propagation_network.json"

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

for path_data in data["paths"]:
    print(
        f"{path_data['path_id']} | "
        f"{path_data['actuator_id']} -> "
        f"{path_data['receiver_id']}"
    )

    for guid in path_data["component_guids"]:
        print(f"    {guid}")

    print()