# Aegis3D BIM Architecture & Component Identity

## Purpose

This document defines how the Aegis3D structural BIM model, processed metadata,
GLB visualization model, backend database, sensors, and frontend are related.

The purpose is to ensure that the backend, database, and frontend use a
consistent identity system for structural components.

---

# 1. Source BIM Model

Primary structural BIM model:

`data/raw/bim/sample_structural.ifc`

This IFC file is the source of truth for the structural digital twin.

It is an IFC4 model containing:

| IFC Type | Count |
|---|---:|
| IfcColumn | 203 |
| IfcBeam | 371 |
| IfcSlab | 299 |
| IfcWall | 6 |
| **Total** | **879** |

The model contains:

- 1 `IfcProject`
- 1 `IfcSite`
- 1 `IfcBuilding`
- 5 `IfcBuildingStorey`
- 203 columns
- 371 beams
- 299 slabs
- 6 walls

The model is a representative structural BIM model used for the prototype.
It should NOT be represented as an actual BIM model of a specific Delhi building.

---

# 2. Canonical Component Identity

Every IFC element has a globally unique IFC `GlobalId`.

The IFC `GlobalId` is the canonical identity of a structural component.

Example:

```json
{
  "ifc_guid": "2UD3D7uxP8kecbbBCRtz3S",
  "name": "...",
  "ifc_type": "IfcBeam",
  "storey": "02 - Floor",
  "storey_guid": "...",
  "storey_elevation_mm": 3800.0
}
```

### RULE

Backend/database records representing structural components MUST be able
to reference the component using its IFC `GlobalId`.

Do NOT use GLB node names as component IDs.

Do NOT generate a separate random component ID that replaces the IFC identity.

An application-level database primary key may exist, but the IFC `GlobalId`
must remain available as the external/canonical BIM identity.

---

# 3. Processed BIM Data

The IFC model is processed into several files.

## components.json

Location:

`data/processed/bim/components.json`

This is an extracted representation of the IFC structural components.

It currently contains 879 selected structural components.

Each component contains information such as:

```json
{
  "ifc_guid": "...",
  "name": "...",
  "ifc_type": "IfcBeam",
  "storey": "02 - Floor",
  "storey_guid": "...",
  "storey_elevation_mm": 3800.0,
  "object_type": "...",
  "predefined_type": "..."
}
```

This file is NOT the database schema.

It is generated from the IFC model and should be treated as BIM
source/extraction data.

---

# 4. Building Metadata

Location:

`data/processed/bim/building_metadata.json`

This contains metadata extracted from the IFC building.

The IFC building GlobalId is:

`3bmyaIWCvEHufVx1c33vn1`

The building has 5 storeys:

- Sub Level
- 01 - Entry Level
- 02 - Floor
- 03 - Floor
- Roof

This file provides model-level metadata and is separate from individual
component records.

---

# 5. GLB Visualization Model

Location:

`models/glb/building_demo.glb`

The GLB is the visualization representation of the IFC model.

It is loaded by the frontend using Three.js.

The GLB contains the visible geometry of the structural model.

The GLB is NOT the source of truth for structural identity.

The IFC remains the source of truth.

---

# 6. IFC → GLB Mapping

Location:

`data/processed/bim/glb_mapping.json`

The frontend needs to convert a canonical IFC component identity into
the corresponding Three.js object.

The mapping is:

IFC GlobalId
→ IFC element
→ IFC Tag
→ GLB node name
→ Three.js object

The generated mapping currently contains 933 IFC-to-GLB node mappings.

Example:

```text
IFC Tag
152154

        ↓

IFC GlobalId
2UD3D7uxP8kecbbBCRtz3S

        ↓

GLB Node
IfcBeam/M_Concrete-Rectangular Beam:400 x 800mm:152154
```

### IMPORTANT

The GLB node name is a visualization implementation detail.

The backend/database MUST NOT use the GLB node name as the structural
component's identity.

The frontend uses `glb_mapping.json` to translate the canonical BIM
identity into the corresponding Three.js object.

---

# 7. Recommended Database Relationship

The logical relationship is:

Building
   │
   ├── Component
   │      │
   │      ├── Sensor
   │      │      │
   │      │      └── Telemetry
   │      │
   │      └── Anomaly/Event
   │
   └── ...

More explicitly:

building_id
    ↓
component_id / IFC GlobalId
    ↓
sensor_id
    ↓
telemetry
    ↓
anomaly/event

A sensor should be associated with the structural component it monitors.

An anomaly/event should be able to identify:

- building
- component
- sensor
- timestamp
- anomaly state/score
- relevant signal information

---

# 8. Database vs IFC Responsibilities

The database should NOT attempt to reproduce the entire IFC model.

### IFC/BIM is responsible for:

- Structural component identity
- Structural geometry
- BIM element types
- Storeys
- BIM metadata
- Spatial relationships
- Physical model structure

### Database is responsible for:

- Application entities
- Sensor registration
- Sensor-to-component relationships
- Telemetry
- Events
- Anomaly records
- Current sensor/node state
- Timestamps
- Backend application state

The database can store selected BIM metadata needed for queries,
but it should not become a second IFC parser/model.

---

# 9. Sensor Identity

Sensors should have their own stable application identity.

Example:

`sensor_id = SENSOR-001`

A sensor record should reference the component it monitors:

sensor_id
    ↓
component_ifc_guid

Example:

SENSOR-001
    ↓
2UD3D7uxP8kecbbBCRtz3S

This means SENSOR-001 monitors the structural component whose IFC
GlobalId is `2UD3D7uxP8kecbbBCRtz3S`.

---

# 10. Telemetry

Telemetry belongs to the sensor rather than directly to the GLB.

Conceptually:

Sensor
  ↓
Telemetry
  ↓
Feature extraction
  ↓
Anomaly detection
  ↓
Event
  ↓
Component

The frontend can then resolve the component to its 3D representation:

Event
  ↓
component_ifc_guid
  ↓
glb_mapping.json
  ↓
GLB node
  ↓
Three.js highlight

---

# 11. Component Highlighting

When an anomaly is detected for a component:

sensor
  ↓
component_ifc_guid
  ↓
glb_mapping.json
  ↓
GLB node
  ↓
Three.js
  ↓
highlight component

The frontend should never have to guess which GLB object corresponds to
a database component.

It should use the mapping generated from the IFC.

---

# 12. Offline State

A missing telemetry update must NOT automatically mean that a component
or sensor is healthy.

Use an explicit state such as:

- `HEALTHY`
- `WARNING`
- `ANOMALY`
- `OFFLINE`

`OFFLINE` means that the system does not currently have valid/recent
telemetry from that node.

It must not be interpreted as structural health.

---

# 13. Current Digital Twin Flow

                  IFC MODEL
                      │
                      ├──────────────┐
                      │              │
                      ▼              ▼
             components.json   building_metadata.json
                      │
                      │
                      ▼
              glb_mapping.json
                      │
                      ▼
                  GLB MODEL
                      │
                      ▼
                  Three.js
                      │
                      │
                      │       Backend
                      │          │
                      │          ▼
                      │       Database
                      │          │
                      │          ▼
                      │       Sensors
                      │          │
                      │          ▼
                      │       Telemetry
                      │          │
                      │          ▼
                      │       Anomaly
                      │          │
                      └────────────┘
                             │
                             ▼
                     Component Highlight

---

# 14. Rules for Developers / AI Agents

When modifying the Aegis3D backend or frontend:

1. Treat `sample_structural.ifc` as the BIM source of truth.
2. Treat IFC `GlobalId` as the canonical structural component identity.
3. Do not use GLB node names as database identifiers.
4. Do not hardcode GLB node names into backend logic.
5. Use `glb_mapping.json` to resolve IFC components to GLB nodes.
6. Do not treat `components.json` as the database schema.
7. Do not duplicate the complete IFC model inside the database.
8. Sensors should reference structural components using their IFC identity.
9. Telemetry belongs to sensors.
10. Anomalies/events should reference the affected component and sensor.
11. `OFFLINE` must be distinct from `HEALTHY`.
12. Do not assume an OSM building corresponds to the IFC demonstration model.
13. Do not describe the IFC prototype as an actual BIM model of a Delhi
    building.
