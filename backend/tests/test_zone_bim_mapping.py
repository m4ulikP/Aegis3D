"""Automated tests for Aegis3D Zone <-> BIM Mapping Artifact."""

import json
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAPPING_FILE = REPO_ROOT / "data" / "processed" / "bim" / "zone_bim_mapping.json"
COMPONENTS_FILE = REPO_ROOT / "data" / "processed" / "bim" / "components.json"
GLB_MAPPING_FILE = REPO_ROOT / "data" / "processed" / "bim" / "glb_mapping.json"


@pytest.fixture(scope="module")
def mapping_data():
    assert MAPPING_FILE.exists(), f"Mapping file missing: {MAPPING_FILE}"
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def components_data():
    assert COMPONENTS_FILE.exists(), f"Components file missing: {COMPONENTS_FILE}"
    with open(COMPONENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def glb_mapping_data():
    assert GLB_MAPPING_FILE.exists(), f"GLB mapping file missing: {GLB_MAPPING_FILE}"
    with open(GLB_MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_zone_bim_mapping_structure(mapping_data):
    """Verify top-level metadata and disclaimers exist in the mapping file."""
    assert mapping_data.get("schema_version") == "1.0"
    assert mapping_data.get("mapping_type") == "inferred_spatial_group"
    assert "disclaimer" in mapping_data
    assert "zones" in mapping_data
    assert len(mapping_data["zones"]) == 2


def test_zone_1_mapping(mapping_data, components_data, glb_mapping_data):
    """Verify Zone 1 mapping rule, counts, and 100% GLB resolution."""
    z1 = next((z for z in mapping_data["zones"] if z["zone_id"] == 1), None)
    assert z1 is not None, "Zone 1 missing in mapping"
    assert z1["zone_name"] == "Zone 1 - Main Deck Girder"
    assert z1["mapping_rule"]["storey_name"] == "02 - Floor"
    assert z1["mapping_rule"]["component_type"] == "IfcBeam"
    assert z1["expected_component_count"] == 133
    assert z1["resolved_component_count"] == 133
    assert z1["unresolved_component_count"] == 0

    components = z1["components"]
    assert len(components) == 133

    # Check uniqueness
    guids = [c["ifc_guid"] for c in components]
    assert len(guids) == len(set(guids)), "Duplicate GUIDs detected in Zone 1"

    # Verify against components.json and glb_mapping.json
    components_by_guid = {c["ifc_guid"]: c for c in components_data}
    guid_to_glb = {v["ifc_guid"]: v["glb_node"] for v in glb_mapping_data.values() if "ifc_guid" in v}

    for comp in components:
        guid = comp["ifc_guid"]
        assert guid in components_by_guid, f"GUID {guid} not in components.json"
        assert components_by_guid[guid]["storey"] == "02 - Floor"
        assert components_by_guid[guid]["ifc_type"] == "IfcBeam"
        assert guid in guid_to_glb, f"GUID {guid} not resolved in glb_mapping.json"
        assert comp["glb_node"] == guid_to_glb[guid]


def test_zone_2_mapping(mapping_data, components_data, glb_mapping_data):
    """Verify Zone 2 mapping rule, documented ambiguity, counts, and 100% GLB resolution."""
    z2 = next((z for z in mapping_data["zones"] if z["zone_id"] == 2), None)
    assert z2 is not None, "Zone 2 missing in mapping"
    assert z2["zone_name"] == "Zone 2 - Substructure Pier B"
    assert z2["mapping_confidence"] == "inferred_with_storey_ambiguity"
    assert z2["mapping_rule"]["storey_name"] == "01 - Entry Level"
    assert z2["mapping_rule"]["component_type"] == "IfcColumn"
    assert "candidate_alternate_storey" in z2["mapping_rule"]
    assert z2["mapping_rule"]["candidate_alternate_storey"]["storey_name"] == "Sub Level"
    assert z2["expected_component_count"] == 77
    assert z2["resolved_component_count"] == 77
    assert z2["unresolved_component_count"] == 0

    components = z2["components"]
    assert len(components) == 77

    # Check uniqueness
    guids = [c["ifc_guid"] for c in components]
    assert len(guids) == len(set(guids)), "Duplicate GUIDs detected in Zone 2"

    # Verify against components.json and glb_mapping.json
    components_by_guid = {c["ifc_guid"]: c for c in components_data}
    guid_to_glb = {v["ifc_guid"]: v["glb_node"] for v in glb_mapping_data.values() if "ifc_guid" in v}

    for comp in components:
        guid = comp["ifc_guid"]
        assert guid in components_by_guid, f"GUID {guid} not in components.json"
        assert components_by_guid[guid]["storey"] == "01 - Entry Level"
        assert components_by_guid[guid]["ifc_type"] == "IfcColumn"
        assert guid in guid_to_glb, f"GUID {guid} not resolved in glb_mapping.json"
        assert comp["glb_node"] == guid_to_glb[guid]
