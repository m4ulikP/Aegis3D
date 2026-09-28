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

/* =========================================================
   BUILDING MODEL WITH DYNAMIC MATERIAL HIGHLIGHTING
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

    // Resolve mapped components in zone_bim_mapping.json to Three.js meshes
    const zoneMeshesMap = useMemo(() => {
        const zMap = new Map<number, THREE.Mesh[]>();
        if (!mapping?.zones) return zMap;

        let totalResolved = 0;
        let totalUnresolved = 0;

        for (const zone of mapping.zones) {
            const meshes: THREE.Mesh[] = [];
            for (const comp of zone.components) {
                const found = meshMap.get(comp.glb_node);
                if (found && found.length > 0) {
                    meshes.push(...found);
                    totalResolved++;
                } else {
                    totalUnresolved++;
                    console.warn(`[Aegis3D BIM Viewer] Unresolved GLB node: ${comp.glb_node}`);
                }
            }
            zMap.set(zone.zone_id, meshes);
        }

        console.info(
            `[Aegis3D BIM Viewer] Scene resolved ${totalResolved} component meshes (${totalUnresolved} unresolved)`
        );
        return zMap;
    }, [mapping, meshMap]);

    // Apply reversible material highlighting based on live health and active selection
    useEffect(() => {
        const createdMaterials: THREE.Material[] = [];

        function createHighlightMaterial(type: "critical" | "warning" | "selected") {
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
            } else {
                // Active selection of healthy zone
                mat = new THREE.MeshStandardMaterial({
                    color: new THREE.Color("#38bdf8"),
                    emissive: new THREE.Color("#0284c7"),
                    emissiveIntensity: 0.65,
                    roughness: 0.3,
                    metalness: 0.15,
                });
            }
            createdMaterials.push(mat);
            return mat;
        }

        // 1. Restore all original materials
        originalMaterials.forEach((origMat, mesh) => {
            mesh.material = origMat;
        });

        // 2. Apply highlights to mapped zone groups
        if (mapping?.zones) {
            for (const zone of mapping.zones) {
                const meshes = zoneMeshesMap.get(zone.zone_id) || [];
                if (meshes.length === 0) continue;

                const isSelected = activeZoneId === zone.zone_id;
                const isViewingAll = activeZoneId === null;

                const backendZone = resolveBackendZone(zone, zones);
                const backendZoneId = backendZone?.id;

                const zoneAlerts = backendZoneId !== undefined
                    ? alerts.filter((a) => a.zone_id === backendZoneId && a.status === "ACTIVE")
                    : [];
                const health = backendZoneId !== undefined ? zoneHealthMap[backendZoneId] : undefined;

                const hasCriticalAlert = zoneAlerts.some(
                    (a) => a.severity === "CRITICAL" || a.severity === "HIGH"
                );
                const hasWarningAlert = zoneAlerts.some(
                    (a) => a.severity === "MEDIUM" || a.severity === "LOW"
                );

                const isCriticalHealth =
                    health?.status === "HIGH_PRIORITY_INSPECTION" ||
                    health?.status === "INSPECTION_ADVISED";
                const isWarningHealth = health?.status === "MONITOR";

                let highlightType: "critical" | "warning" | "selected" | null = null;

                if (hasCriticalAlert || isCriticalHealth) {
                    highlightType = "critical";
                } else if (hasWarningAlert || isWarningHealth) {
                    highlightType = "warning";
                } else if (isSelected) {
                    highlightType = "selected";
                }

                // If user selected a specific zone, only highlight that zone unless in 'view all' mode
                if (highlightType) {
                    if (isViewingAll || isSelected) {
                        const mat = createHighlightMaterial(highlightType);
                        for (const mesh of meshes) {
                            mesh.material = mat;
                        }
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
    }, [mapping, zoneMeshesMap, activeZoneId, zones, zoneHealthMap, alerts, originalMaterials]);

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

    // Load canonical mapping and live monitoring telemetry
    useEffect(() => {
        let isMounted = true;
        let pollInterval: NodeJS.Timeout | null = null;

        async function initViewerData() {
            try {
                // 1. Fetch canonical Step 1 mapping artifact
                const mapRes = await fetch("/data/zone_bim_mapping.json");
                if (!mapRes.ok) {
                    throw new Error(`Failed to load zone BIM mapping: HTTP ${mapRes.status}`);
                }
                const mapData: ZoneBimMappingFile = await mapRes.json();

                // 2. Fetch live zones and active alerts
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

                // 3. Fetch detailed health status for each zone
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
                    setMapping(mapData);
                    setZones(zonesData);
                    setAlerts(alertsData);
                    setZoneHealthMap(healthEntries);
                    setLoading(false);

                    // 4. Start periodic background polling (every 1.5s) to reflect real-time simulator events
                    pollInterval = setInterval(async () => {
                        if (!isMounted) return;
                        try {
                            const [freshAlerts, freshZones] = await Promise.all([
                                api.getAlerts().catch(() => []),
                                api.getZones().catch(() => []),
                            ]);
                            const freshHealth: Record<number, ZoneHealthResponse> = {};
                            const targetZones = freshZones.length > 0 ? freshZones : zonesData;
                            await Promise.all(
                                targetZones.map(async (z) => {
                                    try {
                                        const h = await api.getZoneHealth(z.id);
                                        freshHealth[z.id] = h;
                                    } catch {
                                        // Ignore polling failures
                                    }
                                })
                            );
                            if (isMounted) {
                                setAlerts(freshAlerts);
                                if (freshZones.length > 0) setZones(freshZones);
                                if (Object.keys(freshHealth).length > 0) {
                                    setZoneHealthMap(freshHealth);
                                }
                            }
                        } catch {
                            // Non-blocking poll failure
                        }
                    }, 1500);
                }
            } catch (err: any) {
                if (isMounted) {
                    console.error("[Aegis3D BIM Viewer] Initialization error:", err);
                    setError(err.message || "Failed to initialize Digital Twin viewer");
                    setLoading(false);
                }
            }
        }

        initViewerData();

        return () => {
            isMounted = false;
            if (pollInterval) clearInterval(pollInterval);
        };
    }, []);

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
                        {totalMappedComponents} elements mapped
                    </span>
                </div>
                <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 12px 0", lineHeight: 1.4 }}>
                    Option 1: Inferred spatial component groups linked to live telemetry.
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
                        const isCritical =
                            zoneAlerts.some((a) => a.severity === "CRITICAL" || a.severity === "HIGH") ||
                            health?.status === "HIGH_PRIORITY_INSPECTION" ||
                            health?.status === "INSPECTION_ADVISED";
                        const isWarning =
                            zoneAlerts.some((a) => a.severity === "MEDIUM" || a.severity === "LOW") ||
                            health?.status === "MONITOR";

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
                                            background: isCritical ? "#dc2626" : isWarning ? "#d97706" : "#059669",
                                            color: "#ffffff",
                                        }}
                                    >
                                        {isCritical && zoneAlerts.length > 0 && (!health || health.status === "NORMAL")
                                            ? "ALERT ACTIVE"
                                            : (health?.status ?? (isCritical ? "ALERT ACTIVE" : "NORMAL"))}
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

                                {zoneAlerts.length > 0 && (
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
                                        <div style={{ fontSize: 10, color: "#e2e8f0" }}>
                                            {zoneAlerts[0].message}
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
                    <span style={{ fontWeight: 700, color: "#cbd5e1" }}>Prototype Disclaimer:</span> Zone anomalies are visually highlighted across the mapped structural framing group. This indicates monitoring state and does not establish certified structural damage or millimeter crack localization.
                </div>
            </div>

            {/* =====================================================
                RIGHT HUD: MISSION-CRITICAL TELEMETRY OPERATIONS
            ===================================================== */}
            <TelemetryHUD
                activeZoneId={activeZoneId}
                onSelectZone={(selectedId) => {
                    const foundByBackend = mapping?.zones.find((mz) => {
                        const bz = resolveBackendZone(mz, zones);
                        return bz?.id === selectedId;
                    });
                    if (foundByBackend) {
                        setActiveZoneId(foundByBackend.zone_id);
                    } else {
                        setActiveZoneId(selectedId);
                    }
                }}
                onFocusAlert={(alert) => {
                    const mZone = mapping?.zones.find((mz) => {
                        const bz = resolveBackendZone(mz, zones);
                        return bz?.id === alert.zone_id;
                    });
                    if (mZone) {
                        setActiveZoneId(mZone.zone_id);
                    }
                }}
                collapsed={hudCollapsed}
                onToggleCollapse={() => setHudCollapsed(!hudCollapsed)}
            />

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
                <color attach="background" args={["#020617"]} />

                {/* Lighting */}
                <ambientLight intensity={0.7} />
                <hemisphereLight args={["#dbeafe", "#0f172a", 1.2]} />
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
                    activeZoneId={activeZoneId}
                    zones={zones}
                    zoneHealthMap={zoneHealthMap}
                    alerts={alerts}
                    onSelectZone={(id) => setActiveZoneId(id)}
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
                    background: "rgba(15,23,42,0.8)",
                    border: "1px solid rgba(148,163,184,0.15)",
                    borderRadius: 8,
                    color: "#94a3b8",
                    fontSize: 12,
                    backdropFilter: "blur(8px)",
                }}
            >
                <div>Left click · Rotate</div>
                <div>Middle / Right click · Pan</div>
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
                    background: "rgba(15,23,42,0.8)",
                    border: "1px solid rgba(148,163,184,0.15)",
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
                        background: loading ? "#f59e0b" : error ? "#ef4444" : "#22c55e",
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