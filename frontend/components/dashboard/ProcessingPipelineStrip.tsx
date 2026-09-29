"use client";

import { TelemetryLatestResponse } from "@/types/api";
import { theme } from "@/lib/theme";

interface ProcessingPipelineStripProps {
    telemetry: TelemetryLatestResponse | null;
    onInspect?: () => void;
}

export default function ProcessingPipelineStrip({
    telemetry,
    onInspect,
}: ProcessingPipelineStripProps) {
    if (!telemetry) {
        return (
            <div
                style={{
                    background: "#080d1a",
                    border: `1px solid ${theme.surfaces.border}`,
                    borderRadius: 8,
                    padding: "12px 14px",
                    fontFamily: theme.typography.fontSans,
                    fontSize: 11,
                    color: theme.text.muted,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}
            >
                <div
                    style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: "#64748b",
                    }}
                />
                <div>PIPELINE IDLE · WAITING FOR SENSOR PACKET</div>
            </div>
        );
    }

    const hasEvents = telemetry.events_detected > 0;
    const hasAnomaly = telemetry.events.some((e) => e.is_anomalous);
    const firstEvent = telemetry.events[0];

    const maxZScore = Math.max(
        Math.abs(firstEvent?.magnitude_z_score || 0),
        Math.abs(firstEvent?.energy_z_score || 0)
    );

    const hasExtractedFeatures =
        telemetry.extracted_features !== null &&
        telemetry.extracted_features !== undefined;

    const isCorrelated =
        telemetry.cross_sensor_correlation_confirmed === true;

    const isPersistent =
        telemetry.temporal_persistence_confirmed === true;

    const hasAlert = telemetry.alert_generated;

    const stages = [
        {
            num: "01",
            name: "INGESTION",
            state: "ACCEPTED",
            statusColor: theme.status.normal,
            evidence: `${telemetry.samples_count} pts @ ${telemetry.sample_rate_hz}Hz (seq #${telemetry.sequence ?? 0})`,
        },
        {
            num: "02",
            name: "CONDITIONING",
            state: "COMPLETED",
            statusColor: theme.status.normal,
            evidence: "DC removal + moving-average preprocessing",
        },
        {
            num: "03",
            name: "EVENT DETECT",
            state: hasEvents
                ? `${telemetry.events_detected} DETECTED`
                : "BELOW THRESHOLD",
            statusColor: hasEvents
                ? theme.status.warning
                : theme.status.monitor,
            evidence:
                hasEvents && telemetry.extracted_features
                    ? `Peak: ${telemetry.extracted_features.peak_amplitude.toFixed(
                        2
                    )} mm/s² (${telemetry.extracted_features.duration_ms.toFixed(
                        0
                    )}ms)`
                    : `Activity < threshold (${telemetry.detection_threshold?.toFixed(2) ?? "1.00"
                    })`,
        },
        {
            num: "04",
            name: "FEATURE EXTRACTION",
            state: hasEvents
                ? hasExtractedFeatures
                    ? "EXTRACTED"
                    : "NO FEATURES"
                : "NOT TRIGGERED",
            statusColor: !hasEvents
                ? {
                    bg: "rgba(100, 116, 139, 0.15)",
                    text: "#94a3b8",
                    border: "rgba(100, 116, 139, 0.3)",
                }
                : hasExtractedFeatures
                    ? theme.status.normal
                    : theme.status.monitor,
            evidence:
                hasExtractedFeatures && telemetry.extracted_features
                    ? `Peak ${telemetry.extracted_features.peak_amplitude.toFixed(
                        2
                    )} · RMS ${telemetry.extracted_features.rms_amplitude.toFixed(
                        2
                    )} · Energy ${telemetry.extracted_features.energy.toFixed(
                        2
                    )}`
                    : "No event features extracted",
        },
        {
            num: "05",
            name: "BASELINE REFERENCE",
            state: "REFERENCED",
            statusColor: theme.status.normal,
            evidence:
                "Zone baseline reference used for anomaly evaluation",
        },
        {
            num: "06",
            name: "ANOMALY EVAL",
            state: !hasEvents
                ? "NOT TRIGGERED"
                : hasAnomaly
                    ? `ANOMALOUS (${maxZScore.toFixed(1)}σ)`
                    : "BASELINE NORMAL",
            statusColor: !hasEvents
                ? {
                    bg: "rgba(100, 116, 139, 0.15)",
                    text: "#94a3b8",
                    border: "rgba(100, 116, 139, 0.3)",
                }
                : hasAnomaly
                    ? theme.status.critical
                    : theme.status.normal,
            evidence: !hasEvents
                ? "Sub-threshold signal bypassed"
                : hasAnomaly
                    ? `Z-Score: +${maxZScore.toFixed(2)}σ · ${firstEvent?.anomaly_reasons?.[0] ||
                    "Statistical outlier"
                    }`
                    : "Signal within ±3.0σ baseline envelope",
        },
        {
            num: "07",
            name: "PERSISTENCE",
            state: !hasEvents
                ? "INACTIVE"
                : isPersistent
                    ? "CONFIRMED"
                    : "NOT CONFIRMED",
            statusColor: !hasEvents
                ? {
                    bg: "rgba(100, 116, 139, 0.15)",
                    text: "#94a3b8",
                    border: "rgba(100, 116, 139, 0.3)",
                }
                : isPersistent
                    ? theme.status.warning
                    : theme.status.monitor,
            evidence: isPersistent
                ? "Multiple anomalous bursts within persistence window"
                : hasEvents
                    ? "Persistence threshold not confirmed"
                    : "No events detected in current packet",
        },
        {
            num: "08",
            name: "CORRELATION",
            state: !hasEvents
                ? "INACTIVE"
                : isCorrelated
                    ? "CONFIRMED (2-PZT)"
                    : "NOT CORRELATED",
            statusColor: !hasEvents
                ? {
                    bg: "rgba(100, 116, 139, 0.15)",
                    text: "#94a3b8",
                    border: "rgba(100, 116, 139, 0.3)",
                }
                : isCorrelated
                    ? theme.status.critical
                    : theme.status.monitor,
            evidence: isCorrelated
                ? "Multi-node spatial coincidence verified"
                : hasEvents
                    ? "No cross-sensor correlation confirmed"
                    : "No events detected in current packet",
        },
        {
            num: "09",
            name: "HEALTH & ALERT",
            state:
                telemetry.health_score !== null &&
                    telemetry.health_score !== undefined
                    ? hasAlert
                        ? `ALERT #${telemetry.alert_id}`
                        : `${telemetry.health_score.toFixed(1)} / 100`
                    : "UNMODIFIED",
            statusColor: hasAlert
                ? theme.status.critical
                : telemetry.health_status === "HIGH_PRIORITY_INSPECTION" ||
                    telemetry.health_status === "INSPECTION_ADVISED"
                    ? theme.status.critical
                    : telemetry.health_status === "MONITOR"
                        ? theme.status.warning
                        : theme.status.normal,
            evidence: hasAlert
                ? `${telemetry.alert_severity || "HIGH"}: ${telemetry.alert_title || "Structural degradation"
                }`
                : telemetry.health_status
                    ? `SHI: ${telemetry.health_score?.toFixed(
                        1
                    )} / 100 · Status: ${telemetry.health_status
                    } (${telemetry.health_trend || "STABLE"})`
                    : "Health index unchanged (no event)",
        },
    ];

    return (
        <div
            style={{
                width: "100%",
                background: "#080d1a",
                border: `1px solid ${theme.surfaces.border}`,
                borderRadius: 8,
                padding: "10px 12px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                fontFamily: theme.typography.fontSans,
            }}
            aria-label="Backend signal processing pipeline state progression"
        >
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: 11,
                    fontWeight: 600,
                    color: theme.text.secondary,
                    letterSpacing: "0.04em",
                }}
            >
                <span>PROCESSING PIPELINE PROGRESSION</span>

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                    }}
                >
                    {onInspect && (
                        <button
                            onClick={onInspect}
                            style={{
                                border: "1px solid rgba(56, 189, 248, 0.4)",
                                background: "rgba(56, 189, 248, 0.15)",
                                color: "#38bdf8",
                                fontSize: 9.5,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                padding: "2px 8px",
                                borderRadius: 4,
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                                letterSpacing: "0.04em",
                                transition: "all 0.15s ease",
                            }}
                            title="Open Telemetry Processing Inspector"
                        >
                            🔍 INSPECT
                        </button>
                    )}

                    <span
                        style={{
                            fontFamily: theme.typography.fontMono,
                            fontSize: 10,
                            color: theme.status.monitor.text,
                        }}
                    >
                        9-STAGE VERIFICATION
                    </span>
                </div>
            </div>

            {/* Stages Stack */}
            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 5,
                }}
            >
                {stages.map((stage) => (
                    <div
                        key={stage.num}
                        style={{
                            display: "grid",
                            gridTemplateColumns:
                                "auto minmax(0, 1fr) auto",
                            alignItems: "center",
                            gap: 8,
                            background: "rgba(15, 23, 42, 0.6)",
                            border: "1px solid rgba(148, 163, 184, 0.12)",
                            borderRadius: 6,
                            padding: "5px 8px",
                            minWidth: 0,
                            boxSizing: "border-box",
                        }}
                    >
                        {/* 1. Left: Step number & name */}
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                flexShrink: 0,
                                whiteSpace: "nowrap",
                            }}
                        >
                            <span
                                style={{
                                    fontFamily: theme.typography.fontMono,
                                    fontSize: 10,
                                    color: theme.text.muted,
                                    width: 14,
                                }}
                            >
                                {stage.num}
                            </span>

                            <span
                                style={{
                                    fontWeight: 600,
                                    color: theme.text.primary,
                                    fontSize: 10.5,
                                    letterSpacing: "0.02em",
                                }}
                            >
                                {stage.name}
                            </span>
                        </div>

                        {/* 2. Middle: Description / Evidence */}
                        <div
                            style={{
                                minWidth: 0,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                                fontSize: 10,
                                fontFamily: theme.typography.fontMono,
                                color: theme.text.muted,
                                textAlign: "left",
                            }}
                            title={stage.evidence}
                        >
                            {stage.evidence}
                        </div>

                        {/* 3. Right: Status / State Badge */}
                        <div
                            style={{
                                flexShrink: 0,
                                whiteSpace: "nowrap",
                                fontSize: 9.5,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: stage.statusColor.bg,
                                color: stage.statusColor.text,
                                border: `1px solid ${stage.statusColor.border}`,
                                textAlign: "center",
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center",
                            }}
                        >
                            {stage.state}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}