"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
    AlertResponse,
    HealthSummaryResponse,
    ZoneResponse,
} from "@/types/api";

export default function MonitoringOverlay() {
    const [summary, setSummary] = useState<HealthSummaryResponse | null>(null);
    const [zones, setZones] = useState<ZoneResponse[]>([]);
    const [alerts, setAlerts] = useState<AlertResponse[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        async function loadMonitoringData() {
            try {
                const [summaryData, zonesData, alertsData] = await Promise.all([
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
                ]);

                if (isMounted) {
                    setSummary(summaryData);
                    setZones(zonesData);
                    setAlerts(alertsData);
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

        return () => {
            isMounted = false;
        };
    }, []);

    return (
        <div
            style={{
                position: "absolute",
                top: "16px",
                left: "16px",
                zIndex: 10,
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                maxWidth: "360px",
                fontFamily: "system-ui, -apple-system, sans-serif",
                color: "#f3f4f6",
                pointerEvents: "auto",
            }}
        >
            {/* Header Status Panel */}
            <div
                style={{
                    background: "rgba(17, 24, 39, 0.85)",
                    backdropFilter: "blur(8px)",
                    border: "1px solid rgba(75, 85, 99, 0.4)",
                    borderRadius: "8px",
                    padding: "16px",
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <h1 style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: "#60a5fa" }}>
                        Aegis3D Structural Health
                    </h1>
                    <span
                        style={{
                            fontSize: "11px",
                            padding: "2px 8px",
                            borderRadius: "12px",
                            background: loading ? "#374151" : error ? "#991b1b" : "#065f46",
                            color: "#ffffff",
                            fontWeight: 600,
                        }}
                    >
                        {loading ? "CONNECTING..." : error ? "OFFLINE" : "LIVE BACKEND"}
                    </span>
                </div>
                <p style={{ fontSize: "12px", color: "#9ca3af", margin: "0 0 12px 0" }}>
                    SDG 11 — Sustainable Cities & Infrastructure Monitoring
                </p>

                {/* Summary Metrics */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", textAlign: "center" }}>
                    <div style={{ background: "rgba(31, 41, 55, 0.6)", padding: "8px", borderRadius: "6px" }}>
                        <div style={{ fontSize: "18px", fontWeight: 700, color: "#38bdf8" }}>
                            {loading ? "..." : summary?.total_zones ?? zones.length}
                        </div>
                        <div style={{ fontSize: "10px", color: "#9ca3af" }}>Monitored Zones</div>
                    </div>

                    <div style={{ background: "rgba(31, 41, 55, 0.6)", padding: "8px", borderRadius: "6px" }}>
                        <div style={{ fontSize: "18px", fontWeight: 700, color: (summary?.active_alerts_count ?? alerts.length) > 0 ? "#f87171" : "#34d399" }}>
                            {loading ? "..." : summary?.active_alerts_count ?? alerts.length}
                        </div>
                        <div style={{ fontSize: "10px", color: "#9ca3af" }}>Active Alerts</div>
                    </div>

                    <div style={{ background: "rgba(31, 41, 55, 0.6)", padding: "8px", borderRadius: "6px" }}>
                        <div style={{ fontSize: "18px", fontWeight: 700, color: "#fbbf24" }}>
                            {loading ? "..." : summary?.recent_events_count ?? 0}
                        </div>
                        <div style={{ fontSize: "10px", color: "#9ca3af" }}>Recent Events</div>
                    </div>
                </div>
            </div>

            {/* Active Alerts Panel */}
            {alerts.length > 0 && (
                <div
                    style={{
                        background: "rgba(17, 24, 39, 0.85)",
                        backdropFilter: "blur(8px)",
                        border: "1px solid rgba(239, 68, 68, 0.4)",
                        borderRadius: "8px",
                        padding: "14px",
                    }}
                >
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#f87171", textTransform: "uppercase", marginBottom: "6px" }}>
                        ⚠️ Active Alert ({alerts.length})
                    </div>
                    {alerts.map((alert) => (
                        <div key={alert.id} style={{ fontSize: "12px", margin: "4px 0" }}>
                            <div style={{ fontWeight: 600, color: "#fef08a" }}>{alert.title}</div>
                            <div style={{ fontSize: "11px", color: "#d1d5db" }}>{alert.message}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Zones List Panel */}
            {zones.length > 0 && (
                <div
                    style={{
                        background: "rgba(17, 24, 39, 0.85)",
                        backdropFilter: "blur(8px)",
                        border: "1px solid rgba(75, 85, 99, 0.4)",
                        borderRadius: "8px",
                        padding: "14px",
                    }}
                >
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#93c5fd", textTransform: "uppercase", marginBottom: "8px" }}>
                        📍 Monitored Structure Zones ({zones.length})
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {zones.map((zone) => (
                            <div
                                key={zone.id}
                                style={{
                                    background: "rgba(31, 41, 55, 0.5)",
                                    padding: "8px 10px",
                                    borderRadius: "6px",
                                    fontSize: "12px",
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                }}
                            >
                                <div>
                                    <div style={{ fontWeight: 600, color: "#ffffff" }}>{zone.name}</div>
                                    <div style={{ fontSize: "10px", color: "#9ca3af" }}>{zone.floor || "General"}</div>
                                </div>
                                <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "#1e3a8a", color: "#bfdbfe" }}>
                                    ID: {zone.id}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
