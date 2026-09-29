# Aegis3D Zone, Sensor & BIM Identifier Audit

This document audits the identifier structures and spatial mappings currently established across the Aegis3D backend, database schemas, BIM datasets, GIS data, and architectural specification (`docs/BIM_ARCHITECTURE.md`).

---

## 1. Identifier Hierarchy Audit

| Entity | Identifier Type | Example Values | Source Location |
| :--- | :--- | :--- | :--- |
| **Building** | String Code | `BLDG-001` | `data/processed/bim/building_metadata.json`, `BIM_ARCHITECTURE.md` |
| **Storey / Floor** | String Tag | `STOREY-GROUND`, `STOREY-01` .. `STOREY-04` | `data/processed/bim/building_metadata.json` |
| **Building Floor (DB)** | String | `"Floor 1"`, `"Floor 2"` | `Zone.floor` column in `zones` table |
| **Zone (DB)** | Integer Primary Key | `1`, `2`, `3` | `Zone.id` column in `zones` table |
| **Zone Name** | String Tag | `"Zone 1 - North Wing"` | `Zone.name` column |
| **IFC GlobalId** | 22-char Base64 UUID | `3kR9wX$yH0G9zL2qW1eR4t` | `data/raw/bim/sample_structural.ifc`, `glb_mapping.json` |
| **Structural Component** | IFC Class + Tag | `IfcColumn` (`C-01`), `IfcBeam` (`B-102`), `IfcSlab`, `IfcWall` | `building_metadata.json`, `glb_mapping.json` |
| **3D GLB Node Name** | Mesh Object Name | `IfcColumn_203_C01` | `models/glb/building_demo.glb`, `glb_mapping.json` |
| **Sensor Source ID** | String Code | `"PZT-01"`, `"PZT-02"` | `Event.source_id` column in `events` table |
| **Event** | Integer Primary Key | `101`, `102` | `Event.id` column in `events` table |
| **Correlation Group** | String Identifier | `"CORR-20260927-001"` | `Event.correlation_id`, `CorrelatedEventGroup.group_id` |

---

## 2. Established Mappings

1. **Building $\rightarrow$ Storey $\rightarrow$ Structural Component**:
   Fully parsed and mapped offline in `data/processed/bim/building_metadata.json` and `glb_mapping.json`. Contains 879 structural elements (203 columns, 371 beams, 299 slabs, 6 walls) across 5 storeys.
2. **IFC GlobalId $\rightarrow$ 3D GLB Mesh Node**:
   Mapped in `data/processed/bim/glb_mapping.json` (933 node mappings). Allows 3D browser renderers (Three.js / React Three Fiber) to locate and highlight specific 3D meshes when referenced by IFC GlobalId or tag name.
3. **Sensor Source ID $\rightarrow$ Zone ID $\rightarrow$ Event**:
   Fully established in PostgreSQL database schema (`Event.zone_id` foreign key pointing to `Zone.id`, `Event.source_id` recording sensor tag).

---

## 3. Existing Identifier Gaps & Technical Notes

- **No Direct Database Foreign Key to IFC GlobalId**: The current PostgreSQL `zones` database table uses integer primary keys (`id: int`) and text floor tags (`floor: varchar`), without a database column explicitly tying a `Zone` record to an `ifc_global_id`.
- **Zone Spatial Grouping**: As specified in `docs/BIM_ARCHITECTURE.md`, a `Zone` represents a logical spatial monitoring area (e.g. "North Wing Floor 2") containing multiple structural components (columns/beams) and sensors.
- **Frontend Mapping Responsibility**: When rendering 3D highlights in the frontend browser viewer, the frontend should map `zone.floor` or `zone.name` to the storeys/components in `building_metadata.json` and lookup corresponding GLB node names via `glb_mapping.json`.
- **Zero Schema Changes Made**: Per Step 11 requirements, no database schema changes were made to introduce `component_ifc_guid` columns. The existing zone-based REST endpoints serve clean structural health summaries for the zone.
