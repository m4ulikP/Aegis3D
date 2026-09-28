"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
    AlertResponse,
    HealthStatus,
    TelemetryLatestResponse,
    ZoneHealthResponse,
    ZoneResponse,
} from "@/types/api";
import { theme } from "@/lib/theme";
import SignalWaveform from "./SignalWaveform";
import ProcessingPipelineStrip from "./ProcessingPipelineStrip";
import TelemetryProcessingInspector from "./TelemetryProcessingInspector";

interface TelemetryHUDProps {
    activeZoneId: number | null;
    onSelectZone?: (zoneId: number) => void;
    onFocusAlert?: (alert: AlertResponse) => void;
    collapsed?: boolean;
    onToggleCollapse?: () => void;
}

const AVAILABLE_SENSORS = [
    { id: null, label: "Auto (Latest)" },
    { id: "PZT-Z1-01", label: "PZT-Z1-01" },
    { id: "PZT-Z1-02", label: "PZT-Z1-02" },
    { id: "PZT-Z2-01", label: "PZT-Z2-01" },
    { id: "PZT-Z2-02", label: "PZT-Z2-02" },
];

export default function TelemetryHUD({
    activeZoneId,
    onSelectZone,
    onFocusAlert,
    collapsed = false,
    onToggleCollapse,
}: TelemetryHUDProps) {
    const [telemetry, setTelemetry] = useState<TelemetryLatestResponse | null>(null);
    const [zones, setZones] = useState<ZoneResponse[]>([]);
    const [alerts, setAlerts] = useState<AlertResponse[]>([]);
    const [zoneHealth, setZoneHealth] = useState<ZoneHealthResponse | null>(null);
    const [isLiveConnected, setIsLiveConnected] = useState<boolean>(true);
    const [lastSyncTime, setLastSyncTime] = useState<string>("Initializing...");
    const [selectedSensorId, setSelectedSensorId] = useState<string | null>(null);
    const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);

    // Fetch live backend data
    const refreshData = useCallback(async () => {
        try {
            const [latestTel, alertsData, zonesData] = await Promise.all([
                api.getLatestTelemetry(selectedSensorId || undefined).catch((err) => {
                    console.warn("Failed to poll telemetry/latest:", err);
                    return null;
                }),
                api.getAlerts().catch((err) => {
                    console.warn("Failed to poll alerts:", err);
                    return [];
                }),
                api.getZones().catch((err) => {
                    console.warn("Failed to poll zones:", err);
                    return [];
                }),
            ]);

            setTelemetry(latestTel);
            setAlerts(alertsData);
            setZones(zonesData);
            setIsLiveConnected(true);

            const now = new Date();
            setLastSyncTime(now.toTimeString().split(" ")[0] + " UTC");

            // If a zone is active, get its detailed health
            const targetZoneId = activeZoneId ?? (latestTel?.zone_id ?? (zonesData[0]?.id ?? 1));
            if (targetZoneId) {
                try {
                    const health = await api.getZoneHealth(targetZoneId);
                    setZoneHealth(health);
                } catch {
                    // Ignore non-fatal health error
                }
            }
        } catch {
            setIsLiveConnected(false);
        }
    }, [activeZoneId, selectedSensorId]);

    // Polling effect: lightweight 1.5s interval, cleaned up on unmount
    useEffect(() => {
        let isMounted = true;
        refreshData();

        const intervalId = setInterval(() => {
            if (isMounted) {
                refreshData();
            }
        }, 1500);

        return () => {
            isMounted = false;
            clearInterval(intervalId);
        };
    }, [refreshData]);

    if (isInspectorOpen) {
        return (
            <TelemetryProcessingInspector
                telemetry={telemetry}
                onClose={() => setIsInspectorOpen(false)}
            />
        );
    }

    if (collapsed) {
        return (
            <button
                onClick={onToggleCollapse}
                style={{
                    position: "absolute",
                    top: 76,
                    right: 20,
                    zIndex: 20,
                    padding: "8px 12px",
                    background: theme.surfaces.panel,
                    backdropFilter: "blur(10px)",
                    border: `1px solid ${theme.surfaces.border}`,
                    borderRadius: 8,
                    color: theme.text.primary,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
                }}
            >
                <div
                    style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: isLiveConnected ? "#22c55e" : "#ef4444",
                    }}
                />
                <span>SHOW TELEMETRY HUD ◀</span>
            </button>
        );
    }

    const currentZoneName =
        telemetry?.zone_name ||
        zones.find((z) => z.id === activeZoneId)?.name ||
        "Zone 1 - Main Deck Girder";
    const currentSensorId = telemetry?.sensor_id || selectedSensorId || "PZT-Z1-01";
    const hasAnomaly = telemetry?.events.some((e) => e.is_anomalous) || false;
    const hasEvent = (telemetry?.events_detected || 0) > 0;

    return (
        <aside
            className="custom-scrollbar"
            style={{
                position: "absolute",
                top: 76,
                right: 20,
                zIndex: 20,
                width: 380,
                maxWidth: "calc(100vw - 40px)",
                maxHeight: "calc(100dvh - 96px)",
                overflowY: "auto",
                background: theme.surfaces.panel,
                backdropFilter: "blur(14px)",
                border: `1px solid ${hasAnomaly ? theme.surfaces.borderCritical : theme.surfaces.border}`,
                borderRadius: 10,
                padding: "14px 16px",
                paddingRight: "8px",
                color: theme.text.primary,
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                fontFamily: theme.typography.fontSans,
                transition: "border-color 0.2s ease",
            }}
            aria-label="Mission-Critical Telemetry Engineering HUD"
        >
            {/* Top Bar / Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <h2
                            style={{
                                margin: 0,
                                fontSize: 13,
                                fontWeight: 700,
                                letterSpacing: "0.06em",
                                color: theme.text.accent,
                                textTransform: "uppercase",
                            }}
                        >
                            Telemetry Operations HUD
                        </h2>
                        <span
                            style={{
                                fontSize: 9,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                padding: "1px 5px",
                                borderRadius: 4,
                                background: isLiveConnected ? theme.status.normal.bg : theme.status.critical.bg,
                                color: isLiveConnected ? theme.status.normal.text : theme.status.critical.text,
                                border: `1px solid ${isLiveConnected ? theme.status.normal.border : theme.status.critical.border}`,
                            }}
                        >
                            {isLiveConnected ? "LIVE 1.5s" : "DISCONNECTED"}
                        </span>
                    </div>
                    <div
                        style={{
                            fontSize: 10,
                            color: theme.text.muted,
                            fontFamily: theme.typography.fontMono,
                            marginTop: 2,
                        }}
                    >
                        Sync: {lastSyncTime} · Source: Python Simulator
                    </div>
                </div>

                {onToggleCollapse && (
                    <button
                        onClick={onToggleCollapse}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: theme.text.muted,
                            cursor: "pointer",
                            fontSize: 12,
                            padding: "2px 4px",
                        }}
                        title="Collapse Telemetry HUD"
                    >
                        ✕
                    </button>
                )}
            </div>

            {/* Sensor Selection Bar */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    flexWrap: "wrap",
                    background: "rgba(15, 23, 42, 0.4)",
                    padding: "6px 8px",
                    borderRadius: 6,
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                }}
            >
                <span
                    style={{
                        fontSize: 9,
                        fontFamily: theme.typography.fontMono,
                        color: theme.text.muted,
                        marginRight: 2,
                    }}
                >
                    NODE:
                </span>
                {AVAILABLE_SENSORS.map((s) => {
                    const isSelected = selectedSensorId === s.id;
                    return (
                        <button
                            key={s.label}
                            onClick={() => setSelectedSensorId(s.id)}
                            style={{
                                fontSize: 9,
                                fontFamily: theme.typography.fontMono,
                                padding: "3px 6px",
                                borderRadius: 4,
                                border: isSelected
                                    ? "1px solid #38bdf8"
                                    : "1px solid rgba(148, 163, 184, 0.2)",
                                background: isSelected
                                    ? "rgba(56, 189, 248, 0.2)"
                                    : "rgba(15, 23, 42, 0.5)",
                                color: isSelected ? "#38bdf8" : "#94a3b8",
                                cursor: "pointer",
                                fontWeight: isSelected ? 700 : 400,
                            }}
                        >
                            {s.label}
                        </button>
                    );
                })}
            </div>

            {/* Sensor & Zone Context Strip */}
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: `1px solid ${theme.surfaces.border}`,
                    borderRadius: 8,
                    padding: "10px 12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <div style={{ fontWeight: 700, fontSize: 13, color: "#f8fafc" }}>
                        {currentSensorId}
                    </div>
                    <div
                        style={{
                            fontSize: 11,
                            color: theme.text.secondary,
                            maxWidth: 200,
                            textAlign: "right",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                        }}
                    >
                        {currentZoneName}
                    </div>
                </div>

                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr 1fr",
                        gap: 6,
                        fontFamily: theme.typography.fontMono,
                        fontSize: 10,
                        color: theme.text.muted,
                        borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                        paddingTop: 6,
                    }}
                >
                    <div>
                        RATE:{" "}
                        <strong style={{ color: theme.text.primary }}>
                            {telemetry?.sample_rate_hz ?? 1000} Hz
                        </strong>
                    </div>
                    <div>
                        SAMPLES:{" "}
                        <strong style={{ color: theme.text.primary }}>
                            {telemetry?.samples_count ?? 0}
                        </strong>
                    </div>
                    <div>
                        SEQ:{" "}
                        <strong style={{ color: theme.text.primary }}>
                            #{telemetry?.sequence ?? 0}
                        </strong>
                    </div>
                </div>
            </div>

            {/* Awaiting Telemetry Notice (if no snapshot cached yet) */}
            {!telemetry && (
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.5)",
                        border: "1px dashed rgba(148, 163, 184, 0.25)",
                        borderRadius: 8,
                        padding: "12px",
                        textAlign: "center",
                        fontFamily: theme.typography.fontMono,
                        fontSize: 11,
                        color: theme.text.muted,
                    }}
                >
                    <div style={{ color: "#38bdf8", fontWeight: 700, marginBottom: 4 }}>
                        AWAITING SENSOR TELEMETRY
                    </div>
                    <div style={{ fontSize: 10, color: "#94a3b8" }}>
                        No snapshot cached for {selectedSensorId || "this sensor node"}.
                    </div>
                    <div style={{ fontSize: 9, color: "#64748b", marginTop: 4 }}>
                        Transmit from Virtual Sensor Simulator on Laptop 2
                    </div>
                </div>
            )}

            {/* Real Waveform Trace */}
            <SignalWaveform
                samples={telemetry?.samples ?? []}
                sampleRateHz={telemetry?.sample_rate_hz ?? 1000}
                detectionThreshold={telemetry?.detection_threshold ?? 1.0}
                isAnomalous={hasAnomaly}
                hasEvent={hasEvent}
                sensorId={currentSensorId}
                status={telemetry?.status}
                height={115}
            />

            {/* Processing Pipeline Progression Strip */}
            <ProcessingPipelineStrip
                telemetry={telemetry}
                onInspect={() => setIsInspectorOpen(true)}
            />


            {/* Structural Health (SHI) Card */}
            {zoneHealth && (
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.6)",
                        border: `1px solid ${theme.surfaces.border}`,
                        borderRadius: 8,
                        padding: "10px 12px",
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: theme.text.secondary }}>
                            Structural Health Indicator (SHI)
                        </span>
                        <span
                            style={{
                                fontFamily: theme.typography.fontMono,
                                fontSize: 13,
                                fontWeight: 700,
                                color:
                                    zoneHealth.status === "HIGH_PRIORITY_INSPECTION" ||
                                    zoneHealth.status === "INSPECTION_ADVISED"
                                        ? theme.status.critical.text
                                        : zoneHealth.status === "MONITOR"
                                        ? theme.status.warning.text
                                        : theme.status.normal.text,
                            }}
                        >
                            {zoneHealth.score.toFixed(1)} / 100
                        </span>
                    </div>

                    {/* Score Bar */}
                    <div
                        style={{
                            width: "100%",
                            height: 6,
                            background: "rgba(30, 41, 59, 0.8)",
                            borderRadius: 3,
                            overflow: "hidden",
                        }}
                    >
                        <div
                            style={{
                                width: `${Math.min(100, Math.max(0, zoneHealth.score))}%`,
                                height: "100%",
                                background:
                                    zoneHealth.status === "HIGH_PRIORITY_INSPECTION" ||
                                    zoneHealth.status === "INSPECTION_ADVISED"
                                        ? theme.status.critical.solid
                                        : zoneHealth.status === "MONITOR"
                                        ? theme.status.warning.solid
                                        : theme.status.normal.solid,
                                transition: "width 0.4s ease",
                            }}
                        />
                    </div>

                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: 10,
                            color: theme.text.muted,
                            fontFamily: theme.typography.fontMono,
                        }}
                    >
                        <span>Rating: {zoneHealth.status}</span>
                        <span>Trend: {zoneHealth.trend}</span>
                    </div>
                </div>
            )}

            {/* Active System Alerts */}
            {alerts.length > 0 && (
                <div
                    style={{
                        background: theme.status.critical.bg,
                        border: `1px solid ${theme.status.critical.border}`,
                        borderRadius: 8,
                        padding: "10px 12px",
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            fontSize: 11,
                            fontWeight: 700,
                            color: theme.status.critical.text,
                        }}
                    >
                        <span>⚠️ ACTIVE ALERTS ({alerts.length})</span>
                    </div>
                    {alerts.slice(0, 2).map((a) => (
                        <div
                            key={a.id}
                            onClick={() => {
                                onSelectZone?.(a.zone_id);
                                onFocusAlert?.(a);
                            }}
                            style={{
                                cursor: "pointer",
                                padding: "6px 8px",
                                background: "rgba(15, 23, 42, 0.5)",
                                borderRadius: 6,
                                fontSize: 11,
                                transition: "background 0.15s ease",
                            }}
                            title="Click to focus affected zone in 3D"
                        >
                            <div style={{ fontWeight: 600, color: "#fecaca" }}>
                                {a.severity} · {a.title}
                            </div>
                            <div style={{ fontSize: 10, color: "#e2e8f0", marginTop: 2 }}>
                                {a.message}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Engineering Disclaimer */}
            <div
                style={{
                    fontSize: 9,
                    color: theme.text.muted,
                    lineHeight: 1.3,
                    borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                    paddingTop: 6,
                }}
            >
                Aegis3D Structural Health Indicator represents algorithmic evaluation of sensor telemetry. Does not constitute certified structural failure certification.
            </div>
        </aside>
    );
}
