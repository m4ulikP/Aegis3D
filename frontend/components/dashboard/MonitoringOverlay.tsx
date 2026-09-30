"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
    AlertResponse,
    HealthSummaryResponse,
    TelemetryLatestResponse,
    ZoneResponse,
} from "@/types/api";
import { theme } from "@/lib/theme";

export default function MonitoringOverlay() {
    const [summary, setSummary] = useState<HealthSummaryResponse | null>(null);
    const [zones, setZones] = useState<ZoneResponse[]>([]);
    const [alerts, setAlerts] = useState<AlertResponse[]>([]);
    const [latestTelemetry, setLatestTelemetry] = useState<TelemetryLatestResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const openDigitalTwin = (zoneId?: number) => {
        if (typeof window !== "undefined") {
            window.dispatchEvent(
                new CustomEvent("aegis3d:open-digital-twin", {
                    detail: { zoneId },
                })
            );
        }
    };

    useEffect(() => {
        let isMounted = true;

        async function loadMonitoringData() {
            try {
                const [summaryData, zonesData, alertsData, telData] = await Promise.all([
                    api.getHealthSummary().catch((err) => {
                        console.warn("Failed to fetch health summary:", err);
                        return null;
                    }),
                    api.getZones().catch((err) => {
                        console.warn("Failed to fetch zones:", err);
                        return [];
                    }),
                    api.getAlerts().catch((err) => {
                        console.warn("Failed to fetch alerts:", err);
                        return [];
                    }),
                    api.getLatestTelemetry().catch(() => null),
                ]);

                if (isMounted) {
                    const activeAlerts = alertsData.filter((a: AlertResponse) => a.status === "ACTIVE");
                    setSummary(summaryData);
                    setZones(zonesData);
                    setAlerts(activeAlerts);
                    setLatestTelemetry(telData);
                    setLoading(false);
                }
            } catch (err: any) {
                if (isMounted) {
                    setError(err.message || "Failed to load live data");
                    setLoading(false);
                }
            }
        }

        loadMonitoringData();

        // 1.5s periodic polling for live sync
        const intervalId = setInterval(loadMonitoringData, 1500);

        return () => {
            isMounted = false;
            clearInterval(intervalId);
        };
    }, []);

    const hasCriticalAlert = alerts.some(
        (a) => a.severity === "CRITICAL" || a.severity === "HIGH"
    );

    // Group active alerts by zone to avoid visually repetitive cards while showing accurate counts and latest state
    const groupedAlerts = useMemo(() => {
        const groupMap = new Map<number, {
            zoneId: number;
            zoneName: string;
            count: number;
            latestAlert: AlertResponse;
            highestSeverity: string;
        }>();

        for (const alert of alerts) {
            const zid = alert.zone_id ?? 0;
            const existing = groupMap.get(zid);
            if (!existing) {
                const z = zones.find((item) => item.id === zid);
                let zName = z?.name;
                if (!zName) {
                    if (alert.title.includes("Zone 1")) {
                        zName = "Zone 1 — Main Deck Girder";
                    } else if (alert.title.includes("Zone 2")) {
                        zName = "Zone 2 — Substructure Pier B";
                    } else if (zid) {
                        zName = `Zone ${zid}`;
                    } else {
                        zName = alert.title;
                    }
                }
                groupMap.set(zid, {
                    zoneId: zid,
                    zoneName: zName,
                    count: 1,
                    latestAlert: alert,
                    highestSeverity: alert.severity,
                });
            } else {
                existing.count += 1;
                if (alert.id > existing.latestAlert.id) {
                    existing.latestAlert = alert;
                }
                if (alert.severity === "CRITICAL" || (alert.severity === "HIGH" && existing.highestSeverity !== "CRITICAL")) {
                    existing.highestSeverity = alert.severity;
                }
            }
        }

        return Array.from(groupMap.values());
    }, [alerts, zones]);

    return (
        <aside
            className="custom-scrollbar"
            style={{
                position: "absolute",
                top: "16px",
                left: "16px",
                zIndex: 10,
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                width: "360px",
                maxWidth: "calc(100vw - 32px)",
                maxHeight: "calc(100dvh - 32px)",
                overflowY: "auto",
                fontFamily: theme.typography.fontSans,
                color: theme.text.primary,
                pointerEvents: "auto",
                paddingRight: "4px",
            }}
            aria-label="City-wide structural health overview panel"
        >
            {/* Header Status Panel */}
            <div
                style={{
                    background: theme.surfaces.panel,
                    backdropFilter: "blur(12px)",
                    border: `1px solid ${hasCriticalAlert ? theme.surfaces.borderCritical : theme.surfaces.border}`,
                    borderRadius: "8px",
                    padding: "16px",
                    boxShadow: "0 15px 25px -5px rgba(0, 0, 0, 0.6)",
                }}
            >
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "8px",
                    }}
                >
                    <h1
                        style={{
                            fontSize: "15px",
                            fontWeight: 700,
                            margin: 0,
                            color: theme.text.accent,
                            letterSpacing: "0.04em",
                        }}
                    >
                        AEGIS3D OPERATIONS
                    </h1>
                    <span
                        style={{
                            fontSize: "10px",
                            fontFamily: theme.typography.fontMono,
                            padding: "2px 8px",
                            borderRadius: "12px",
                            background: loading
                                ? "#374151"
                                : error
                                ? theme.status.critical.bg
                                : theme.status.normal.bg,
                            color: loading
                                ? "#ffffff"
                                : error
                                ? theme.status.critical.text
                                : theme.status.normal.text,
                            border: `1px solid ${error ? theme.status.critical.border : theme.status.normal.border}`,
                            fontWeight: 700,
                        }}
                    >
                        {loading ? "CONNECTING..." : error ? "OFFLINE" : "LIVE BACKEND"}
                    </span>
                </div>

                <p style={{ fontSize: "11px", color: theme.text.secondary, margin: "0 0 12px 0" }}>
                    Civil Infrastructure Structural Integrity Monitoring
                </p>

                {/* Primary Action Button: Open 3D Digital Twin */}
                <button
                    onClick={() => openDigitalTwin()}
                    style={{
                        width: "100%",
                        padding: "10px 14px",
                        marginBottom: "12px",
                        border: "1px solid rgba(56, 189, 248, 0.5)",
                        borderRadius: "6px",
                        background: "rgba(56, 189, 248, 0.15)",
                        color: "#38bdf8",
                        fontSize: "12px",
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        transition: "all 0.15s ease",
                    }}
                >
                    <span>⚡ OPEN 3D DIGITAL TWIN & HUD</span>
                </button>

                {/* Latest Telemetry Banner */}
                {latestTelemetry ? (
                    <div
                        onClick={() => openDigitalTwin(latestTelemetry.zone_id)}
                        style={{
                            background: "rgba(15, 23, 42, 0.7)",
                            border: "1px solid rgba(148, 163, 184, 0.15)",
                            borderRadius: "6px",
                            padding: "8px 10px",
                            marginBottom: "12px",
                            fontSize: "11px",
                            cursor: "pointer",
                        }}
                        title="Click to view sensor in 3D"
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontWeight: 600, color: theme.text.primary }}>
                                {latestTelemetry.sensor_id}
                            </span>
                            <span
                                style={{
                                    fontFamily: theme.typography.fontMono,
                                    fontSize: "9px",
                                    padding: "1px 5px",
                                    borderRadius: "3px",
                                    background:
                                        latestTelemetry.events_detected > 0
                                            ? theme.status.warning.bg
                                            : theme.status.normal.bg,
                                    color:
                                        latestTelemetry.events_detected > 0
                                            ? theme.status.warning.text
                                            : theme.status.normal.text,
                                }}
                            >
                                {latestTelemetry.status}
                            </span>
                        </div>
                        <div
                            style={{
                                fontSize: "10px",
                                color: theme.text.muted,
                                fontFamily: theme.typography.fontMono,
                                marginTop: "3px",
                            }}
                        >
                            {latestTelemetry.samples_count} samples @ {latestTelemetry.sample_rate_hz}Hz · {latestTelemetry.zone_name}
                        </div>
                    </div>
                ) : (
                    <div
                        style={{
                            background: "rgba(15, 23, 42, 0.5)",
                            border: "1px dashed rgba(148, 163, 184, 0.2)",
                            borderRadius: "6px",
                            padding: "8px 10px",
                            marginBottom: "12px",
                            fontSize: "10px",
                            color: theme.text.muted,
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            fontFamily: theme.typography.fontMono,
                        }}
                    >
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#64748b" }} />
                        <span>AWAITING SENSOR TELEMETRY</span>
                    </div>
                )}

                {/* Summary Metrics */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px", textAlign: "center" }}>
                    <div style={{ background: theme.surfaces.panelSubtle, padding: "8px 4px", borderRadius: "6px" }}>
                        <div style={{ fontSize: "16px", fontWeight: 700, color: theme.text.accent, fontFamily: theme.typography.fontMono }}>
                            {loading ? "..." : summary?.total_zones ?? zones.length}
                        </div>
                        <div style={{ fontSize: "9px", color: theme.text.muted, textTransform: "uppercase" }}>Zones</div>
                    </div>

                    <div style={{ background: theme.surfaces.panelSubtle, padding: "8px 4px", borderRadius: "6px" }}>
                        <div
                            style={{
                                fontSize: "16px",
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                color: alerts.length > 0
                                    ? theme.status.critical.text
                                    : theme.status.normal.text,
                            }}
                        >
                            {loading ? "..." : alerts.length}
                        </div>
                        <div style={{ fontSize: "9px", color: theme.text.muted, textTransform: "uppercase" }}>Alerts</div>
                    </div>

                    <div style={{ background: theme.surfaces.panelSubtle, padding: "8px 4px", borderRadius: "6px" }}>
                        <div style={{ fontSize: "16px", fontWeight: 700, color: theme.status.warning.text, fontFamily: theme.typography.fontMono }}>
                            {loading ? "..." : summary?.recent_events_count ?? 0}
                        </div>
                        <div style={{ fontSize: "9px", color: theme.text.muted, textTransform: "uppercase" }}>Events</div>
                    </div>
                </div>
            </div>

            {/* Active Alerts Panel */}
            {alerts.length > 0 && (
                <div
                    style={{
                        background: theme.surfaces.panel,
                        backdropFilter: "blur(12px)",
                        border: `1px solid ${theme.status.critical.border}`,
                        borderRadius: "8px",
                        padding: "12px",
                    }}
                >
                    <div
                        style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            color: theme.status.critical.text,
                            textTransform: "uppercase",
                            marginBottom: "8px",
                            display: "flex",
                            justifyContent: "space-between",
                        }}
                    >
                        <span>⚠️ Active Alerts ({alerts.length})</span>
                    </div>
                    {/* Bounded Internal Scroll Container */}
                    <div
                        className="custom-scrollbar"
                        style={{
                            maxHeight: "180px",
                            overflowY: "auto",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                            paddingRight: "4px",
                        }}
                    >
                        {groupedAlerts.map((group) => (
                            <div
                                key={group.zoneId}
                                onClick={() => openDigitalTwin(group.zoneId)}
                                style={{
                                    fontSize: "11px",
                                    padding: "8px 10px",
                                    background: "rgba(239, 68, 68, 0.12)",
                                    border: "1px solid rgba(239, 68, 68, 0.35)",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                    wordBreak: "break-word",
                                    overflowWrap: "anywhere",
                                    transition: "all 0.15s ease",
                                }}
                                title="Click to view affected zone in 3D Digital Twin"
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "3px" }}>
                                    <div style={{ fontWeight: 700, color: "#fca5a5", fontSize: "12px" }}>
                                        {group.zoneName}
                                    </div>
                                    <span
                                        style={{
                                            fontSize: "9px",
                                            fontFamily: theme.typography.fontMono,
                                            fontWeight: 700,
                                            padding: "1px 5px",
                                            borderRadius: "3px",
                                            background: group.highestSeverity === "CRITICAL" || group.highestSeverity === "HIGH" ? "#dc2626" : "#d97706",
                                            color: "#ffffff",
                                        }}
                                    >
                                        {group.highestSeverity}
                                    </span>
                                </div>
                                <div style={{ fontSize: "10px", color: "#94a3b8", fontFamily: theme.typography.fontMono, marginBottom: "4px" }}>
                                    Active alerts: <strong style={{ color: "#fca5a5" }}>{group.count}</strong> · Latest: <strong style={{ color: "#e2e8f0" }}>#{group.latestAlert.id}</strong>
                                </div>
                                <div style={{ fontSize: "10px", color: "#cbd5e1", lineHeight: 1.35 }}>
                                    {group.latestAlert.message}
                                </div>
                                <div style={{ fontSize: "10px", color: "#38bdf8", fontWeight: 600, marginTop: "6px" }}>
                                    Inspect in 3D Twin →
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Zones List Panel */}
            {zones.length > 0 && (
                <div
                    style={{
                        background: theme.surfaces.panel,
                        backdropFilter: "blur(12px)",
                        border: `1px solid ${theme.surfaces.border}`,
                        borderRadius: "8px",
                        padding: "12px",
                    }}
                >
                    <div
                        style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            color: theme.text.secondary,
                            textTransform: "uppercase",
                            marginBottom: "8px",
                        }}
                    >
                        Monitored Zones ({zones.length})
                    </div>
                    {/* Bounded Internal Scroll Container */}
                    <div
                        className="custom-scrollbar"
                        style={{
                            maxHeight: "140px",
                            overflowY: "auto",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                            paddingRight: "4px",
                        }}
                    >
                        {zones.map((zone) => (
                            <div
                                key={zone.id}
                                onClick={() => openDigitalTwin(zone.id)}
                                style={{
                                    background: theme.surfaces.panelSubtle,
                                    padding: "6px 8px",
                                    borderRadius: "6px",
                                    fontSize: "11px",
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    cursor: "pointer",
                                }}
                                title="Click to view zone in 3D Digital Twin"
                            >
                                <div>
                                    <div style={{ fontWeight: 600, color: theme.text.primary }}>{zone.name}</div>
                                    <div style={{ fontSize: "9px", color: theme.text.muted }}>
                                        {zone.floor || "Structural Level"}
                                    </div>
                                </div>
                                <span
                                    style={{
                                        fontSize: "9px",
                                        fontFamily: theme.typography.fontMono,
                                        padding: "2px 6px",
                                        borderRadius: "4px",
                                        background: "rgba(56, 189, 248, 0.15)",
                                        color: "#38bdf8",
                                    }}
                                >
                                    ID {zone.id} →
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </aside>
    );
}
