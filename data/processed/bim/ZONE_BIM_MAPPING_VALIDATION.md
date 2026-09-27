# Zone ↔ BIM Mapping Validation

## 1. Mapping Strategy

This mapping implements **Option 1: Inferred / Logical Prototype Mapping** for the Aegis3D platform. 

Because the repository does not contain authoritative engineering drawings or direct sensor-to-component attachment data linking backend monitoring zones to individual physical structural members, the mapping operates on **rule-based spatial component groups**. Instead of arbitrarily picking a single beam or column out of hundreds of identical elements, each backend monitoring zone is mapped to a logical, structural framing group on a designated storey.

All component assignments are rule-derived programmatically from the canonical IFC structural model data (`data/processed/bim/components.json`), the building hierarchy (`data/processed/bim/building_metadata.json`), and the 3D visualization lookup table (`data/processed/bim/glb_mapping.json`).

---

## 2. Zone 1

- **Backend Zone ID**: `1`
- **Zone Name**: `"Zone 1 - Main Deck Girder"`
- **Backend Floor String**: `"Level 2"`
- **Selected BIM Storey**: `"02 - Floor"`
- **Storey GUID**: `"35r2O_4kTAf8AbYFs_VCl1"`
- **Storey Elevation**: `3800.0 mm`
- **Component Type**: `IfcBeam`
- **Number of Matching Components**: `133`
- **Number of GLB-Resolved Components**: `133` (`100.0%`)
- **Unresolved Components**: `0`
- **Mapping Confidence**: `inferred`
- **Rationale**: Backend Zone 1 is designated as "Level 2". The BIM model contains Storey "02 - Floor" at elevation 3800mm. While the demo zone name uses civil/bridge terminology ("Main Deck Girder"), the BIM model contains a framed floor system with 133 `IfcBeam` elements rather than an explicit bridge girder. The mapping rule selects the complete spatial group of 133 `IfcBeam` elements on Storey "02 - Floor" as the representative structural framing group for Zone 1.

---

## 3. Zone 2

- **Backend Zone ID**: `2`
- **Zone Name**: `"Zone 2 - Substructure Pier B"`
- **Backend Floor String**: `"Substructure"`
- **Selected BIM Storey**: `"01 - Entry Level"`
- **Storey GUID**: `"35r2O_4kTAf8AbYFs_VCl2"`
- **Storey Elevation**: `0.0 mm`
- **Candidate Alternate Storey**: `"Sub Level"` (`storey_guid`: `"0cyJyJpgz269aC2ZMeIyS8"`, elevation: `-2500.0 mm`, `components_in_dataset`: `0`)
- **Component Type**: `IfcColumn`
- **Number of Matching Components**: `77`
- **Number of GLB-Resolved Components**: `77` (`100.0%`)
- **Unresolved Components**: `0`
- **Mapping Confidence**: `inferred_with_storey_ambiguity`
- **Rationale & Ambiguity Documentation**: Backend Zone 2 floor is designated as "Substructure". In the BIM dataset, Storey "Sub Level" exists in the building metadata at elevation -2500mm, but contains 0 extracted structural elements in `components.json`. All 77 lowest vertical load-bearing columns (`IfcColumn`) and foundation retaining walls (`IfcWall`) in the model are assigned to "01 - Entry Level" (elevation 0.0mm). To ensure that valid 3D geometry can be resolved and visually highlighted in the digital twin, the mapping rule designates "01 - Entry Level" with "IfcColumn" as the active spatial group, while explicitly recording the structural datum distinction and ambiguity with "Sub Level".

---

## 4. Validation Results

A dedicated validation suite (`scripts/data/verify_zone_bim_mapping.py`) was executed against `data/processed/bim/zone_bim_mapping.json`.

| Metric | Result | Status |
| :--- | :--- | :--- |
| **Total IFC IDs Checked** | `210` (133 Zone 1 + 77 Zone 2) | **PASSED** |
| **Valid IFC IDs in `components.json`** | `210` | **PASSED** |
| **Invalid / Missing IFC IDs** | `0` | **PASSED** |
| **GLB Mappings Checked** | `210` | **PASSED** |
| **Valid GLB Node Paths in `glb_mapping.json`** | `210` | **PASSED** |
| **Unresolved GLB Mappings** | `0` | **PASSED** |
| **Duplicate IDs Detected** | `0` | **PASSED** |
| **Component / Storey / Type Mismatches** | `0` | **PASSED** |
| **Overall Validation Result** | **100% Valid & Resolved** | **ALL CHECKS PASSED** |

---

## 5. Limitations

The following architectural limitations apply strictly to this mapping artifact:

1. **Inferred Prototype Mapping**: This mapping represents a logical spatial grouping for demonstration and visualization. It does **not** establish verified physical component identity.
2. **No Millimeter Localization**: It does not provide or assume precise 3D physical sensor coordinates or localized crack coordinates.
3. **Indicator of Anomaly Context, Not Damage**: 3D visual highlighting of a mapped component group signifies that the logical backend Zone is experiencing anomalous acoustic events or degraded Structural Health Indicator (SHI) scores; it does **not** establish verified physical damage or failure of every individual member.
4. **Decoupled Architecture**: The mapping layer connects zone-level monitoring telemetry to the existing BIM model without modifying the source IFC or GLB files, and without altering backend database schemas or monitoring algorithms.
