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
import TelemetryHUD from "../dashboard/TelemetryHUD";

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
}

/* =========================================================
   CANONICAL SENSOR-TO-PHYSICS LOCALIZATION REGISTRY
========================================================= */

export interface LocalizedComponentInfo {
    guid: string;
    glb_node: string;
    name: string;
    type: string;
    label: string;
}

export const SENSOR_LOCALIZED_COMPONENTS: Record<string, LocalizedComponentInfo> = {
    // Zone 1 Primary Simulated Damaged Component (Physics Guided-Wave Path 007)
    "PZT-Z05": {
        guid: "1WrzGm1SD2ev45B_OWQ3El",
        glb_node: "IfcBeam/M_Concrete-Rectangular Beam:300 x 600mm:124614",
        name: "M_Concrete-Rectangular Beam:300 x 600mm:124614",
        type: "IfcBeam",
        label: "Simulated Affected Component (Main Deck Beam 124614)",
    },
    "PZT-Z06": {
        guid: "1WrzGm1SD2ev45B_OWQ3Eg",
        glb_node: "IfcBeam/M_Concrete-Rectangular Beam:300 x 600mm:124615",
        name: "M_Concrete-Rectangular Beam:300 x 600mm:124615",
        type: "IfcBeam",
        label: "Simulated Affected Component (Main Deck Beam 124615)",
    },
    // Zone 2 Primary Simulated Damaged Component (Physics Guided-Wave Path 001)
    "PZT-Z01": {
        guid: "2Ci2k7uxXCqAqqsxOmESOv",
        glb_node: "IfcColumn/UC-Universal Columns-Column:UC356x368x129:123067",
        name: "UC-Universal Columns-Column:UC356x368x129:123067",
        type: "IfcColumn",
        label: "Simulated Affected Component (Pier B Column 123067)",
    },
    "PZT-Z02": {
        guid: "18YHwga450Mw4Fy6M5t_8F",
        glb_node: "IfcColumn/M_Concrete-Round-Column:450mm:122548",
        name: "M_Concrete-Round-Column:450mm:122548",
        type: "IfcColumn",
        label: "Simulated Affected Component (Pier B Column 122548)",
    },
};

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
        (bz) => bz.name.trim().toLowerCase() === mappingZone.zone_name.trim().toLowerCase()
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

export function resolveMappingZoneId(
    targetId: number | null,
    mapping: ZoneBimMappingFile | null,
    backendZones: ZoneResponse[]
): number | null {
    if (targetId === null || targetId === undefined || !mapping?.zones) return null;

    // 1. Direct match with mapping.zone.zone_id (e.g. 1 or 2)
    const directMatch = mapping.zones.find((z) => z.zone_id === targetId);
    if (directMatch) return directMatch.zone_id;

    // 2. Match targetId with backendZone.id
    const matchedByBackend = mapping.zones.find((mz) => {
        const bz = resolveBackendZone(mz, backendZones);
        return bz?.id === targetId;
    });
    if (matchedByBackend) return matchedByBackend.zone_id;

    return null;
}

/* =========================================================
   BUILDING MODEL WITH LOCALIZED MATERIAL HIGHLIGHTING
========================================================= */

interface BuildingModelProps {
    mapping: ZoneBimMappingFile | null;
    activeZoneId: number | null;
    zones: ZoneResponse[];
    zoneHealthMap: Record<number, ZoneHealthResponse>;
    alerts: AlertResponse[];
    onSelectZone?: (zoneId: number) => void;
}

function BuildingModel({
    mapping,
    activeZoneId,
    zones,
    zoneHealthMap,
    alerts,
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
                    const list = mNodeMap.get(name) || [];
                    list.push(child);
                    mNodeMap.set(name, list);
                }
                mOrigMat.set(child, child.material);
            }
        });

        return { meshMap: mNodeMap, originalMaterials: mOrigMat };
    }, [model]);

    // Index all GLB nodes in zone_bim_mapping.json to Three.js meshes
    const zoneMeshesMap = useMemo(() => {
        const zMap = new Map<number, THREE.Mesh[]>();
        if (!mapping?.zones) return zMap;

        let totalResolved = 0;
        let totalUnresolved = 0;

        for (const zone of mapping.zones) {
            const meshes: THREE.Mesh[] = [];
            for (const comp of zone.components) {
                const sanitized = THREE.PropertyBinding.sanitizeNodeName(comp.glb_node);

                let found = meshMap.get(sanitized);
                if (!found || found.length === 0) {
                    found = meshMap.get(comp.glb_node);
                }
                if (!found || found.length === 0) {
                    const obj = model.getObjectByName(sanitized) || model.getObjectByName(comp.glb_node);
                    if (obj) {
                        const descendantMeshes: THREE.Mesh[] = [];
                        obj.traverse((c) => {
                            if (c instanceof THREE.Mesh) descendantMeshes.push(c);
                        });
                        if (descendantMeshes.length > 0) found = descendantMeshes;
                    }
                }
                if (!found || found.length === 0) {
                    const shortName = comp.name || comp.glb_node.split("/").pop();
                    if (shortName) {
                        const sanitizedShort = THREE.PropertyBinding.sanitizeNodeName(shortName);
                        found = meshMap.get(sanitizedShort) || meshMap.get(shortName);
                    }
                }

                if (found && found.length > 0) {
                    meshes.push(...found);
                    totalResolved++;
                } else {
                    totalUnresolved++;
                }
            }
            zMap.set(zone.zone_id, meshes);
        }

        return zMap;
    }, [mapping, meshMap, model]);

    // Apply localized material highlighting based strictly on active alerts and selection
    useEffect(() => {
        const createdMaterials: THREE.Material[] = [];

        function createMaterial(colorHex: string, emissiveHex: string, intensity: number) {
            const mat = new THREE.MeshStandardMaterial({
                color: new THREE.Color(colorHex),
                emissive: new THREE.Color(emissiveHex),
                emissiveIntensity: intensity,
                roughness: 0.25,
                metalness: 0.1,
            });
            createdMaterials.push(mat);
            return mat;
        }

        // 1. Restore all original materials
        originalMaterials.forEach((origMat, mesh) => {
            mesh.material = origMat;
        });

        const redMat = createMaterial("#ef4444", "#dc2626", 0.85);
        const selectedMat = createMaterial("#38bdf8", "#0284c7", 0.65);

        // 2. Apply localized highlights
        if (mapping?.zones) {
            for (const zone of mapping.zones) {
                const zoneMeshes = zoneMeshesMap.get(zone.zone_id) || [];
                if (zoneMeshes.length === 0) continue;

                const isSelected = activeZoneId === zone.zone_id;
                const isViewingAll = activeZoneId === null;

                const backendZone = resolveBackendZone(zone, zones);
                const backendZoneId = backendZone?.id;

                const zoneAlerts = backendZoneId !== undefined
                    ? alerts.filter((a) => a.zone_id === backendZoneId && a.status === "ACTIVE")
                    : [];

                const hasActiveAlert = zoneAlerts.length > 0;

                if (hasActiveAlert) {
                    if (isViewingAll || isSelected) {
                        // Localized Anomaly Highlight: Highlight specific simulated damaged component in RED
                        const targetSensorKey = zone.zone_id === 1 ? "PZT-Z05" : "PZT-Z01";
                        const localizedInfo = SENSOR_LOCALIZED_COMPONENTS[targetSensorKey];

                        if (localizedInfo) {
                            const sanitizedNode = THREE.PropertyBinding.sanitizeNodeName(localizedInfo.glb_node);
                            const targetMeshes = meshMap.get(sanitizedNode) || meshMap.get(localizedInfo.glb_node) || [];

                            if (targetMeshes.length > 0) {
                                for (const m of targetMeshes) {
                                    m.material = redMat;
                                }
                            } else {
                                // Fallback if single node lookup missed
                                for (const m of zoneMeshes.slice(0, 1)) {
                                    m.material = redMat;
                                }
                            }
                        }
                    }
                } else if (isSelected) {
                    // Selection inspection mode for healthy zone: highlight zone group in cyan
                    for (const m of zoneMeshes) {
                        m.material = selectedMat;
                    }
                }
            }
        }

        // Cleanup on unmount or state change
        return () => {
            originalMaterials.forEach((origMat, mesh) => {
                mesh.material = origMat;
            });
            createdMaterials.forEach((mat) => mat.dispose());
        };
    }, [mapping, zoneMeshesMap, activeZoneId, zones, zoneHealthMap, alerts, originalMaterials, meshMap]);

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
}: DigitalTwinViewerProps) {
    const [mapping, setMapping] = useState<ZoneBimMappingFile | null>(null);
    const [zones, setZones] = useState<ZoneResponse[]>([]);
    const [alerts, setAlerts] = useState<AlertResponse[]>([]);
    const [zoneHealthMap, setZoneHealthMap] = useState<Record<number, ZoneHealthResponse>>({});
    const [activeZoneId, setActiveZoneId] = useState<number | null>(initialZoneId);
    const [hudCollapsed, setHudCollapsed] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // 1. Load static BIM mapping independently & immediately on mount
    useEffect(() => {
        let isMounted = true;
        async function loadBimMapping() {
            try {
                const mapRes = await fetch("/data/zone_bim_mapping.json");
                if (mapRes.ok) {
                    const mapData: ZoneBimMappingFile = await mapRes.json();
                    if (isMounted) {
                        setMapping(mapData);
                    }
                }
            } catch (err) {
                console.warn("[Aegis3D BIM Viewer] Failed to load static BIM mapping:", err);
            }
        }
        loadBimMapping();
        return () => {
            isMounted = false;
        };
    }, []);

    // 2. Poll live backend zones, alerts, and health independently
    useEffect(() => {
        let isMounted = true;

        async function fetchLiveBackendState() {
            try {
                const [zonesData, alertsData] = await Promise.all([
                    api.getZones().catch((err) => {
                        console.warn("Failed to fetch zones for BIM viewer:", err);
                        return [];
                    }),
                    api.getAlerts().catch((err) => {
                        console.warn("Failed to fetch alerts for BIM viewer:", err);
                        return [];
                    }),
                ]);

                const activeAlerts = alertsData.filter((a: AlertResponse) => a.status === "ACTIVE");

                const healthEntries: Record<number, ZoneHealthResponse> = {};
                await Promise.all(
                    zonesData.map(async (z) => {
                        try {
                            const h = await api.getZoneHealth(z.id);
                            healthEntries[z.id] = h;
                        } catch (hErr) {
                            console.warn(`Failed to fetch health for zone ${z.id}:`, hErr);
                        }
                    })
                );

                if (isMounted) {
                    setZones(zonesData);
                    setAlerts(activeAlerts);
                    setZoneHealthMap(healthEntries);
                    setLoading(false);
                }
            } catch (err: any) {
                if (isMounted) {
                    setError(err.message || "Failed to initialize Digital Twin viewer");
                    setLoading(false);
                }
            }
        }

        fetchLiveBackendState();

        const interval = setInterval(fetchLiveBackendState, 1500);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, []);

    // Synchronize initialZoneId when mapping and backend zones are loaded
    useEffect(() => {
        if (initialZoneId !== null && initialZoneId !== undefined && mapping && zones.length > 0) {
            const resolvedId = resolveMappingZoneId(initialZoneId, mapping, zones);
            if (resolvedId !== null) {
                setActiveZoneId(resolvedId);
            }
        }
    }, [initialZoneId, mapping, zones]);

    const totalMappedComponents = useMemo(() => {
        if (!mapping?.zones) return 0;
        return mapping.zones.reduce((sum, z) => sum + (z.resolved_component_count || z.components.length), 0);
    }, [mapping]);

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                background: "#020617",
                fontFamily: "system-ui, -apple-system, sans-serif",
                overflow: "hidden",
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
                    background: "linear-gradient(to bottom, rgba(2,6,23,0.95), rgba(2,6,23,0.65))",
                    borderBottom: "1px solid rgba(148,163,184,0.15)",
                    backdropFilter: "blur(10px)",
                }}
            >
                {/* Left Branding */}
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
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
                            background: "rgba(148,163,184,0.3)",
                        }}
                    />
                    <div style={{ fontSize: 14, color: "#94a3b8" }}>
                        Structural Digital Twin & Health Visualization
                    </div>
                </div>

                {/* Right Close Button */}
                <button
                    onClick={onClose}
                    style={{
                        border: "1px solid rgba(148,163,184,0.25)",
                        background: "rgba(15,23,42,0.8)",
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
                className="custom-scrollbar"
                style={{
                    position: "absolute",
                    top: 76,
                    left: 20,
                    zIndex: 10,
                    width: 360,
                    maxWidth: "calc(100vw - 40px)",
                    maxHeight: "calc(100dvh - 96px)",
                    overflowY: "auto",
                    background: "rgba(15, 23, 42, 0.88)",
                    backdropFilter: "blur(12px)",
                    border: "1px solid rgba(148, 163, 184, 0.2)",
                    borderRadius: 10,
                    padding: 16,
                    paddingRight: 8,
                    color: "#f1f5f9",
                    boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.6)",
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <h2 style={{ fontSize: 14, fontWeight: 700, color: "#67e8f9", margin: 0, textTransform: "uppercase" }}>
                        Monitored BIM Zones
                    </h2>
                    <span style={{ fontSize: 11, color: "#94a3b8", background: "rgba(51, 65, 85, 0.6)", padding: "2px 6px", borderRadius: 4 }}>
                        {mapping ? `${totalMappedComponents} elements mapped` : "Loading BIM mapping..."}
                    </span>
                </div>
                <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 12px 0", lineHeight: 1.4 }}>
                    Inferred spatial component groups linked to live PZT telemetry.
                </p>

                {/* View Mode Selector */}
                <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
                    <button
                        onClick={() => setActiveZoneId(null)}
                        style={{
                            flex: 1,
                            padding: "6px 8px",
                            fontSize: 11,
                            fontWeight: 600,
                            borderRadius: 6,
                            border: activeZoneId === null ? "1px solid #38bdf8" : "1px solid rgba(148, 163, 184, 0.2)",
                            background: activeZoneId === null ? "rgba(56, 189, 248, 0.2)" : "rgba(30, 41, 59, 0.6)",
                            color: activeZoneId === null ? "#38bdf8" : "#cbd5e1",
                            cursor: "pointer",
                        }}
                    >
                        All Anomaly Highlights
                    </button>
                    {mapping?.zones.map((z) => (
                        <button
                            key={z.zone_id}
                            onClick={() => setActiveZoneId(z.zone_id)}
                            style={{
                                flex: 1,
                                padding: "6px 8px",
                                fontSize: 11,
                                fontWeight: 600,
                                borderRadius: 6,
                                border: activeZoneId === z.zone_id ? "1px solid #67e8f9" : "1px solid rgba(148, 163, 184, 0.2)",
                                background: activeZoneId === z.zone_id ? "rgba(34, 211, 238, 0.2)" : "rgba(30, 41, 59, 0.6)",
                                color: activeZoneId === z.zone_id ? "#67e8f9" : "#cbd5e1",
                                cursor: "pointer",
                            }}
                        >
                            Zone {z.zone_id}
                        </button>
                    ))}
                </div>

                {/* Zone Cards */}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {mapping?.zones.map((zone) => {
                        const backendZone = resolveBackendZone(zone, zones);
                        const backendZoneId = backendZone?.id;
                        const health = backendZoneId !== undefined ? zoneHealthMap[backendZoneId] : undefined;
                        const zoneAlerts = backendZoneId !== undefined
                            ? alerts.filter((a) => a.zone_id === backendZoneId && a.status === "ACTIVE")
                            : [];
                        const isSelected = activeZoneId === zone.zone_id;
                        const hasActiveAlert = zoneAlerts.length > 0;
                        const isCritical =
                            hasActiveAlert ||
                            health?.status === "HIGH_PRIORITY_INSPECTION" ||
                            health?.status === "INSPECTION_ADVISED";
                        const isWarning =
                            !isCritical && (
                                zoneAlerts.some((a) => a.severity === "MEDIUM" || a.severity === "LOW") ||
                                health?.status === "MONITOR"
                            );

                        const badgeText = hasActiveAlert
                            ? (health?.status && health.status !== "NORMAL" ? health.status : "ALERT ACTIVE")
                            : (health?.status ?? "NORMAL");

                        const badgeBg = isCritical ? "#dc2626" : isWarning ? "#d97706" : "#059669";

                        const sensorKey = zone.zone_id === 1 ? "PZT-Z05" : "PZT-Z01";
                        const locInfo = SENSOR_LOCALIZED_COMPONENTS[sensorKey];

                        return (
                            <div
                                key={zone.zone_id}
                                onClick={() => setActiveZoneId(zone.zone_id)}
                                style={{
                                    border: isSelected
                                        ? "1px solid #38bdf8"
                                        : isCritical
                                        ? "1px solid rgba(239, 68, 68, 0.5)"
                                        : "1px solid rgba(75, 85, 99, 0.4)",
                                    background: isSelected
                                        ? "rgba(30, 58, 138, 0.3)"
                                        : isCritical
                                        ? "rgba(220, 38, 38, 0.15)"
                                        : "rgba(30, 41, 59, 0.5)",
                                    borderRadius: 8,
                                    padding: 12,
                                    cursor: "pointer",
                                    transition: "all 0.15s ease",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                                    <div style={{ fontWeight: 600, fontSize: 13, color: "#f8fafc" }}>
                                        {zone.zone_name}
                                    </div>
                                    <span
                                        style={{
                                            fontSize: 10,
                                            fontWeight: 700,
                                            padding: "2px 6px",
                                            borderRadius: 4,
                                            background: badgeBg,
                                            color: "#ffffff",
                                        }}
                                    >
                                        {badgeText}
                                    </span>
                                </div>

                                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 6 }}>
                                    Storey: <span style={{ color: "#e2e8f0" }}>{zone.mapping_rule.storey_name}</span> · Type:{" "}
                                    <span style={{ color: "#e2e8f0" }}>{zone.mapping_rule.component_type}</span> ({zone.components.length} elements)
                                </div>

                                {health?.score !== undefined && (
                                    <div style={{ fontSize: 11, color: "#cbd5e1", marginBottom: 6, display: "flex", justifyContent: "space-between" }}>
                                        <span>Structural Health Indicator (SHI):</span>
                                        <span style={{ fontWeight: 700, color: isCritical ? "#f87171" : isWarning ? "#fbbf24" : "#34d399" }}>
                                            {health.score.toFixed(1)} / 100
                                        </span>
                                    </div>
                                )}

                                {hasActiveAlert && locInfo && (
                                    <div
                                        style={{
                                            background: "rgba(220, 38, 38, 0.2)",
                                            border: "1px solid rgba(239, 68, 68, 0.4)",
                                            borderRadius: 6,
                                            padding: "6px 8px",
                                            marginTop: 6,
                                            fontSize: 11,
                                            color: "#fecaca",
                                        }}
                                    >
                                        <div style={{ fontWeight: 700, color: "#fca5a5", marginBottom: 2 }}>
                                            ⚠️ {zoneAlerts[0].title}
                                        </div>
                                        <div style={{ fontSize: 10, color: "#e2e8f0", marginBottom: 4 }}>
                                            {zoneAlerts[0].message}
                                        </div>
                                        <div style={{ fontSize: 10, color: "#fef08a", fontFamily: "ui-monospace, SFMono-Regular, monospace" }}>
                                            <strong>Simulated Affected Component:</strong>
                                            <br />
                                            {locInfo.name} (1 / {zone.components.length} elements)
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
                        background: "rgba(30, 41, 59, 0.4)",
                        border: "1px solid rgba(148, 163, 184, 0.15)",
                        borderRadius: 6,
                        fontSize: 10,
                        color: "#94a3b8",
                        lineHeight: 1.4,
                    }}
                >
                    <span style={{ fontWeight: 700, color: "#cbd5e1" }}>Prototype Disclaimer:</span> Active anomalies highlight the simulated affected structural component derived from PZT guided-wave propagation physics. Unaffected structural elements remain neutral.
                </div>
            </div>

            {/* =====================================================
                RIGHT HUD: TELEMETRY & SENSOR FREQUENCY GRAPHS
            ===================================================== */}
            <div
                style={{
                    position: "absolute",
                    top: 76,
                    right: 20,
                    zIndex: 20,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-end",
                    pointerEvents: "auto",
                }}
            >
                <button
                    onClick={() => setHudCollapsed(!hudCollapsed)}
                    style={{
                        background: "rgba(15, 23, 42, 0.85)",
                        border: "1px solid rgba(148, 163, 184, 0.25)",
                        color: hudCollapsed ? "#94a3b8" : "#34d399",
                        padding: "6px 12px",
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: "pointer",
                        backdropFilter: "blur(8px)",
                        boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
                        marginBottom: 8,
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                    }}
                >
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: hudCollapsed ? "#64748b" : "#34d399" }} />
                    {hudCollapsed ? "SHOW TELEMETRY HUD ▶" : "HIDE TELEMETRY HUD ▼"}
                </button>

                <div
                    className="custom-scrollbar"
                    style={{
                        display: hudCollapsed ? "none" : "block",
                        width: 380,
                        maxWidth: "calc(100vw - 40px)",
                        maxHeight: "calc(100dvh - 140px)",
                        overflowY: "auto",
                        background: "rgba(15, 23, 42, 0.92)",
                        backdropFilter: "blur(12px)",
                        border: "1px solid rgba(148, 163, 184, 0.2)",
                        borderRadius: 10,
                        padding: 14,
                        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.6)",
                    }}
                >
                    <TelemetryHUD
                        activeZoneId={activeZoneId}
                        onSelectZone={setActiveZoneId}
                    />
                </div>
            </div>

            {/* =====================================================
                BOTTOM CONTROLS / OVERLAY STATUS
            ===================================================== */}
            <div
                style={{
                    position: "absolute",
                    bottom: 20,
                    left: 20,
                    zIndex: 10,
                    background: "rgba(15, 23, 42, 0.75)",
                    backdropFilter: "blur(8px)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 6,
                    padding: "6px 12px",
                    fontSize: 11,
                    color: "#94a3b8",
                    pointerEvents: "none",
                }}
            >
                <div>Left click · Rotate</div>
                <div>Middle / Right click · Pan</div>
                <div>Scroll · Zoom</div>
            </div>

            <div
                style={{
                    position: "absolute",
                    bottom: 20,
                    right: 20,
                    zIndex: 10,
                    background: "rgba(15, 23, 42, 0.75)",
                    backdropFilter: "blur(8px)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 6,
                    padding: "6px 12px",
                    fontSize: 11,
                    color: "#94a3b8",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}
            >
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981" }} />
                <span>Digital Twin Synced · Live Health Connected</span>
            </div>

            {/* =====================================================
                THREE.JS CANVAS VIEWPORT
            ===================================================== */}
            <Canvas
                camera={{
                    position: [55, 40, 65],
                    fov: 40,
                    near: 0.1,
                    far: 1000,
                }}
                style={{ width: "100%", height: "100%" }}
                gl={{
                    antialias: true,
                    alpha: false,
                    powerPreference: "high-performance",
                }}
            >
                <color attach="background" args={["#020617"]} />
                <ambientLight intensity={1.2} />
                <directionalLight position={[60, 90, 40]} intensity={1.8} castShadow />
                <directionalLight position={[-60, 50, -40]} intensity={0.9} />
                <pointLight position={[0, 30, 0]} intensity={0.6} />

                <BuildingModel
                    mapping={mapping}
                    activeZoneId={activeZoneId}
                    zones={zones}
                    zoneHealthMap={zoneHealthMap}
                    alerts={alerts}
                    onSelectZone={(id) => setActiveZoneId(id)}
                />

                <StaticFloor />

                <OrbitControls
                    enableDamping
                    dampingFactor={0.08}
                    minDistance={5}
                    maxDistance={350}
                    maxPolarAngle={Math.PI / 2 + 0.05}
                />
            </Canvas>
        </div>
    );
}