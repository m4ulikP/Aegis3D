"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { api } from "@/lib/api";
import {
    AlertResponse,
    HealthStatus,
    ZoneHealthResponse,
    ZoneResponse,
} from "@/types/api";

/* =========================================================
   TYPES
========================================================= */

export interface BimMappedComponent {
    ifc_guid: string;
    name: string;
    ifc_type: string;
    glb_node: string;
}

export interface ZoneBimMappingRule {
    storey_name: string;
    storey_guid: string;
    component_type: string;
    candidate_alternate_storey?: {
        storey_name: string;
        storey_guid: string;
        elevation_mm: number;
        components_in_dataset: number;
        note: string;
    };
}

export interface ZoneBimMappingEntry {
    zone_id: number;
    zone_name: string;
    mapping_confidence: string;
    mapping_rule: ZoneBimMappingRule;
    rationale: string;
    ambiguity_note?: string;
    expected_component_count: number;
    resolved_component_count: number;
    unresolved_component_count: number;
    components: BimMappedComponent[];
}

export interface ZoneBimMappingFile {
    schema_version: string;
    mapping_type: string;
    description: string;
    disclaimer: string;
    building?: {
        building_guid: string;
        building_name: string;
        ifc_schema: string;
    };
    zones: ZoneBimMappingEntry[];
}

interface DigitalTwinViewerProps {
    onClose: () => void;
    initialZoneId?: number | null;

    /**
     * IFC GUID of the structural component that should be
     * explicitly highlighted by the digital twin.
     *
     * This is intentionally independent from zone selection.
     * Later this can be driven by backend anomaly localization,
     * sensor/path localization, or another frontend interaction.
     */
    selectedComponentGuid?: string | null;
}

/* =========================================================
   ZONE IDENTITY RESOLUTION HELPER
========================================================= */

export function resolveBackendZone(
    mappingZone: ZoneBimMappingEntry,
    backendZones: ZoneResponse[]
): ZoneResponse | undefined {
    if (!backendZones || backendZones.length === 0) return undefined;

    // 1. Exact name match
    const exactMatch = backendZones.find(
        (bz) => bz.name === mappingZone.zone_name
    );
    if (exactMatch) return exactMatch;

    // 2. Case-insensitive / trimmed name match
    const normalizedMatch = backendZones.find(
        (bz) =>
            bz.name.trim().toLowerCase() ===
            mappingZone.zone_name.trim().toLowerCase()
    );
    if (normalizedMatch) return normalizedMatch;

    // 3. Match by zone number if name starts with "Zone X"
    const zoneNumMatch = mappingZone.zone_name.match(/Zone\s*(\d+)/i);

    if (zoneNumMatch) {
        const num = zoneNumMatch[1];

        const numMatch = backendZones.find((bz) => {
            const bzNum = bz.name.match(/Zone\s*(\d+)/i);
            return bzNum && bzNum[1] === num;
        });

        if (numMatch) return numMatch;
    }

    return undefined;
}

/* =========================================================
   GLB NODE NAME NORMALIZATION
========================================================= */

/**
 * Blender / GLB export can rewrite IFC-derived node names.
 *
 * The canonical mapping file contains names such as:
 *   IfcBeam/M_Concrete-Rectangular Beam:300 x 600mm:124614
 *
 * The exported GLB currently contains:
 *   IfcBeamM_Concrete-Rectangular_Beam300_x_600mm124614
 *
 * They represent the same node, but Three.js sees the exported
 * name literally. Normalizing both forms lets the existing
 * IFC GUID -> GLB mapping work without changing the canonical
 * mapping artifact.
 */
function normalizeGlbNodeName(name: string): string {
    return name
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "");
}

/* =========================================================
   BUILDING MODEL WITH DYNAMIC MATERIAL HIGHLIGHTING
========================================================= */

interface BuildingModelProps {
    mapping: ZoneBimMappingFile | null;
    selectedComponentGuid?: string | null;
}

function BuildingModel({
    mapping,
    selectedComponentGuid = null,
}: BuildingModelProps) {
    const { scene } = useGLTF("/models/building_demo.glb");

    // Clone and horizontally center the scene
    const model = useMemo(() => {
        const clonedScene = scene.clone(true);

        const box = new THREE.Box3().setFromObject(clonedScene);
        const center = box.getCenter(new THREE.Vector3());

        // Center horizontally only; preserve original vertical elevation
        clonedScene.position.x -= center.x;
        clonedScene.position.z -= center.z;

        return clonedScene;
    }, [scene]);

    // Index mesh nodes by node.name and cache original materials
    const { meshMap, originalMaterials } = useMemo(() => {
        const mNodeMap = new Map<string, THREE.Mesh[]>();
        const mOrigMat = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();

        model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
                const name = child.name;

                if (name) {
                    // Keep the exact exported name.
                    const exactList = mNodeMap.get(name) || [];
                    exactList.push(child);
                    mNodeMap.set(name, exactList);

                    // Also keep a normalized alias so IFC mapping names
                    // survive Blender/GLB name sanitization.
                    const normalizedName = normalizeGlbNodeName(name);

                    if (normalizedName && normalizedName !== name) {
                        const normalizedList =
                            mNodeMap.get(normalizedName) || [];

                        normalizedList.push(child);
                        mNodeMap.set(normalizedName, normalizedList);
                    }
                }

                mOrigMat.set(child, child.material);
            }
        });

        return {
            meshMap: mNodeMap,
            originalMaterials: mOrigMat,
        };
    }, [model]);

    /*
     * Resolve individual IFC components to their actual GLB meshes.
     *
     * This is deliberately separate from zoneMeshesMap.
     *
     * zoneMeshesMap:
     *     zone_id -> meshes[]
     *
     * componentMeshesMap:
     *     IFC GUID -> meshes[]
     *
     * This gives us a stable bridge for future:
     *
     * backend anomaly
     *      -> IFC GUID
     *      -> GLB node
     *      -> component highlight
     */
    const componentMeshesMap = useMemo(() => {
        const cMap = new Map<string, THREE.Mesh[]>();

        if (!mapping?.zones) return cMap;

        for (const zone of mapping.zones) {
            for (const component of zone.components) {
                const found =
                    meshMap.get(component.glb_node) ||
                    meshMap.get(normalizeGlbNodeName(component.glb_node));

                if (found && found.length > 0) {
                    const existing = cMap.get(component.ifc_guid) || [];
                    cMap.set(component.ifc_guid, [...existing, ...found]);
                }
            }
        }

        return cMap;
    }, [mapping, meshMap]);

    /*
     * Resolve the currently targeted IFC component.
     *
     * We keep the component metadata as well as its meshes so that
     * the next frontend step can build an inspector without having
     * to repeat the mapping lookup.
     */
    const selectedComponent = useMemo(() => {
        if (!selectedComponentGuid || !mapping?.zones) {
            return null;
        }

        for (const zone of mapping.zones) {
            const component = zone.components.find(
                (candidate) =>
                    candidate.ifc_guid === selectedComponentGuid
            );

            if (component) {
                return {
                    component,
                    zone,
                    meshes:
                        componentMeshesMap.get(selectedComponentGuid) || [],
                };
            }
        }

        console.warn(
            `[Aegis3D BIM Viewer] IFC GUID not found in mapping: ${selectedComponentGuid}`
        );

        return null;
    }, [selectedComponentGuid, mapping, componentMeshesMap]);

    // Apply reversible material highlighting
    useEffect(() => {
        const createdMaterials: THREE.Material[] = [];

        function createHighlightMaterial(
            type: "critical" | "warning" | "selected" | "component"
        ) {
            let mat: THREE.MeshStandardMaterial;

            if (type === "critical") {
                mat = new THREE.MeshStandardMaterial({
                    color: new THREE.Color("#f87171"),
                    emissive: new THREE.Color("#dc2626"),
                    emissiveIntensity: 0.85,
                    roughness: 0.2,
                    metalness: 0.1,
                });
            } else if (type === "warning") {
                mat = new THREE.MeshStandardMaterial({
                    color: new THREE.Color("#fbbf24"),
                    emissive: new THREE.Color("#d97706"),
                    emissiveIntensity: 0.75,
                    roughness: 0.25,
                    metalness: 0.1,
                });
            } else if (type === "selected") {
                // Existing healthy-zone selection
                mat = new THREE.MeshStandardMaterial({
                    color: new THREE.Color("#38bdf8"),
                    emissive: new THREE.Color("#0284c7"),
                    emissiveIntensity: 0.65,
                    roughness: 0.3,
                    metalness: 0.15,
                });
            } else {
                /*
                 * Individual component localization.
                 *
                 * This is intentionally visually distinct from the
                 * existing zone-level critical/warning states.
                 */
                mat = new THREE.MeshStandardMaterial({
                    color: new THREE.Color("#f43f5e"),
                    emissive: new THREE.Color("#e11d48"),
                    emissiveIntensity: 1.0,
                    roughness: 0.2,
                    metalness: 0.1,
                });
            }

            createdMaterials.push(mat);
            return mat;
        }

        // ---------------------------------------------------------
        // 1. Restore every original material
        // ---------------------------------------------------------

        originalMaterials.forEach((origMat, mesh) => {
            mesh.material = origMat;
        });

        // ---------------------------------------------------------
        // 2. Zone status stays in the UI; do NOT color every mesh
        // ---------------------------------------------------------
        //
        // Zone alerts/health are represented by the left-hand zone
        // cards. The 3D model is intentionally localized to the
        // specific IFC component identified by selectedComponentGuid.
        // This prevents an anomaly in one component from coloring an
        // entire floor/zone.

        // ---------------------------------------------------------
        // 3. Individual component localization
        // ---------------------------------------------------------

        if (selectedComponent?.meshes.length) {
            const componentMaterial =
                createHighlightMaterial("component");

            for (const mesh of selectedComponent.meshes) {
                mesh.material = componentMaterial;
            }

            console.info(
                `[Aegis3D BIM Viewer] Highlighted component ${selectedComponent.component.ifc_guid} -> ${selectedComponent.component.glb_node}`
            );
        }

        // ---------------------------------------------------------
        // Cleanup
        // ---------------------------------------------------------

        return () => {
            originalMaterials.forEach((origMat, mesh) => {
                mesh.material = origMat;
            });

            createdMaterials.forEach((mat) => mat.dispose());
        };
    }, [
        mapping,
        componentMeshesMap,
        selectedComponent,
        selectedComponentGuid,
        originalMaterials,
    ]);

    return <primitive object={model} />;
}

/* =========================================================
   STATIC FLOOR
========================================================= */

function StaticFloor() {
    return (
        <group position={[0, -0.01, 0]}>
            <gridHelper
                args={[200, 20, "#334155", "#1e293b"]}
                position={[0, 0.01, 0]}
            />
        </group>
    );
}

/* =========================================================
   PRELOAD
========================================================= */

useGLTF.preload("/models/building_demo.glb");

/* =========================================================
   MAIN DIGITAL TWIN VIEWER
========================================================= */

export default function DigitalTwinViewer({
    onClose,
    initialZoneId = null,
    selectedComponentGuid = "1WrzGm1SD2ev45B_OWQ3El",
}: DigitalTwinViewerProps) {
    const [mapping, setMapping] =
        useState<ZoneBimMappingFile | null>(null);

    const [zones, setZones] = useState<ZoneResponse[]>([]);
    const [alerts, setAlerts] = useState<AlertResponse[]>([]);

    const [zoneHealthMap, setZoneHealthMap] =
        useState<Record<number, ZoneHealthResponse>>({});

    const [activeZoneId, setActiveZoneId] =
        useState<number | null>(initialZoneId);

    const [loading, setLoading] =
        useState<boolean>(true);

    const [error, setError] =
        useState<string | null>(null);

    // Load canonical mapping and live monitoring telemetry
    useEffect(() => {
        let isMounted = true;

        async function initViewerData() {
            try {
                // 1. Fetch canonical Step 1 mapping artifact
                const mapRes = await fetch(
                    "/data/zone_bim_mapping.json"
                );

                if (!mapRes.ok) {
                    throw new Error(
                        `Failed to load zone BIM mapping: HTTP ${mapRes.status}`
                    );
                }

                const mapData: ZoneBimMappingFile =
                    await mapRes.json();

                // 2. Fetch live zones and active alerts
                const [zonesData, alertsData] =
                    await Promise.all([
                        api.getZones().catch((err) => {
                            console.warn(
                                "Failed to fetch zones for BIM viewer:",
                                err
                            );

                            return [];
                        }),

                        api.getAlerts().catch((err) => {
                            console.warn(
                                "Failed to fetch alerts for BIM viewer:",
                                err
                            );

                            return [];
                        }),
                    ]);

                // 3. Fetch detailed health status for each zone
                const healthEntries: Record<
                    number,
                    ZoneHealthResponse
                > = {};

                await Promise.all(
                    zonesData.map(async (z) => {
                        try {
                            const h =
                                await api.getZoneHealth(z.id);

                            healthEntries[z.id] = h;
                        } catch (hErr) {
                            console.warn(
                                `Failed to fetch health for zone ${z.id}:`,
                                hErr
                            );
                        }
                    })
                );

                if (isMounted) {
                    setMapping(mapData);
                    setZones(zonesData);
                    setAlerts(alertsData);
                    setZoneHealthMap(healthEntries);
                    setLoading(false);
                }
            } catch (err: any) {
                if (isMounted) {
                    console.error(
                        "[Aegis3D BIM Viewer] Initialization error:",
                        err
                    );

                    setError(
                        err.message ||
                        "Failed to initialize Digital Twin viewer"
                    );

                    setLoading(false);
                }
            }
        }

        initViewerData();

        return () => {
            isMounted = false;
        };
    }, []);

    const totalMappedComponents = useMemo(() => {
        if (!mapping?.zones) return 0;

        return mapping.zones.reduce(
            (sum, z) =>
                sum +
                (z.resolved_component_count ||
                    z.components.length),
            0
        );
    }, [mapping]);

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                background: "#020617",
                fontFamily:
                    "system-ui, -apple-system, sans-serif",
            }}
        >
            {/* =====================================================
                TOP BAR
            ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 64,
                    zIndex: 10,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0 24px",
                    background:
                        "linear-gradient(to bottom, rgba(2,6,23,0.95), rgba(2,6,23,0.65))",
                    borderBottom:
                        "1px solid rgba(148,163,184,0.15)",
                    backdropFilter: "blur(10px)",
                }}
            >
                {/* Left Branding */}

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 14,
                    }}
                >
                    <div
                        style={{
                            fontSize: 18,
                            fontWeight: 700,
                            letterSpacing: "0.08em",
                            color: "#f8fafc",
                        }}
                    >
                        AEGIS3D
                    </div>

                    <div
                        style={{
                            width: 1,
                            height: 22,
                            background:
                                "rgba(148,163,184,0.3)",
                        }}
                    />

                    <div
                        style={{
                            fontSize: 14,
                            color: "#94a3b8",
                        }}
                    >
                        Structural Digital Twin & Health
                        Visualization
                    </div>
                </div>

                {/* Right Close Button */}

                <button
                    onClick={onClose}
                    style={{
                        border:
                            "1px solid rgba(148,163,184,0.25)",
                        background:
                            "rgba(15,23,42,0.8)",
                        color: "#e2e8f0",
                        padding: "9px 16px",
                        borderRadius: 8,
                        fontSize: 13,
                        fontWeight: 500,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                    }}
                >
                    ← Back to City
                </button>
            </div>

            {/* =====================================================
                LEFT HUD: ZONE & STRUCTURAL BIM INSPECTOR
            ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    top: 80,
                    left: 20,
                    zIndex: 10,
                    width: 360,
                    maxHeight: "calc(100vh - 180px)",
                    overflowY: "auto",
                    background:
                        "rgba(15, 23, 42, 0.88)",
                    backdropFilter: "blur(12px)",
                    border:
                        "1px solid rgba(148, 163, 184, 0.2)",
                    borderRadius: 10,
                    padding: 16,
                    color: "#f1f5f9",
                    boxShadow:
                        "0 20px 25px -5px rgba(0, 0, 0, 0.6)",
                }}
            >
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 6,
                    }}
                >
                    <h2
                        style={{
                            fontSize: 14,
                            fontWeight: 700,
                            color: "#67e8f9",
                            margin: 0,
                            textTransform: "uppercase",
                        }}
                    >
                        Monitored BIM Zones
                    </h2>

                    <span
                        style={{
                            fontSize: 11,
                            color: "#94a3b8",
                            background:
                                "rgba(51, 65, 85, 0.6)",
                            padding: "2px 6px",
                            borderRadius: 4,
                        }}
                    >
                        {totalMappedComponents} elements
                        mapped
                    </span>
                </div>

                <p
                    style={{
                        fontSize: 11,
                        color: "#94a3b8",
                        margin: "0 0 12px 0",
                        lineHeight: 1.4,
                    }}
                >
                    Option 1: Inferred spatial component
                    groups linked to live telemetry.
                </p>

                {/* View Mode Selector */}

                <div
                    style={{
                        display: "flex",
                        gap: 6,
                        marginBottom: 12,
                    }}
                >
                    <button
                        onClick={() => setActiveZoneId(null)}
                        style={{
                            flex: 1,
                            padding: "6px 8px",
                            fontSize: 11,
                            fontWeight: 600,
                            borderRadius: 6,
                            border:
                                activeZoneId === null
                                    ? "1px solid #38bdf8"
                                    : "1px solid rgba(148, 163, 184, 0.2)",
                            background:
                                activeZoneId === null
                                    ? "rgba(56, 189, 248, 0.2)"
                                    : "rgba(30, 41, 59, 0.6)",
                            color:
                                activeZoneId === null
                                    ? "#38bdf8"
                                    : "#cbd5e1",
                            cursor: "pointer",
                        }}
                    >
                        All Anomaly Highlights
                    </button>

                    {mapping?.zones.map((z) => (
                        <button
                            key={z.zone_id}
                            onClick={() =>
                                setActiveZoneId(z.zone_id)
                            }
                            style={{
                                flex: 1,
                                padding: "6px 8px",
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 6,
                                border:
                                    activeZoneId ===
                                        z.zone_id
                                        ? "1px solid #67e8f9"
                                        : "1px solid rgba(148, 163, 184, 0.2)",
                                background:
                                    activeZoneId ===
                                        z.zone_id
                                        ? "rgba(34, 211, 238, 0.2)"
                                        : "rgba(30, 41, 59, 0.6)",
                                color:
                                    activeZoneId ===
                                        z.zone_id
                                        ? "#67e8f9"
                                        : "#cbd5e1",
                                cursor: "pointer",
                            }}
                        >
                            Zone {z.zone_id}
                        </button>
                    ))}
                </div>

                {/* Zone Cards */}

                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 10,
                    }}
                >
                    {mapping?.zones.map((zone) => {
                        const backendZone =
                            resolveBackendZone(
                                zone,
                                zones
                            );

                        const backendZoneId =
                            backendZone?.id;

                        const health =
                            backendZoneId !== undefined
                                ? zoneHealthMap[
                                backendZoneId
                                ]
                                : undefined;

                        const zoneAlerts =
                            backendZoneId !== undefined
                                ? alerts.filter(
                                    (a) =>
                                        a.zone_id ===
                                        backendZoneId &&
                                        a.status ===
                                        "ACTIVE"
                                )
                                : [];

                        const isSelected =
                            activeZoneId === zone.zone_id;

                        const isCritical =
                            zoneAlerts.some(
                                (a) =>
                                    a.severity ===
                                    "CRITICAL" ||
                                    a.severity === "HIGH"
                            ) ||
                            health?.status ===
                            "HIGH_PRIORITY_INSPECTION" ||
                            health?.status ===
                            "INSPECTION_ADVISED";

                        const isWarning =
                            zoneAlerts.some(
                                (a) =>
                                    a.severity ===
                                    "MEDIUM" ||
                                    a.severity === "LOW"
                            ) ||
                            health?.status ===
                            "MONITOR";

                        return (
                            <div
                                key={zone.zone_id}
                                onClick={() =>
                                    setActiveZoneId(
                                        zone.zone_id
                                    )
                                }
                                style={{
                                    border: isSelected
                                        ? "1px solid #38bdf8"
                                        : isCritical
                                            ? "1px solid rgba(239, 68, 68, 0.5)"
                                            : "1px solid rgba(75, 85, 99, 0.4)",
                                    background:
                                        isSelected
                                            ? "rgba(30, 58, 138, 0.3)"
                                            : "rgba(30, 41, 59, 0.5)",
                                    borderRadius: 8,
                                    padding: 12,
                                    cursor: "pointer",
                                    transition:
                                        "all 0.15s ease",
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent:
                                            "space-between",
                                        alignItems:
                                            "flex-start",
                                        marginBottom: 4,
                                    }}
                                >
                                    <div
                                        style={{
                                            fontWeight: 600,
                                            fontSize: 13,
                                            color: "#f8fafc",
                                        }}
                                    >
                                        {zone.zone_name}
                                    </div>

                                    <span
                                        style={{
                                            fontSize: 10,
                                            fontWeight: 700,
                                            padding:
                                                "2px 6px",
                                            borderRadius: 4,
                                            background:
                                                isCritical
                                                    ? "#dc2626"
                                                    : isWarning
                                                        ? "#d97706"
                                                        : "#059669",
                                            color: "#ffffff",
                                        }}
                                    >
                                        {isCritical &&
                                            zoneAlerts.length >
                                            0 &&
                                            (!health ||
                                                health.status ===
                                                "NORMAL")
                                            ? "ALERT ACTIVE"
                                            : health?.status ??
                                            (isCritical
                                                ? "ALERT ACTIVE"
                                                : "NORMAL")}
                                    </span>
                                </div>

                                <div
                                    style={{
                                        fontSize: 11,
                                        color: "#94a3b8",
                                        marginBottom: 6,
                                    }}
                                >
                                    Storey:{" "}
                                    <span
                                        style={{
                                            color: "#e2e8f0",
                                        }}
                                    >
                                        {
                                            zone
                                                .mapping_rule
                                                .storey_name
                                        }
                                    </span>{" "}
                                    · Type:{" "}
                                    <span
                                        style={{
                                            color: "#e2e8f0",
                                        }}
                                    >
                                        {
                                            zone
                                                .mapping_rule
                                                .component_type
                                        }
                                    </span>{" "}
                                    (
                                    {
                                        zone.components
                                            .length
                                    }{" "}
                                    elements)
                                </div>

                                {health?.score !==
                                    undefined && (
                                        <div
                                            style={{
                                                fontSize: 11,
                                                color: "#cbd5e1",
                                                marginBottom: 6,
                                                display:
                                                    "flex",
                                                justifyContent:
                                                    "space-between",
                                            }}
                                        >
                                            <span>
                                                Structural Health
                                                Indicator (SHI):
                                            </span>

                                            <span
                                                style={{
                                                    fontWeight: 700,
                                                    color: isCritical
                                                        ? "#f87171"
                                                        : isWarning
                                                            ? "#fbbf24"
                                                            : "#34d399",
                                                }}
                                            >
                                                {health.score.toFixed(
                                                    1
                                                )}{" "}
                                                / 100
                                            </span>
                                        </div>
                                    )}

                                {zoneAlerts.length >
                                    0 && (
                                        <div
                                            style={{
                                                background:
                                                    "rgba(220, 38, 38, 0.2)",
                                                border:
                                                    "1px solid rgba(239, 68, 68, 0.4)",
                                                borderRadius: 6,
                                                padding:
                                                    "6px 8px",
                                                marginTop: 6,
                                                fontSize: 11,
                                                color: "#fecaca",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    fontWeight: 700,
                                                    color: "#fca5a5",
                                                    marginBottom: 2,
                                                }}
                                            >
                                                ⚠️{" "}
                                                {
                                                    zoneAlerts[0]
                                                        .title
                                                }
                                            </div>

                                            <div
                                                style={{
                                                    fontSize: 10,
                                                    color: "#e2e8f0",
                                                }}
                                            >
                                                {
                                                    zoneAlerts[0]
                                                        .message
                                                }
                                            </div>
                                        </div>
                                    )}
                            </div>
                        );
                    })}
                </div>

                {/* Architectural Prototype Disclaimer */}

                <div
                    style={{
                        marginTop: 14,
                        padding: "8px 10px",
                        background:
                            "rgba(30, 41, 59, 0.4)",
                        border:
                            "1px solid rgba(148, 163, 184, 0.15)",
                        borderRadius: 6,
                        fontSize: 10,
                        color: "#94a3b8",
                        lineHeight: 1.4,
                    }}
                >
                    <span
                        style={{
                            fontWeight: 700,
                            color: "#cbd5e1",
                        }}
                    >
                        Prototype Disclaimer:
                    </span>{" "}
                    Zone anomalies are visually highlighted
                    across the mapped structural framing
                    group. This indicates monitoring state
                    and does not establish certified
                    structural damage or millimeter crack
                    localization.
                </div>
            </div>

            {/* =====================================================
                3D CANVAS
            ===================================================== */}

            <Canvas
                shadows
                dpr={[1, 2]}
                camera={{
                    position: [15, 12, 15],
                    fov: 45,
                    near: 0.1,
                    far: 5000,
                }}
                gl={{ antialias: true }}
            >
                <color
                    attach="background"
                    args={["#020617"]}
                />

                {/* Lighting */}

                <ambientLight intensity={0.7} />

                <hemisphereLight
                    args={[
                        "#dbeafe",
                        "#0f172a",
                        1.2,
                    ]}
                />

                <directionalLight
                    castShadow
                    position={[30, 40, 20]}
                    intensity={2.2}
                    shadow-mapSize-width={2048}
                    shadow-mapSize-height={2048}
                />

                {/* Structural Digital Twin */}

                <BuildingModel
                    mapping={mapping}
                    selectedComponentGuid={
                        selectedComponentGuid
                    }
                />

                {/* Floor Grid */}

                <StaticFloor />

                {/* Camera Orbit Controls */}

                <OrbitControls
                    makeDefault
                    enableDamping
                    dampingFactor={0.08}
                    rotateSpeed={0.7}
                    panSpeed={1.5}
                    zoomSpeed={0.9}
                    minDistance={2}
                    maxDistance={500}
                    mouseButtons={{
                        LEFT: THREE.MOUSE.ROTATE,
                        MIDDLE: THREE.MOUSE.PAN,
                        RIGHT: THREE.MOUSE.PAN,
                    }}
                />
            </Canvas>

            {/* =====================================================
                CONTROL HINT
            ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    bottom: 20,
                    left: 20,
                    padding: "10px 14px",
                    background:
                        "rgba(15,23,42,0.8)",
                    border:
                        "1px solid rgba(148,163,184,0.15)",
                    borderRadius: 8,
                    color: "#94a3b8",
                    fontSize: 12,
                    backdropFilter: "blur(8px)",
                }}
            >
                <div>Left click · Rotate</div>
                <div>
                    Middle / Right click · Pan
                </div>
                <div>Scroll · Zoom</div>
            </div>

            {/* =====================================================
                STATUS INDICATOR
            ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    bottom: 20,
                    right: 20,
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "9px 14px",
                    background:
                        "rgba(15,23,42,0.8)",
                    border:
                        "1px solid rgba(148,163,184,0.15)",
                    borderRadius: 8,
                    color: "#cbd5e1",
                    fontSize: 12,
                    backdropFilter: "blur(8px)",
                }}
            >
                <div
                    style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        background: loading
                            ? "#f59e0b"
                            : error
                                ? "#ef4444"
                                : "#22c55e",
                        boxShadow: loading
                            ? "0 0 8px rgba(245,158,11,0.7)"
                            : error
                                ? "0 0 8px rgba(239,68,68,0.7)"
                                : "0 0 8px rgba(34,197,94,0.7)",
                    }}
                />

                <div>
                    {loading
                        ? "Syncing Live Telemetry..."
                        : error
                            ? "BIM Offline"
                            : "Digital Twin Synced · Live Health Connected"}
                </div>
            </div>
        </div>
    );
}