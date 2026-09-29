"use client";

import { useMemo } from "react";
import { theme } from "@/lib/theme";

interface SignalWaveformProps {
    samples: number[];
    sampleRateHz?: number;
    detectionThreshold?: number | null;
    isAnomalous?: boolean;
    hasEvent?: boolean;
    sensorId?: string;
    status?: string;
    height?: number;
}

export default function SignalWaveform({
    samples = [],
    sampleRateHz = 1000,
    detectionThreshold = null,
    isAnomalous = false,
    hasEvent = false,
    sensorId,
    status,
    height = 120,
}: SignalWaveformProps) {
    const width = 360;
    const padding = { top: 18, bottom: 22, left: 38, right: 14 };
    const innerWidth = width - padding.left - padding.right;
    const innerHeight = height - padding.top - padding.bottom;
    const centerY = padding.top + innerHeight / 2;

    const waveformData = useMemo(() => {
        if (!samples || samples.length === 0) {
            return null;
        }

        let minVal = Infinity;
        let maxVal = -Infinity;
        let peakIdx = 0;
        let peakAbs = 0;

        for (let i = 0; i < samples.length; i++) {
            const val = samples[i];
            if (val < minVal) minVal = val;
            if (val > maxVal) maxVal = val;
            const abs = Math.abs(val);
            if (abs > peakAbs) {
                peakAbs = abs;
                peakIdx = i;
            }
        }

        // Determine symmetric amplitude range around 0
        let limit = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.1);
        if (detectionThreshold && detectionThreshold > 0) {
            limit = Math.max(limit, detectionThreshold * 1.15);
        }
        // Add 10% headroom
        limit *= 1.1;

        const scaleY = (val: number) => {
            // Clamped to inner bounds
            const normalized = val / limit;
            return centerY - normalized * (innerHeight / 2);
        };

        const scaleX = (idx: number) => {
            if (samples.length <= 1) return padding.left;
            return padding.left + (idx / (samples.length - 1)) * innerWidth;
        };

        const points = samples.map((s, idx) => `${scaleX(idx).toFixed(1)},${scaleY(s).toFixed(1)}`).join(" ");

        const durationMs = sampleRateHz > 0 ? (samples.length / sampleRateHz) * 1000 : 0;
        const peakX = scaleX(peakIdx);
        const peakY = scaleY(samples[peakIdx]);

        const threshYPos = detectionThreshold ? scaleY(detectionThreshold) : null;
        const threshYNeg = detectionThreshold ? scaleY(-detectionThreshold) : null;

        return {
            points,
            minVal,
            maxVal,
            peakAbs,
            peakX,
            peakY,
            limit,
            durationMs,
            threshYPos,
            threshYNeg,
        };
    }, [samples, sampleRateHz, detectionThreshold, innerWidth, innerHeight, centerY, padding.left]);

    // Semantic trace color
    const traceColor = isAnomalous
        ? theme.status.critical.text
        : hasEvent
        ? theme.status.warning.text
        : theme.status.monitor.text;

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
                gap: 6,
                fontFamily: theme.typography.fontSans,
            }}
            aria-label="Real-time discrete sensor telemetry waveform visualization"
        >
            {/* Header info */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: 11,
                    color: theme.text.secondary,
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontWeight: 600, color: theme.text.primary, letterSpacing: "0.04em" }}>
                        DISCRETE SIGNAL TRACE
                    </span>
                    {sensorId && (
                        <span
                            style={{
                                fontFamily: theme.typography.fontMono,
                                fontSize: 10,
                                padding: "1px 5px",
                                borderRadius: 4,
                                background: "rgba(56, 189, 248, 0.12)",
                                color: "#38bdf8",
                            }}
                        >
                            {sensorId}
                        </span>
                    )}
                </div>

                <div
                    style={{
                        fontFamily: theme.typography.fontMono,
                        fontSize: 10,
                        color: isAnomalous ? theme.status.critical.text : theme.text.muted,
                        fontWeight: 600,
                    }}
                >
                    {status || (samples.length > 0 ? `${samples.length} SAMPLES` : "AWAITING")}
                </div>
            </div>

            {/* SVG Waveform Canvas */}
            <div style={{ position: "relative", width: "100%", height, overflow: "hidden" }}>
                <svg
                    viewBox={`0 0 ${width} ${height}`}
                    preserveAspectRatio="none"
                    style={{ width: "100%", height: "100%", display: "block" }}
                >
                    {/* Background gridlines */}
                    <line
                        x1={padding.left}
                        y1={centerY}
                        x2={width - padding.right}
                        y2={centerY}
                        stroke="rgba(148, 163, 184, 0.2)"
                        strokeWidth="1"
                        strokeDasharray="3 3"
                    />

                    {/* Scale axis labels */}
                    {waveformData && (
                        <>
                            <text
                                x={padding.left - 4}
                                y={padding.top + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="9"
                                fontFamily={theme.typography.fontMono}
                            >
                                +{waveformData.limit.toFixed(1)}
                            </text>
                            <text
                                x={padding.left - 4}
                                y={centerY + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="9"
                                fontFamily={theme.typography.fontMono}
                            >
                                0.0
                            </text>
                            <text
                                x={padding.left - 4}
                                y={height - padding.bottom + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="9"
                                fontFamily={theme.typography.fontMono}
                            >
                                -{waveformData.limit.toFixed(1)}
                            </text>
                        </>
                    )}

                    {/* Detection threshold lines */}
                    {waveformData && waveformData.threshYPos !== null && waveformData.threshYNeg !== null && (
                        <>
                            <line
                                x1={padding.left}
                                y1={waveformData.threshYPos}
                                x2={width - padding.right}
                                y2={waveformData.threshYPos}
                                stroke="rgba(245, 158, 11, 0.45)"
                                strokeWidth="1"
                                strokeDasharray="4 2"
                            />
                            <line
                                x1={padding.left}
                                y1={waveformData.threshYNeg}
                                x2={width - padding.right}
                                y2={waveformData.threshYNeg}
                                stroke="rgba(245, 158, 11, 0.45)"
                                strokeWidth="1"
                                strokeDasharray="4 2"
                            />
                            <text
                                x={width - padding.right - 2}
                                y={waveformData.threshYPos - 3}
                                textAnchor="end"
                                fill="#f59e0b"
                                fontSize="8"
                                fontFamily={theme.typography.fontMono}
                            >
                                Thresh ({detectionThreshold?.toFixed(2)})
                            </text>
                        </>
                    )}

                    {/* Signal Trace */}
                    {waveformData ? (
                        <>
                            <polyline
                                fill="none"
                                stroke={traceColor}
                                strokeWidth="1.6"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                points={waveformData.points}
                            />
                            {/* Peak indicator dot */}
                            <circle
                                cx={waveformData.peakX}
                                cy={waveformData.peakY}
                                r="3.5"
                                fill={traceColor}
                                stroke="#020617"
                                strokeWidth="1.5"
                            />
                        </>
                    ) : (
                        // Empty state: flatline at zero
                        <>
                            <line
                                x1={padding.left}
                                y1={centerY}
                                x2={width - padding.right}
                                y2={centerY}
                                stroke="rgba(56, 189, 248, 0.3)"
                                strokeWidth="1.5"
                            />
                            <text
                                x={width / 2}
                                y={centerY - 10}
                                textAnchor="middle"
                                fill={theme.text.muted}
                                fontSize="10"
                                fontFamily={theme.typography.fontSans}
                                letterSpacing="0.04em"
                            >
                                NO RECENT TELEMETRY · SENSOR IDLE
                            </text>
                        </>
                    )}
                </svg>
            </div>

            {/* Waveform Footer Metrics */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                    color: theme.text.muted,
                    borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                    paddingTop: 4,
                }}
            >
                <div>
                    0 ms · {samples.length} pts @ {sampleRateHz.toLocaleString()} Hz
                </div>
                {waveformData && (
                    <div style={{ color: isAnomalous ? theme.status.critical.text : theme.text.secondary }}>
                        Peak |A|:{" "}
                        <strong style={{ color: isAnomalous ? theme.status.critical.text : theme.text.primary }}>
                            {waveformData.peakAbs.toFixed(2)} mm/s²
                        </strong>{" "}
                        ({waveformData.durationMs.toFixed(0)} ms)
                    </div>
                )}
            </div>
        </div>
    );
}
