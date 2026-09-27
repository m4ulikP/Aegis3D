"""
Aegis3D Zone <-> BIM Mapping Generator.

Generates data/processed/bim/zone_bim_mapping.json using Option 1:
Inferred / Logical Prototype Spatial Group Mapping.
"""

import json
from pathlib import Path


COMPONENTS_FILE = Path("data/processed/bim/components.json")
GLB_MAPPING_FILE = Path("data/processed/bim/glb_mapping.json")
BUILDING_METADATA_FILE = Path("data/processed/bim/building_metadata.json")
OUTPUT_FILE = Path("data/processed/bim/zone_bim_mapping.json")


def generate_zone_bim_mapping() -> None:
    # 1. Load source datasets
    with open(BUILDING_METADATA_FILE, "r", encoding="utf-8") as f:
        building_metadata = json.load(f)

    with open(COMPONENTS_FILE, "r", encoding="utf-8") as f:
        components = json.load(f)

    with open(GLB_MAPPING_FILE, "r", encoding="utf-8") as f:
        glb_mapping = json.load(f)

    # Build ifc_guid -> glb_node lookup
    guid_to_glb = {}
    for entry in glb_mapping.values():
        if "ifc_guid" in entry and "glb_node" in entry:
            guid_to_glb[entry["ifc_guid"]] = entry["glb_node"]

    # 2. Zone 1 Definition: "02 - Floor" / "IfcBeam"
    z1_storey_name = "02 - Floor"
    z1_storey_guid = "35r2O_4kTAf8AbYFs_VCl1"
    z1_component_type = "IfcBeam"

    z1_matching = [
        c for c in components
        if c.get("storey") == z1_storey_name and c.get("ifc_type") == z1_component_type
    ]
    # Sort deterministically
    z1_matching.sort(key=lambda x: (x.get("name", ""), x.get("ifc_guid", "")))

    z1_components = []
    z1_unresolved = []
    for c in z1_matching:
        guid = c["ifc_guid"]
        glb_node = guid_to_glb.get(guid)
        if glb_node:
            z1_components.append({
                "ifc_guid": guid,
                "name": c.get("name", ""),
                "ifc_type": z1_component_type,
                "glb_node": glb_node,
            })
        else:
            z1_unresolved.append(guid)

    # 3. Zone 2 Definition: "01 - Entry Level" / "IfcColumn" with documented Sub Level ambiguity
    z2_storey_name = "01 - Entry Level"
    z2_storey_guid = "35r2O_4kTAf8AbYFs_VCl2"
    z2_component_type = "IfcColumn"

    z2_matching = [
        c for c in components
        if c.get("storey") == z2_storey_name and c.get("ifc_type") == z2_component_type
    ]
    z2_matching.sort(key=lambda x: (x.get("name", ""), x.get("ifc_guid", "")))

    z2_components = []
    z2_unresolved = []
    for c in z2_matching:
        guid = c["ifc_guid"]
        glb_node = guid_to_glb.get(guid)
        if glb_node:
            z2_components.append({
                "ifc_guid": guid,
                "name": c.get("name", ""),
                "ifc_type": z2_component_type,
                "glb_node": glb_node,
            })
        else:
            z2_unresolved.append(guid)

    # 4. Construct payload
    mapping_payload = {
        "schema_version": "1.0",
        "mapping_type": "inferred_spatial_group",
        "description": "Prototype mapping between backend monitoring Zones and logical BIM component groups.",
        "disclaimer": (
            "This is an inferred prototype mapping for visualization. "
            "It does not establish verified physical component identity or structural damage."
        ),
        "building": {
            "building_guid": building_metadata.get("building", {}).get("guid", ""),
            "building_name": building_metadata.get("building", {}).get("name", ""),
            "ifc_schema": building_metadata.get("ifc_schema", "IFC4"),
        },
        "zones": [
            {
                "zone_id": 1,
                "zone_name": "Zone 1 - Main Deck Girder",
                "mapping_confidence": "inferred",
                "mapping_rule": {
                    "storey_name": z1_storey_name,
                    "storey_guid": z1_storey_guid,
                    "component_type": z1_component_type,
                },
                "rationale": (
                    "Backend Zone 1 floor is designated as 'Level 2'. The BIM model contains Storey '02 - Floor' "
                    "at elevation 3800mm. While the backend demo zone name refers to a 'Main Deck Girder', the BIM model "
                    "contains a framed floor system with 133 IfcBeam elements rather than an explicit bridge girder. "
                    "The mapping rule selects the complete spatial group of 133 IfcBeam elements on Storey '02 - Floor' "
                    "as the logical representative structural group."
                ),
                "expected_component_count": len(z1_matching),
                "resolved_component_count": len(z1_components),
                "unresolved_component_count": len(z1_unresolved),
                "components": z1_components,
            },
            {
                "zone_id": 2,
                "zone_name": "Zone 2 - Substructure Pier B",
                "mapping_confidence": "inferred_with_storey_ambiguity",
                "mapping_rule": {
                    "storey_name": z2_storey_name,
                    "storey_guid": z2_storey_guid,
                    "component_type": z2_component_type,
                    "candidate_alternate_storey": {
                        "storey_name": "Sub Level",
                        "storey_guid": "0cyJyJpgz269aC2ZMeIyS8",
                        "elevation_mm": -2499.9999999999995,
                        "components_in_dataset": 0,
                        "note": (
                            "Storey 'Sub Level' exists in building metadata at elevation -2500mm, but contains 0 "
                            "components in components.json. Lowest structural columns in the BIM dataset are hosted on "
                            "'01 - Entry Level' (elevation 0.0mm)."
                        ),
                    },
                },
                "rationale": (
                    "Backend Zone 2 floor is designated as 'Substructure'. The BIM model contains 'Sub Level' (-2500mm) "
                    "with 0 extracted structural elements, and '01 - Entry Level' (0.0mm) containing all 77 lowest "
                    "vertical load-bearing columns. The mapping rule therefore selects the 77 IfcColumn elements on "
                    "'01 - Entry Level' as the active spatial group representing the substructure/ground support zone, "
                    "while documenting 'Sub Level' as the nominal foundation datum."
                ),
                "ambiguity_note": (
                    "Storey ambiguity exists between nominal datum 'Sub Level' (-2500mm, 0 elements) and host storey "
                    "'01 - Entry Level' (0.0mm, 77 columns). The mapping rule designates '01 - Entry Level' with "
                    "'IfcColumn' so that valid 3D geometry can be resolved and highlighted, while recording the structural "
                    "datum distinction."
                ),
                "expected_component_count": len(z2_matching),
                "resolved_component_count": len(z2_components),
                "unresolved_component_count": len(z2_unresolved),
                "components": z2_components,
            },
        ],
    }

    # 5. Write mapping output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping_payload, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("AEGIS3D ZONE <-> BIM MAPPING GENERATION")
    print("=" * 60)
    print(f"Output: {OUTPUT_FILE}")
    print()
    print(f"Zone 1: {len(z1_components)}/{len(z1_matching)} resolved (unresolved: {len(z1_unresolved)})")
    print(f"Zone 2: {len(z2_components)}/{len(z2_matching)} resolved (unresolved: {len(z2_unresolved)})")
    print()
    print("Generation complete.")


if __name__ == "__main__":
    generate_zone_bim_mapping()
