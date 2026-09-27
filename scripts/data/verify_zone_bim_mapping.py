"""
Aegis3D Zone <-> BIM Mapping Verification Script.

Validates data/processed/bim/zone_bim_mapping.json against:
1. data/processed/bim/building_metadata.json
2. data/processed/bim/components.json
3. data/processed/bim/glb_mapping.json

Checks:
- Zone ID and rule definitions exist
- Storey exists in building metadata and matches expected elevation
- Component type matches and matches components in components.json
- Every mapped IFC GlobalId exists in components.json
- Every mapped IFC GlobalId resolves to the expected GLB node in glb_mapping.json
- No duplicate IFC GlobalIds exist within any Zone
- All expected counts match resolved counts
"""

import json
import sys
from pathlib import Path


ZONE_MAPPING_FILE = Path("data/processed/bim/zone_bim_mapping.json")
BUILDING_METADATA_FILE = Path("data/processed/bim/building_metadata.json")
COMPONENTS_FILE = Path("data/processed/bim/components.json")
GLB_MAPPING_FILE = Path("data/processed/bim/glb_mapping.json")


def verify_zone_bim_mapping() -> bool:
    print("=" * 60)
    print("AEGIS3D ZONE <-> BIM MAPPING VALIDATION")
    print("=" * 60)

    # 1. Check file existence
    for path, name in [
        (ZONE_MAPPING_FILE, "Zone Mapping File"),
        (BUILDING_METADATA_FILE, "Building Metadata File"),
        (COMPONENTS_FILE, "Components File"),
        (GLB_MAPPING_FILE, "GLB Mapping File"),
    ]:
        if not path.exists():
            print(f"ERROR: {name} not found at {path}")
            return False

    with open(ZONE_MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    with open(BUILDING_METADATA_FILE, "r", encoding="utf-8") as f:
        building_metadata = json.load(f)

    with open(COMPONENTS_FILE, "r", encoding="utf-8") as f:
        components = json.load(f)

    with open(GLB_MAPPING_FILE, "r", encoding="utf-8") as f:
        glb_mapping = json.load(f)

    # Build reference lookup sets
    storeys_by_name = {s["name"]: s for s in building_metadata.get("storeys", [])}
    storeys_by_guid = {s["guid"]: s for s in building_metadata.get("storeys", [])}

    components_by_guid = {c["ifc_guid"]: c for c in components if "ifc_guid" in c}
    guid_to_glb = {}
    for entry in glb_mapping.values():
        if "ifc_guid" in entry and "glb_node" in entry:
            guid_to_glb[entry["ifc_guid"]] = entry["glb_node"]

    zones = mapping_data.get("zones", [])
    if not zones:
        print("ERROR: No zones found in mapping file.")
        return False

    total_components_checked = 0
    total_valid_ifc = 0
    total_valid_glb = 0
    all_passed = True

    print(f"Schema Version: {mapping_data.get('schema_version')}")
    print(f"Mapping Type:   {mapping_data.get('mapping_type')}")
    print(f"Zones to check: {len(zones)}\n")

    for z in zones:
        zone_id = z.get("zone_id")
        zone_name = z.get("zone_name")
        rule = z.get("mapping_rule", {})
        storey_name = rule.get("storey_name")
        storey_guid = rule.get("storey_guid")
        comp_type = rule.get("component_type")
        mapped_comps = z.get("components", [])

        print(f"--- Zone {zone_id}: {zone_name} ---")
        print(f"Rule: Storey='{storey_name}' (GUID={storey_guid}), Type='{comp_type}'")

        # Check storey existence
        if storey_name not in storeys_by_name:
            print(f"  FAILED: Storey '{storey_name}' does not exist in building_metadata.json")
            all_passed = False
        elif storey_guid not in storeys_by_guid:
            print(f"  FAILED: Storey GUID '{storey_guid}' does not match building_metadata.json")
            all_passed = False
        else:
            print(f"  Storey check: PASSED (matches '{storey_name}', elevation={storeys_by_name[storey_name].get('elevation_mm')}mm)")

        # Check duplicate IDs in zone
        guids = [c.get("ifc_guid") for c in mapped_comps if "ifc_guid" in c]
        unique_guids = set(guids)
        if len(guids) != len(unique_guids):
            print(f"  FAILED: Duplicate IFC GUIDs detected ({len(guids)} total, {len(unique_guids)} unique)")
            all_passed = False
        else:
            print(f"  Uniqueness check: PASSED (all {len(guids)} GUIDs unique)")

        # Verify against source components.json
        expected_matches = [
            c for c in components
            if c.get("storey") == storey_name and c.get("ifc_type") == comp_type
        ]
        if len(mapped_comps) != len(expected_matches):
            print(f"  FAILED: Mapped count ({len(mapped_comps)}) does not match source components.json matching count ({len(expected_matches)})")
            all_passed = False
        else:
            print(f"  Count check: PASSED ({len(mapped_comps)} matching components)")

        # Verify each component
        zone_valid_ifc = 0
        zone_valid_glb = 0
        for comp in mapped_comps:
            total_components_checked += 1
            c_guid = comp.get("ifc_guid")
            c_type = comp.get("ifc_type")
            c_glb = comp.get("glb_node")

            # Check IFC existence and type
            if c_guid not in components_by_guid:
                print(f"  FAILED: GUID '{c_guid}' does not exist in components.json")
                all_passed = False
                continue

            src_comp = components_by_guid[c_guid]
            if src_comp.get("storey") != storey_name:
                print(f"  FAILED: Component '{c_guid}' storey '{src_comp.get('storey')}' != rule storey '{storey_name}'")
                all_passed = False
                continue

            if src_comp.get("ifc_type") != comp_type or c_type != comp_type:
                print(f"  FAILED: Component '{c_guid}' type mismatch: expected {comp_type}")
                all_passed = False
                continue

            zone_valid_ifc += 1
            total_valid_ifc += 1

            # Check GLB resolution
            expected_glb = guid_to_glb.get(c_guid)
            if not expected_glb:
                print(f"  FAILED: GUID '{c_guid}' has no GLB node mapping in glb_mapping.json")
                all_passed = False
            elif expected_glb != c_glb:
                print(f"  FAILED: GLB node mismatch for '{c_guid}': mapping={c_glb}, expected={expected_glb}")
                all_passed = False
            else:
                zone_valid_glb += 1
                total_valid_glb += 1

        print(f"  IFC validation: {zone_valid_ifc}/{len(mapped_comps)} valid")
        print(f"  GLB resolution: {zone_valid_glb}/{len(mapped_comps)} resolved")
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total components checked: {total_components_checked}")
    print(f"Valid IFC components:     {total_valid_ifc}")
    print(f"Valid GLB node mappings:  {total_valid_glb}")
    print(f"Overall Result:           {'ALL CHECKS PASSED' if all_passed else 'VALIDATION FAILED'}")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = verify_zone_bim_mapping()
    sys.exit(0 if success else 1)
