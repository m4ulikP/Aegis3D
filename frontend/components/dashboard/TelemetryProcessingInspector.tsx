"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { api } from "@/lib/api";
import { theme } from "@/lib/theme";
import {
    AlertSeverity,
    AlertTrace,
    AnomalyEvaluationTrace,
    BaselineTrace,
    ConditioningTrace,
    CorrelationTrace,
    DetectedWindowTrace,
    EventDetectionTrace,
    FeatureExtractionTrace,
    HealthStatus,
    HealthTrace,
    PersistenceTrace,
    ProcessingTraceResponse,
    RawTelemetryTrace,
    TelemetryLatestResponse,
} from "@/types/api";

// ==========================================
// SVG ENGINEERING ICONS (NO EMOJIS)
// ==========================================
function IconChevronLeft() {
    return (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" />
        </svg>
    );
}

function IconChevronRight() {
    return (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 18l6-6-6-6" />
        </svg>
    );
}

function IconClose() {
    return (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
    );
}

function IconCheck() {
    return (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12" />
        </svg>
    );
}

function IconAlert() {
    return (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
    );
}

function IconSearch() {
    return (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
    );
}

function IconMaximize() {
    return (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="15 3 21 3 21 9" />
            <polyline points="9 21 3 21 3 15" />
            <line x1="21" y1="3" x2="14" y2="10" />
            <line x1="3" y1="21" x2="10" y2="14" />
        </svg>
    );
}

function IconTransducer() {
    return (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M5 12a7 7 0 0 1 14 0" />
            <path d="M2 12a10 10 0 0 1 20 0" />
        </svg>
    );
}

// Stage definition metadata for the 9-stage pagination viewer (Single Stage Metadata Source)
interface StageMeta {
    id: number;
    numberStr: string;
    title: string;
    subtitle: string;
    shortLabel: string;
}

const STAGES: StageMeta[] = [
    { id: 1, numberStr: "01 / 09", title: "INGESTION", subtitle: "Raw Sensor Acquisition", shortLabel: "Ingestion" },
    { id: 2, numberStr: "02 / 09", title: "CONDITIONING", subtitle: "DC Removal & Filtering", shortLabel: "Conditioning" },
    { id: 3, numberStr: "03 / 09", title: "EVENT DETECTION", subtitle: "Energy Threshold & Windowing", shortLabel: "Detection" },
    { id: 4, numberStr: "04 / 09", title: "FEATURE EXTRACTION", subtitle: "Peak, RMS & Frequency Features", shortLabel: "Features" },
    { id: 5, numberStr: "05 / 09", title: "BASELINE REFERENCE", subtitle: "Zone Statistical Norms", shortLabel: "Baseline" },
    { id: 6, numberStr: "06 / 09", title: "ANOMALY EVALUATION", subtitle: "Standardized Z-Score Deviation", shortLabel: "Anomaly" },
    { id: 7, numberStr: "07 / 09", title: "PERSISTENCE", subtitle: "Rolling Temporal Anomaly Window", shortLabel: "Persistence" },
    { id: 8, numberStr: "08 / 09", title: "CROSS-SENSOR CORRELATION", subtitle: "Multi-Transducer TDOA Association", shortLabel: "Correlation" },
    { id: 9, numberStr: "09 / 09", title: "HEALTH & ALERT", subtitle: "Structural Health Indicator & Alert Dispatch", shortLabel: "Health & Alert" },
];

// ==========================================
// DYNAMIC FADING STAGE PAGINATION COMPONENT
// ==========================================
interface DynamicStagePaginationProps {
    currentStage: number;
    onSelectStage: (stageId: number) => void;
    onPrevStage: () => void;
    onNextStage: () => void;
}

function DynamicStagePagination({
    currentStage,
    onSelectStage,
    onPrevStage,
    onNextStage,
}: DynamicStagePaginationProps) {
    const [hoveredStageId, setHoveredStageId] = useState<number | null>(null);

    // Sliding window calculation:
    // Slot width = 20px (10px dot + 10px spacing/margins)
    // 9 stages = 180px track
    // Visible viewport width = 140px (7 dots visible)
    const slotPitch = 20;
    const visibleCount = 7;
    const maxOffset = (STAGES.length - visibleCount) * slotPitch;
    const targetOffset = Math.max(0, Math.min(maxOffset, (currentStage - 4) * slotPitch));

    return (
        <nav
            aria-label="Processing stages navigation"
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "8px 14px 10px 14px",
                background: "rgba(15, 23, 42, 0.75)",
                borderBottom: "1px solid rgba(148, 163, 184, 0.12)",
                gap: 5,
            }}
        >
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    width: "100%",
                    maxWidth: 360,
                    position: "relative",
                }}
            >
                {/* Previous stage arrow */}
                <button
                    onClick={onPrevStage}
                    disabled={currentStage <= 1}
                    aria-label="Previous processing stage"
                    style={{
                        background: currentStage <= 1 ? "rgba(30, 41, 59, 0.2)" : "rgba(56, 189, 248, 0.1)",
                        border: `1px solid ${currentStage <= 1 ? "rgba(148, 163, 184, 0.08)" : "rgba(56, 189, 248, 0.25)"}`,
                        color: currentStage <= 1 ? "rgba(148, 163, 184, 0.25)" : "#38bdf8",
                        cursor: currentStage <= 1 ? "not-allowed" : "pointer",
                        borderRadius: 5,
                        width: 28,
                        height: 28,
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.15s ease",
                        opacity: currentStage <= 1 ? 0.35 : 1,
                    }}
                >
                    <IconChevronLeft />
                </button>

                {/* Centered sliding window of stage indicator dots */}
                <div
                    style={{
                        width: visibleCount * slotPitch,
                        height: 32,
                        overflow: "hidden",
                        position: "relative",
                        display: "flex",
                        alignItems: "center",
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            transform: `translateX(-${targetOffset}px)`,
                            transition: "transform 260ms cubic-bezier(0.2, 0.8, 0.2, 1)",
                            willChange: "transform",
                        }}
                    >
                        {STAGES.map((stage) => {
                            const isActive = stage.id === currentStage;
                            const distance = Math.abs(stage.id - currentStage);
                            // Distance-based fading
                            const opacity = distance === 0 ? 1 : distance === 1 ? 0.75 : distance === 2 ? 0.5 : distance === 3 ? 0.28 : 0.14;
                            const isHovered = hoveredStageId === stage.id;

                            return (
                                <div
                                    key={stage.id}
                                    style={{
                                        width: slotPitch,
                                        height: 32,
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        position: "relative",
                                        flexShrink: 0,
                                    }}
                                    onMouseEnter={() => setHoveredStageId(stage.id)}
                                    onMouseLeave={() => setHoveredStageId(null)}
                                >
                                    {/* Hover Tooltip anchored right above this indicator */}
                                    {isHovered && (
                                        <div
                                            role="tooltip"
                                            style={{
                                                position: "absolute",
                                                bottom: "calc(100% + 4px)",
                                                left: "50%",
                                                transform: "translateX(-50%)",
                                                background: "rgba(15, 23, 42, 0.95)",
                                                border: "1px solid rgba(56, 189, 248, 0.4)",
                                                color: "#67e8f9",
                                                fontSize: 9,
                                                fontWeight: 700,
                                                fontFamily: theme.typography.fontMono,
                                                padding: "2px 6px",
                                                borderRadius: 4,
                                                whiteSpace: "nowrap",
                                                pointerEvents: "none",
                                                zIndex: 50,
                                                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.6)",
                                            }}
                                        >
                                            {stage.numberStr.slice(0, 2)}: {stage.title}
                                        </div>
                                    )}

                                    <button
                                        onClick={() => onSelectStage(stage.id)}
                                        aria-label={`Go to ${stage.title}`}
                                        aria-current={isActive ? "step" : undefined}
                                        style={{
                                            width: isActive ? 10 : 7,
                                            height: isActive ? 10 : 7,
                                            borderRadius: "50%",
                                            background: isActive ? "#38bdf8" : isHovered ? "#67e8f9" : "#94a3b8",
                                            border: isActive ? "1.5px solid #7dd3fc" : "none",
                                            opacity: isHovered ? 1 : opacity,
                                            padding: 0,
                                            cursor: "pointer",
                                            transition: "all 200ms cubic-bezier(0.2, 0.8, 0.2, 1)",
                                            boxShadow: isActive ? "0 1px 3px rgba(0, 0, 0, 0.5), 0 0 2px rgba(56, 189, 248, 0.3)" : "none",
                                        }}
                                        className="stage-dot-btn"
                                    />
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Next stage arrow */}
                <button
                    onClick={onNextStage}
                    disabled={currentStage >= STAGES.length}
                    aria-label="Next processing stage"
                    style={{
                        background: currentStage >= STAGES.length ? "rgba(30, 41, 59, 0.2)" : "rgba(56, 189, 248, 0.1)",
                        border: `1px solid ${currentStage >= STAGES.length ? "rgba(148, 163, 184, 0.08)" : "rgba(56, 189, 248, 0.25)"}`,
                        color: currentStage >= STAGES.length ? "rgba(148, 163, 184, 0.25)" : "#38bdf8",
                        cursor: currentStage >= STAGES.length ? "not-allowed" : "pointer",
                        borderRadius: 5,
                        width: 28,
                        height: 28,
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.15s ease",
                        opacity: currentStage >= STAGES.length ? 0.35 : 1,
                    }}
                >
                    <IconChevronRight />
                </button>
            </div>

            {/* Stage Counter and Title */}
            <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
                <span
                    style={{
                        fontSize: 10.5,
                        fontWeight: 700,
                        color: "#38bdf8",
                        fontFamily: theme.typography.fontMono,
                        letterSpacing: "0.08em",
                    }}
                >
                    {STAGES[currentStage - 1].numberStr}
                </span>
                <span
                    style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#f8fafc",
                        letterSpacing: "0.04em",
                    }}
                >
                    {STAGES[currentStage - 1].title}
                </span>
            </div>
        </nav>
    );
}

// ==========================================
// 1. REUSABLE WAVEFORM CANVAS COMPONENT
// ==========================================
interface WaveformCanvasProps {
    samples: number[];
    sampleRate: number;
    totalSamplesCount: number;
    peakAmplitude: number;
    detectionThreshold?: number | null;
    windows?: DetectedWindowTrace[];
    hoveredWindowIdx?: number | null;
    onHoverWindow?: (idx: number | null) => void;
    isZoomed?: boolean;
    onToggleZoom?: () => void;
    showThreshold?: boolean;
    showWindows?: boolean;
    allowZoom?: boolean;
    title: string;
    subBadge?: string;
    subBadgeColor?: string;
}

function WaveformCanvas({
    samples,
    sampleRate,
    totalSamplesCount,
    peakAmplitude,
    detectionThreshold,
    windows = [],
    hoveredWindowIdx,
    onHoverWindow,
    isZoomed = false,
    onToggleZoom,
    showThreshold = false,
    showWindows = false,
    allowZoom = false,
    title,
    subBadge,
    subBadgeColor = "#38bdf8",
}: WaveformCanvasProps) {
    const hasWindows = windows.length > 0;
    const actualSampleRate = sampleRate > 0 ? sampleRate : 1000;
    const actualTotalCount = totalSamplesCount > 0 ? totalSamplesCount : samples.length || 1;

    // Full Overview Waveform Data
    const fullWaveformData = useMemo(() => {
        if (!samples || samples.length === 0) return null;

        let minVal = Infinity;
        let maxVal = -Infinity;
        for (let i = 0; i < samples.length; i++) {
            const v = samples[i];
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
        }

        let absPeak = Math.max(Math.abs(minVal), Math.abs(maxVal), peakAmplitude || 0.1);
        if (showThreshold && detectionThreshold) {
            absPeak = Math.max(absPeak, detectionThreshold * 1.15);
        }
        const limit = absPeak * 1.1;

        const svgWidth = 380;
        const svgHeight = 135;
        const padding = { top: 18, bottom: 24, left: 45, right: 15 };
        const innerW = svgWidth - padding.left - padding.right;
        const innerH = svgHeight - padding.top - padding.bottom;
        const centerY = padding.top + innerH / 2;

        const scaleY = (val: number) => centerY - (val / limit) * (innerH / 2);
        const scaleX = (idx: number) => {
            if (samples.length <= 1) return padding.left;
            return padding.left + (idx / (samples.length - 1)) * innerW;
        };

        const points = samples.map((s, idx) => `${scaleX(idx).toFixed(1)},${scaleY(s).toFixed(1)}`).join(" ");
        const durationMs = (actualTotalCount / actualSampleRate) * 1000;

        const windowOverlayRegions = showWindows
            ? windows.map((win, idx) => {
                  const denom = Math.max(1, actualTotalCount - 1);
                  const startRatio = Math.max(0, Math.min(1, win.start_index / denom));
                  const endRatio = Math.max(0, Math.min(1, win.end_index / denom));
                  const startX = padding.left + startRatio * innerW;
                  const endX = padding.left + endRatio * innerW;
                  const rectWidth = Math.max(3, endX - startX);
                  return { idx, startX, rectWidth, win };
              })
            : [];

        const thresholdYPos = showThreshold && detectionThreshold ? scaleY(detectionThreshold) : null;
        const thresholdYNeg = showThreshold && detectionThreshold ? scaleY(-detectionThreshold) : null;

        return {
            points,
            limit,
            durationMs,
            svgWidth,
            svgHeight,
            padding,
            centerY,
            windowOverlayRegions,
            thresholdYPos,
            thresholdYNeg,
        };
    }, [
        samples,
        actualSampleRate,
        actualTotalCount,
        peakAmplitude,
        showThreshold,
        detectionThreshold,
        showWindows,
        windows,
    ]);

    // Zoomed Activity Detail Waveform Data
    const zoomData = useMemo(() => {
        if (!isZoomed || !samples || samples.length === 0 || !windows || windows.length === 0) {
            return null;
        }

        let earliestStart = Infinity;
        let latestEnd = -Infinity;
        for (const win of windows) {
            if (win.start_index < earliestStart) earliestStart = win.start_index;
            if (win.end_index > latestEnd) latestEnd = win.end_index;
        }
        if (earliestStart === Infinity || latestEnd === -Infinity) return null;

        const eventSpan = latestEnd - earliestStart;
        const pad = Math.max(30, Math.round((eventSpan > 0 ? eventSpan : 50) * 0.45));
        let focusStart = Math.max(0, earliestStart - pad);
        let focusEnd = Math.min(actualTotalCount - 1, latestEnd + pad);

        if (focusEnd - focusStart < 40) {
            const center = Math.round((focusStart + focusEnd) / 2);
            focusStart = Math.max(0, center - 20);
            focusEnd = Math.min(actualTotalCount - 1, center + 20);
        }

        const startRatio = focusStart / Math.max(1, actualTotalCount - 1);
        const endRatio = focusEnd / Math.max(1, actualTotalCount - 1);
        const boundedStartIdx = Math.floor(startRatio * (samples.length - 1));
        const boundedEndIdx = Math.ceil(endRatio * (samples.length - 1));

        const focusedSamples = samples.slice(
            Math.max(0, boundedStartIdx),
            Math.min(samples.length, boundedEndIdx + 1)
        );
        if (focusedSamples.length < 2) return null;

        let minVal = Infinity;
        let maxVal = -Infinity;
        for (const v of focusedSamples) {
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
        }

        let absPeak = Math.max(Math.abs(minVal), Math.abs(maxVal), peakAmplitude || 0.1);
        if (showThreshold && detectionThreshold) {
            absPeak = Math.max(absPeak, detectionThreshold * 1.15);
        }
        const limit = absPeak * 1.1;

        const svgWidth = 380;
        const svgHeight = 135;
        const svgPadding = { top: 18, bottom: 24, left: 45, right: 15 };
        const innerW = svgWidth - svgPadding.left - svgPadding.right;
        const innerH = svgHeight - svgPadding.top - svgPadding.bottom;
        const centerY = svgPadding.top + innerH / 2;

        const scaleY = (val: number) => centerY - (val / limit) * (innerH / 2);
        const scaleX = (idx: number) => {
            if (focusedSamples.length <= 1) return svgPadding.left;
            return svgPadding.left + (idx / (focusedSamples.length - 1)) * innerW;
        };

        const points = focusedSamples.map((s, idx) => `${scaleX(idx).toFixed(1)},${scaleY(s).toFixed(1)}`).join(" ");
        const startMs = (focusStart / actualSampleRate) * 1000;
        const endMs = (focusEnd / actualSampleRate) * 1000;
        const midMs = (startMs + endMs) / 2;

        const focusSpan = Math.max(1, focusEnd - focusStart);
        const focusedWindows = windows.map((win, idx) => {
            const winStartRatio = (win.start_index - focusStart) / focusSpan;
            const winEndRatio = (win.end_index - focusStart) / focusSpan;
            const winStartX = svgPadding.left + Math.max(0, winStartRatio) * innerW;
            const winEndX = svgPadding.left + Math.min(1, winEndRatio) * innerW;
            const rectWidth = Math.max(4, winEndX - winStartX);
            return {
                idx,
                winStartX,
                rectWidth,
                win,
                labelY: svgPadding.top - 4 - (idx % 2 === 1 ? 12 : 0),
            };
        });

        const thresholdYPos = showThreshold && detectionThreshold ? scaleY(detectionThreshold) : null;
        const thresholdYNeg = showThreshold && detectionThreshold ? scaleY(-detectionThreshold) : null;

        return {
            points,
            limit,
            startMs,
            midMs,
            endMs,
            svgWidth,
            svgHeight,
            svgPadding,
            centerY,
            focusedWindows,
            thresholdYPos,
            thresholdYNeg,
        };
    }, [
        isZoomed,
        samples,
        actualSampleRate,
        actualTotalCount,
        peakAmplitude,
        showThreshold,
        detectionThreshold,
        windows,
    ]);

    const activeData = isZoomed && zoomData ? zoomData : fullWaveformData;

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                fontFamily: theme.typography.fontSans,
                transition: "border-color 0.2s ease",
            }}
        >
            {/* Header with Title and Control Buttons */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                    style={{
                        fontSize: 11.5,
                        fontWeight: 700,
                        color: "#f8fafc",
                        letterSpacing: "0.02em",
                    }}
                >
                    {title}
                </span>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {isZoomed && zoomData ? (
                        <span
                            style={{
                                fontSize: 9,
                                fontFamily: theme.typography.fontMono,
                                color: "#fbbf24",
                                background: "rgba(245, 158, 11, 0.12)",
                                padding: "1px 6px",
                                borderRadius: 4,
                                border: "1px solid rgba(245, 158, 11, 0.25)",
                            }}
                        >
                            {zoomData.startMs.toFixed(0)} ms → {zoomData.endMs.toFixed(0)} ms
                        </span>
                    ) : subBadge ? (
                        <span
                            style={{
                                fontSize: 9,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                color: subBadgeColor,
                                background: `${subBadgeColor}15`,
                                padding: "1px 5px",
                                borderRadius: 4,
                                border: `1px solid ${subBadgeColor}35`,
                            }}
                        >
                            {subBadge}
                        </span>
                    ) : (
                        <span
                            style={{
                                fontSize: 9,
                                fontFamily: theme.typography.fontMono,
                                color: theme.text.muted,
                            }}
                        >
                            {samples.length} pts
                        </span>
                    )}

                    {allowZoom && hasWindows && onToggleZoom && (
                        <button
                            onClick={onToggleZoom}
                            style={{
                                background: isZoomed ? "rgba(245, 158, 11, 0.15)" : "rgba(56, 189, 248, 0.12)",
                                border: `1px solid ${isZoomed ? "rgba(245, 158, 11, 0.35)" : "rgba(56, 189, 248, 0.25)"}`,
                                color: isZoomed ? "#fbbf24" : "#38bdf8",
                                fontSize: 9.5,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                padding: "2px 7px",
                                borderRadius: 4,
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                                transition: "all 0.15s ease",
                            }}
                            title={isZoomed ? "Return to full overview" : "Focus detected activity"}
                            aria-label={isZoomed ? "Return to full overview" : "Focus detected activity"}
                        >
                            {isZoomed ? (
                                <>
                                    <IconMaximize /> FULL VIEW
                                </>
                            ) : (
                                <>
                                    <IconSearch /> FOCUS
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* SVG Canvas Container */}
            {activeData ? (
                <div style={{ position: "relative", width: "100%", height: 135, overflow: "hidden" }}>
                    {isZoomed && zoomData ? (
                        /* Focused Activity Detail Waveform */
                        <svg
                            viewBox={`0 0 ${zoomData.svgWidth} ${zoomData.svgHeight}`}
                            preserveAspectRatio="none"
                            style={{ width: "100%", height: "100%", display: "block" }}
                        >
                            <line
                                x1={zoomData.svgPadding.left}
                                y1={zoomData.centerY}
                                x2={zoomData.svgWidth - zoomData.svgPadding.right}
                                y2={zoomData.centerY}
                                stroke="rgba(148, 163, 184, 0.25)"
                                strokeWidth="1"
                                strokeDasharray="3 3"
                            />

                            {zoomData.thresholdYPos !== null && zoomData.thresholdYNeg !== null && (
                                <>
                                    <line
                                        x1={zoomData.svgPadding.left}
                                        y1={zoomData.thresholdYPos}
                                        x2={zoomData.svgWidth - zoomData.svgPadding.right}
                                        y2={zoomData.thresholdYPos}
                                        stroke="rgba(245, 158, 11, 0.5)"
                                        strokeWidth="1"
                                        strokeDasharray="4 2"
                                    />
                                    <line
                                        x1={zoomData.svgPadding.left}
                                        y1={zoomData.thresholdYNeg}
                                        x2={zoomData.svgWidth - zoomData.svgPadding.right}
                                        y2={zoomData.thresholdYNeg}
                                        stroke="rgba(245, 158, 11, 0.5)"
                                        strokeWidth="1"
                                        strokeDasharray="4 2"
                                    />
                                </>
                            )}

                            {zoomData.focusedWindows.map(({ idx, winStartX, rectWidth, labelY }) => {
                                const isHovered = hoveredWindowIdx === idx;
                                return (
                                    <g
                                        key={idx}
                                        onMouseEnter={() => onHoverWindow?.(idx)}
                                        onMouseLeave={() => onHoverWindow?.(null)}
                                        style={{ cursor: "pointer" }}
                                    >
                                        <rect
                                            x={winStartX}
                                            y={zoomData.svgPadding.top}
                                            width={rectWidth}
                                            height={zoomData.svgHeight - zoomData.svgPadding.top - zoomData.svgPadding.bottom}
                                            fill={isHovered ? "rgba(245, 158, 11, 0.4)" : "rgba(245, 158, 11, 0.22)"}
                                            stroke={isHovered ? "#fef08a" : "#f59e0b"}
                                            strokeWidth={isHovered ? "1.8" : "1.2"}
                                            rx="2"
                                        />
                                        <text
                                            x={winStartX + rectWidth / 2}
                                            y={labelY}
                                            textAnchor="middle"
                                            fill={isHovered ? "#fef08a" : "#fbbf24"}
                                            fontSize="8.5"
                                            fontWeight="700"
                                            fontFamily={theme.typography.fontMono}
                                        >
                                            E{idx + 1}
                                        </text>
                                    </g>
                                );
                            })}

                            <text
                                x={zoomData.svgPadding.left - 4}
                                y={zoomData.svgPadding.top + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                +{zoomData.limit.toFixed(2)}
                            </text>
                            <text
                                x={zoomData.svgPadding.left - 4}
                                y={zoomData.centerY + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                0.0
                            </text>
                            <text
                                x={zoomData.svgPadding.left - 4}
                                y={zoomData.svgHeight - zoomData.svgPadding.bottom + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                -{zoomData.limit.toFixed(2)}
                            </text>

                            <polyline
                                fill="none"
                                stroke="#38bdf8"
                                strokeWidth="1.6"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                points={zoomData.points}
                            />

                            <text
                                x={zoomData.svgPadding.left}
                                y={zoomData.svgHeight - 6}
                                textAnchor="start"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                {zoomData.startMs.toFixed(0)} ms
                            </text>
                            <text
                                x={zoomData.svgPadding.left + (zoomData.svgWidth - zoomData.svgPadding.left - zoomData.svgPadding.right) / 2}
                                y={zoomData.svgHeight - 6}
                                textAnchor="middle"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                {zoomData.midMs.toFixed(0)} ms
                            </text>
                            <text
                                x={zoomData.svgWidth - zoomData.svgPadding.right}
                                y={zoomData.svgHeight - 6}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                {zoomData.endMs.toFixed(0)} ms
                            </text>
                        </svg>
                    ) : (
                        /* Full Overview Waveform */
                        <svg
                            viewBox={`0 0 ${fullWaveformData!.svgWidth} ${fullWaveformData!.svgHeight}`}
                            preserveAspectRatio="none"
                            style={{ width: "100%", height: "100%", display: "block" }}
                        >
                            <line
                                x1={fullWaveformData!.padding.left}
                                y1={fullWaveformData!.centerY}
                                x2={fullWaveformData!.svgWidth - fullWaveformData!.padding.right}
                                y2={fullWaveformData!.centerY}
                                stroke="rgba(148, 163, 184, 0.25)"
                                strokeWidth="1"
                                strokeDasharray="3 3"
                            />

                            {fullWaveformData!.thresholdYPos !== null && fullWaveformData!.thresholdYNeg !== null && (
                                <>
                                    <line
                                        x1={fullWaveformData!.padding.left}
                                        y1={fullWaveformData!.thresholdYPos}
                                        x2={fullWaveformData!.svgWidth - fullWaveformData!.padding.right}
                                        y2={fullWaveformData!.thresholdYPos}
                                        stroke="rgba(245, 158, 11, 0.5)"
                                        strokeWidth="1"
                                        strokeDasharray="4 2"
                                    />
                                    <line
                                        x1={fullWaveformData!.padding.left}
                                        y1={fullWaveformData!.thresholdYNeg}
                                        x2={fullWaveformData!.svgWidth - fullWaveformData!.padding.right}
                                        y2={fullWaveformData!.thresholdYNeg}
                                        stroke="rgba(245, 158, 11, 0.5)"
                                        strokeWidth="1"
                                        strokeDasharray="4 2"
                                    />
                                </>
                            )}

                            {fullWaveformData!.windowOverlayRegions.map(({ idx, startX, rectWidth }) => {
                                const isHovered = hoveredWindowIdx === idx;
                                return (
                                    <g
                                        key={idx}
                                        onMouseEnter={() => onHoverWindow?.(idx)}
                                        onMouseLeave={() => onHoverWindow?.(null)}
                                        style={{ cursor: "pointer" }}
                                    >
                                        <rect
                                            x={startX}
                                            y={fullWaveformData!.padding.top}
                                            width={rectWidth}
                                            height={fullWaveformData!.svgHeight - fullWaveformData!.padding.top - fullWaveformData!.padding.bottom}
                                            fill={isHovered ? "rgba(245, 158, 11, 0.35)" : "rgba(245, 158, 11, 0.18)"}
                                            stroke={isHovered ? "#f59e0b" : "rgba(245, 158, 11, 0.5)"}
                                            strokeWidth={isHovered ? "1.5" : "1"}
                                            rx="2"
                                        />
                                        <text
                                            x={startX + rectWidth / 2}
                                            y={fullWaveformData!.padding.top - 4}
                                            textAnchor="middle"
                                            fill={isHovered ? "#fef08a" : "#f59e0b"}
                                            fontSize="8"
                                            fontWeight="700"
                                            fontFamily={theme.typography.fontMono}
                                        >
                                            E{idx + 1}
                                        </text>
                                    </g>
                                );
                            })}

                            <text
                                x={fullWaveformData!.padding.left - 4}
                                y={fullWaveformData!.padding.top + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                +{fullWaveformData!.limit.toFixed(2)}
                            </text>
                            <text
                                x={fullWaveformData!.padding.left - 4}
                                y={fullWaveformData!.centerY + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                0.0
                            </text>
                            <text
                                x={fullWaveformData!.padding.left - 4}
                                y={fullWaveformData!.svgHeight - fullWaveformData!.padding.bottom + 3}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                -{fullWaveformData!.limit.toFixed(2)}
                            </text>

                            <polyline
                                fill="none"
                                stroke="#38bdf8"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                points={fullWaveformData!.points}
                            />

                            <text
                                x={fullWaveformData!.padding.left}
                                y={fullWaveformData!.svgHeight - 6}
                                textAnchor="start"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                0 ms
                            </text>
                            <text
                                x={fullWaveformData!.svgWidth - fullWaveformData!.padding.right}
                                y={fullWaveformData!.svgHeight - 6}
                                textAnchor="end"
                                fill={theme.text.muted}
                                fontSize="8.5"
                                fontFamily={theme.typography.fontMono}
                            >
                                {fullWaveformData!.durationMs.toFixed(1)} ms
                            </text>
                        </svg>
                    )}
                </div>
            ) : (
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.4)",
                        border: "1px dashed rgba(148, 163, 184, 0.2)",
                        borderRadius: 6,
                        padding: "20px 10px",
                        textAlign: "center",
                        fontFamily: theme.typography.fontMono,
                        fontSize: 10,
                        color: theme.text.muted,
                    }}
                >
                    No sample data available for display.
                </div>
            )}
        </div>
    );
}

// ==========================================
// 2. PAGE 1 — INGESTION COMPONENTS
// ==========================================
function IngestionMetadataBox({ metadata }: { metadata: ProcessingTraceResponse["metadata"] }) {
    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "#4ade80", letterSpacing: "0.04em", display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <IconCheck /> INGESTED
                </span>
                <span style={{ fontSize: 9, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                    {metadata.timestamp ? new Date(metadata.timestamp).toLocaleTimeString() + " UTC" : ""}
                </span>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "100px 1fr",
                    gap: "6px 10px",
                    fontSize: 10.5,
                    fontFamily: theme.typography.fontMono,
                    background: "rgba(15, 23, 42, 0.5)",
                    border: "1px solid rgba(148, 163, 184, 0.08)",
                    borderRadius: 6,
                    padding: "10px",
                }}
            >
                <span style={{ color: theme.text.muted }}>Trace ID:</span>
                <strong style={{ color: "#38bdf8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {metadata.trace_id}
                </strong>

                <span style={{ color: theme.text.muted }}>Event ID:</span>
                <strong style={{ color: metadata.event_id ? "#fbbf24" : "#94a3b8" }}>
                    {metadata.event_id ?? "None (Raw Telemetry)"}
                </strong>

                <span style={{ color: theme.text.muted }}>Sensor ID:</span>
                <strong style={{ color: "#f8fafc" }}>{metadata.sensor_id}</strong>

                <span style={{ color: theme.text.muted }}>Zone:</span>
                <strong style={{ color: "#f8fafc" }}>
                    {metadata.zone_name} (ID {metadata.zone_id})
                </strong>

                <span style={{ color: theme.text.muted }}>Timestamp:</span>
                <strong style={{ color: "#f8fafc", fontSize: 9.5 }}>{metadata.timestamp}</strong>

                <span style={{ color: theme.text.muted }}>Sample rate:</span>
                <strong style={{ color: "#f8fafc" }}>{metadata.sample_rate_hz} Hz</strong>

                <span style={{ color: theme.text.muted }}>Samples:</span>
                <strong style={{ color: "#f8fafc" }}>{metadata.samples_count} points</strong>

                <span style={{ color: theme.text.muted }}>Session:</span>
                <strong style={{ color: metadata.session_id ? "#38bdf8" : "#94a3b8" }}>
                    {metadata.session_id ? `#${metadata.session_id}` : "—"}
                </strong>
            </div>
        </div>
    );
}

function RawTelemetryGrid({ ingestion }: { ingestion: RawTelemetryTrace }) {
    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div
                style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: "#f8fafc",
                    letterSpacing: "0.02em",
                    marginBottom: 10,
                }}
            >
                Raw telemetry parameters
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>SAMPLES</span>
                    <strong style={{ color: "#f8fafc" }}>{ingestion.samples_count.toLocaleString()}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>SAMPLE RATE</span>
                    <strong style={{ color: "#f8fafc" }}>{ingestion.sample_rate_hz} Hz</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>PEAK</span>
                    <strong style={{ color: "#38bdf8" }}>{ingestion.peak_amplitude.toFixed(3)}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>RMS</span>
                    <strong style={{ color: "#38bdf8" }}>{ingestion.rms_amplitude.toFixed(3)}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", gridColumn: "span 2", paddingTop: 2 }}>
                    <span style={{ color: theme.text.muted }}>DISPLAY BOUNDING</span>
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            padding: "1px 5px",
                            borderRadius: 4,
                            background: ingestion.is_bounded ? "rgba(56, 189, 248, 0.15)" : "rgba(34, 197, 94, 0.15)",
                            color: ingestion.is_bounded ? "#38bdf8" : "#4ade80",
                            border: `1px solid ${ingestion.is_bounded ? "rgba(56, 189, 248, 0.3)" : "rgba(34, 197, 94, 0.3)"}`,
                        }}
                    >
                        {ingestion.is_bounded ? "BOUNDED SAMPLES (≤500 PTS)" : "FULL SAMPLES"}
                    </span>
                </div>
            </div>
        </div>
    );
}

// ==========================================
// ==========================================
// 2.5 SIGNAL TRANSITION HOOK (PAGE 02 VISUAL MORPHING)
// ==========================================
function useSignalTransition({
    rawSamples,
    conditionedSamples,
    signalViewMode,
}: {
    rawSamples: number[];
    conditionedSamples: number[];
    signalViewMode: "raw" | "conditioned";
}) {
    const [tFactor, setTFactor] = useState<number>(signalViewMode === "conditioned" ? 1 : 0);
    const animRef = useRef<number | null>(null);

    useEffect(() => {
        const targetT = signalViewMode === "conditioned" ? 1 : 0;

        const prefersReducedMotion =
            typeof window !== "undefined" &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        if (prefersReducedMotion) {
            setTFactor(targetT);
            return;
        }

        // Cancel previous animation frame to cleanly handle rapid user clicks
        if (animRef.current !== null) {
            cancelAnimationFrame(animRef.current);
            animRef.current = null;
        }

        let startT = tFactor;
        const duration = 500; // ~500 ms target transition duration
        let startTimestamp: number | null = null;

        const animate = (timestamp: number) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const elapsed = timestamp - startTimestamp;
            const progress = Math.min(1, elapsed / duration);

            // Restrained engineering ease-in-out curve
            const eased =
                progress < 0.5
                    ? 2 * progress * progress
                    : 1 - Math.pow(-2 * progress + 2, 2) / 2;

            const currentT = startT + (targetT - startT) * eased;
            setTFactor(currentT);

            if (progress < 1) {
                animRef.current = requestAnimationFrame(animate);
            } else {
                setTFactor(targetT);
                animRef.current = null;
            }
        };

        animRef.current = requestAnimationFrame(animate);

        return () => {
            if (animRef.current !== null) {
                cancelAnimationFrame(animRef.current);
                animRef.current = null;
            }
        };
    }, [signalViewMode]);

    const displaySamples = useMemo(() => {
        const raw = rawSamples || [];
        const cond = conditionedSamples && conditionedSamples.length > 0 ? conditionedSamples : raw;

        if (tFactor <= 0.0001) return raw;
        if (tFactor >= 0.9999) return cond;

        const len = Math.min(raw.length, cond.length);
        const interpolated = new Array(len);
        for (let i = 0; i < len; i++) {
            interpolated[i] = raw[i] + tFactor * (cond[i] - raw[i]);
        }
        return interpolated;
    }, [rawSamples, conditionedSamples, tFactor]);

    const isTransitioning = tFactor > 0.0001 && tFactor < 0.9999;

    return {
        displaySamples,
        tFactor,
        isTransitioning,
    };
}

// ==========================================
// 3. PAGE 2 — CONDITIONING COMPONENTS
// ==========================================
function ConditioningParamsGrid({
    conditioning,
    signalViewMode,
    onSignalViewModeChange,
    isTransitioning = false,
}: {
    conditioning?: ConditioningTrace;
    signalViewMode: "raw" | "conditioned";
    onSignalViewModeChange: (mode: "raw" | "conditioned") => void;
    isTransitioning?: boolean;
}) {
    if (!conditioning) {
        return (
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 8,
                    padding: "12px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 11,
                    color: theme.text.muted,
                }}
            >
                <div style={{ fontWeight: 700, color: "#67e8f9", marginBottom: 4, textTransform: "uppercase" }}>
                    Signal Conditioning
                </div>
                <div>No conditioning trace available.</div>
            </div>
        );
    }

    const isApplied = conditioning.dc_removal_applied || conditioning.filter_applied;
    const filterTypeFormatted = conditioning.filter_type
        ? conditioning.filter_type.replace(/_/g, " ").toUpperCase()
        : "NONE";
    const dcOffsetFormatted =
        conditioning.dc_offset_removed !== undefined && conditioning.dc_offset_removed !== null
            ? `${conditioning.dc_offset_removed >= 0 ? "+" : ""}${conditioning.dc_offset_removed.toFixed(6)}`
            : "N/A";
    const windowSizeFormatted = conditioning.filter_window_size
        ? `${conditioning.filter_window_size} samples`
        : "N/A";

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontFamily: theme.typography.fontSans,
            }}
        >
            {/* Header with Title and Status Indicator */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                    style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#f8fafc",
                        letterSpacing: "0.02em",
                    }}
                >
                    Signal conditioning parameters
                </span>
                <span
                    style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fontFamily: theme.typography.fontMono,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: isApplied ? "rgba(34, 197, 94, 0.15)" : "rgba(100, 116, 139, 0.2)",
                        color: isApplied ? "#4ade80" : "#94a3b8",
                        border: `1px solid ${isApplied ? "rgba(34, 197, 94, 0.3)" : "rgba(100, 116, 139, 0.3)"}`,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                    }}
                >
                    {isApplied ? (
                        <>
                            <IconCheck /> APPLIED
                        </>
                    ) : (
                        "UNCONDITIONED"
                    )}
                </span>
            </div>

            {/* Parameter Grid */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>DC REMOVAL</span>
                    <strong style={{ color: conditioning.dc_removal_applied ? "#4ade80" : "#94a3b8" }}>
                        {conditioning.dc_removal_applied ? "ENABLED" : "DISABLED"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>DC OFFSET REMOVED</span>
                    <strong style={{ color: "#38bdf8" }}>{dcOffsetFormatted}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>FILTER TYPE</span>
                    <strong style={{ color: conditioning.filter_applied ? "#38bdf8" : "#f8fafc" }}>
                        {filterTypeFormatted}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>WINDOW SIZE</span>
                    <strong style={{ color: "#f8fafc" }}>{windowSizeFormatted}</strong>
                </div>
            </div>

            {/* Signal View Toggle Bar */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    paddingTop: 6,
                    borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 10, color: theme.text.muted, fontFamily: theme.typography.fontMono }}>
                        COMPARE WAVEFORM
                    </span>
                    {isTransitioning && (
                        <span
                            style={{
                                fontSize: 8.5,
                                fontFamily: theme.typography.fontMono,
                                color: "#fbbf24",
                                background: "rgba(245, 158, 11, 0.15)",
                                padding: "1px 5px",
                                borderRadius: 3,
                                border: "1px solid rgba(245, 158, 11, 0.3)",
                            }}
                        >
                            APPLYING CONDITIONED VIEW
                        </span>
                    )}
                </div>
                <div
                    style={{
                        display: "inline-flex",
                        background: "rgba(15, 23, 42, 0.8)",
                        border: "1px solid rgba(148, 163, 184, 0.2)",
                        borderRadius: 5,
                        padding: 2,
                        gap: 2,
                    }}
                >
                    <button
                        onClick={() => onSignalViewModeChange("raw")}
                        style={{
                            background: signalViewMode === "raw" ? "rgba(56, 189, 248, 0.25)" : "transparent",
                            border: `1px solid ${signalViewMode === "raw" ? "rgba(56, 189, 248, 0.4)" : "transparent"}`,
                            color: signalViewMode === "raw" ? "#38bdf8" : theme.text.muted,
                            fontSize: 9.5,
                            fontWeight: 700,
                            fontFamily: theme.typography.fontMono,
                            padding: "3px 8px",
                            borderRadius: 4,
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                        }}
                    >
                        RAW / UNCONDITIONED
                    </button>
                    <button
                        onClick={() => onSignalViewModeChange("conditioned")}
                        style={{
                            background: signalViewMode === "conditioned" ? "rgba(56, 189, 248, 0.25)" : "transparent",
                            border: `1px solid ${signalViewMode === "conditioned" ? "rgba(56, 189, 248, 0.4)" : "transparent"}`,
                            color: signalViewMode === "conditioned" ? "#38bdf8" : theme.text.muted,
                            fontSize: 9.5,
                            fontWeight: 700,
                            fontFamily: theme.typography.fontMono,
                            padding: "3px 8px",
                            borderRadius: 4,
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                        }}
                    >
                        CONDITIONED
                    </button>
                </div>
            </div>
        </div>
    );
}

// ==========================================
// 4. PAGE 3 — EVENT DETECTION COMPONENTS
// ==========================================
function EventDetectionParamsGrid({ eventDetection }: { eventDetection?: EventDetectionTrace }) {
    if (!eventDetection) return null;
    const hasDetectedEvents = eventDetection.events_detected_count > 0;

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                    Event detection parameters
                </span>
                <span
                    style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fontFamily: theme.typography.fontMono,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: hasDetectedEvents ? "rgba(245, 158, 11, 0.15)" : "rgba(100, 116, 139, 0.2)",
                        color: hasDetectedEvents ? "#fbbf24" : "#94a3b8",
                        border: `1px solid ${hasDetectedEvents ? "rgba(245, 158, 11, 0.3)" : "rgba(100, 116, 139, 0.3)"}`,
                    }}
                >
                    {hasDetectedEvents ? `${eventDetection.events_detected_count} DETECTED` : "BELOW THRESHOLD"}
                </span>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>THRESHOLD</span>
                    <strong style={{ color: "#fbbf24" }}>{eventDetection.detection_threshold.toFixed(2)}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>EVENTS COUNT</span>
                    <strong style={{ color: hasDetectedEvents ? "#fbbf24" : "#f8fafc" }}>
                        {eventDetection.events_detected_count}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>MIN DURATION</span>
                    <strong style={{ color: "#f8fafc" }}>{eventDetection.min_duration_samples} samples</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>MERGE GAP</span>
                    <strong style={{ color: "#f8fafc" }}>{eventDetection.merge_gap_samples} samples</strong>
                </div>
            </div>
        </div>
    );
}

function DetectedWindowsList({
    windows,
    hoveredWindowIdx,
    setHoveredWindowIdx,
}: {
    windows: DetectedWindowTrace[];
    hoveredWindowIdx?: number | null;
    setHoveredWindowIdx?: (idx: number | null) => void;
}) {
    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                    Detected activity windows
                </span>
                <span style={{ fontSize: 9, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                    {windows.length} activity region{windows.length === 1 ? "" : "s"}
                </span>
            </div>

            {windows.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {windows.map((win, idx) => {
                        const isHovered = hoveredWindowIdx === idx;
                        return (
                            <div
                                key={idx}
                                onMouseEnter={() => setHoveredWindowIdx?.(idx)}
                                onMouseLeave={() => setHoveredWindowIdx?.(null)}
                                style={{
                                    background: isHovered ? "rgba(245, 158, 11, 0.15)" : "rgba(15, 23, 42, 0.5)",
                                    border: `1px solid ${isHovered ? "rgba(245, 158, 11, 0.4)" : "rgba(148, 163, 184, 0.12)"}`,
                                    borderRadius: 6,
                                    padding: "8px 10px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 4,
                                    cursor: "pointer",
                                    transition: "all 0.15s ease",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                        <span
                                            style={{
                                                fontSize: 9,
                                                fontWeight: 700,
                                                fontFamily: theme.typography.fontMono,
                                                padding: "1px 5px",
                                                borderRadius: 4,
                                                background: "rgba(245, 158, 11, 0.2)",
                                                color: "#fbbf24",
                                                border: "1px solid rgba(245, 158, 11, 0.35)",
                                            }}
                                        >
                                            E{idx + 1}
                                        </span>
                                        <span style={{ fontSize: 10, fontFamily: theme.typography.fontMono, color: "#f8fafc" }}>
                                            Index #{win.start_index} → #{win.end_index}
                                        </span>
                                    </div>
                                    <span style={{ fontSize: 10, fontFamily: theme.typography.fontMono, color: "#38bdf8" }}>
                                        {win.duration_ms.toFixed(1)} ms ({win.sample_count} pts)
                                    </span>
                                </div>

                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                                    <span>
                                        Time: {win.start_time_ms.toFixed(0)} ms → {win.end_time_ms.toFixed(0)} ms
                                    </span>
                                    <span>
                                        Peak: {win.peak_amplitude.toFixed(3)} · RMS: {win.rms_amplitude.toFixed(3)}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.4)",
                        border: "1px dashed rgba(148, 163, 184, 0.2)",
                        borderRadius: 6,
                        padding: "12px",
                        textAlign: "center",
                        fontFamily: theme.typography.fontMono,
                        fontSize: 10,
                        color: theme.text.muted,
                    }}
                >
                    No activity windows detected (signal below threshold).
                </div>
            )}
        </div>
    );
}

// ==========================================
// 5. PAGE 4 — FEATURE EXTRACTION COMPONENT
// ==========================================
function FeatureExtractionSection({
    features,
    metadataEventId,
}: {
    features?: FeatureExtractionTrace | null;
    metadataEventId?: number | null;
}) {
    if (!features) {
        return (
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 8,
                    padding: "12px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 11,
                    color: theme.text.muted,
                }}
            >
                <div style={{ fontWeight: 700, color: "#67e8f9", marginBottom: 4, textTransform: "uppercase" }}>
                    Feature Extraction
                </div>
                <div>No feature extraction data available.</div>
            </div>
        );
    }

    const eventId = features.event_id ?? metadataEventId;
    const hasEvent = eventId !== undefined && eventId !== null;

    const primaryKeys = new Set([
        "event_id",
        "peak",
        "peak_amplitude",
        "rms",
        "rms_amplitude",
        "energy",
        "duration",
        "duration_ms",
        "frequency",
        "frequency_hz",
        "sample_count",
    ]);

    const additionalEntries = Object.entries(features.features_dict || {}).filter(
        ([key]) => !primaryKeys.has(key)
    );

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                    style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#f8fafc",
                        letterSpacing: "0.02em",
                    }}
                >
                    Extracted event features
                </span>
                <span
                    style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fontFamily: theme.typography.fontMono,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: hasEvent ? "rgba(245, 158, 11, 0.15)" : "rgba(100, 116, 139, 0.2)",
                        color: hasEvent ? "#fbbf24" : "#94a3b8",
                        border: `1px solid ${hasEvent ? "rgba(245, 158, 11, 0.3)" : "rgba(100, 116, 139, 0.3)"}`,
                    }}
                >
                    {hasEvent ? `EVENT #${eventId}` : "RAW TELEMETRY"}
                </span>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>PEAK</span>
                    <strong style={{ color: "#38bdf8" }}>
                        {features.peak_amplitude !== undefined && features.peak_amplitude !== null
                            ? features.peak_amplitude.toFixed(3)
                            : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>RMS</span>
                    <strong style={{ color: "#38bdf8" }}>
                        {features.rms_amplitude !== undefined && features.rms_amplitude !== null
                            ? features.rms_amplitude.toFixed(3)
                            : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>ENERGY</span>
                    <strong style={{ color: "#fbbf24" }}>
                        {features.energy !== undefined && features.energy !== null
                            ? features.energy.toFixed(3)
                            : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>DURATION</span>
                    <strong style={{ color: "#f8fafc" }}>
                        {features.duration_ms !== undefined && features.duration_ms !== null
                            ? `${features.duration_ms.toFixed(1)} ms`
                            : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>FREQUENCY</span>
                    <strong style={{ color: features.frequency_hz ? "#38bdf8" : theme.text.muted }}>
                        {features.frequency_hz !== undefined && features.frequency_hz !== null
                            ? `${features.frequency_hz.toFixed(1)} Hz`
                            : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>SAMPLES</span>
                    <strong style={{ color: "#f8fafc" }}>
                        {features.sample_count !== undefined && features.sample_count !== null
                            ? `${features.sample_count} pts`
                            : "—"}
                    </strong>
                </div>
            </div>

            {additionalEntries.length > 0 && (
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                        paddingTop: 4,
                        borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                    }}
                >
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            color: theme.text.muted,
                            letterSpacing: "0.04em",
                            textTransform: "uppercase",
                        }}
                    >
                        Additional Trace Attributes
                    </span>
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: "4px 12px",
                            fontSize: 9.5,
                            fontFamily: theme.typography.fontMono,
                        }}
                    >
                        {additionalEntries.map(([key, val]) => (
                            <div key={key} style={{ display: "flex", justifyContent: "space-between" }}>
                                <span style={{ color: theme.text.muted, textTransform: "uppercase" }}>
                                    {key.replace(/_/g, " ")}
                                </span>
                                <span style={{ color: "#cbd5e1" }}>
                                    {typeof val === "number" ? val.toFixed(2) : String(val)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ==========================================
// 6. PAGE 5 — BASELINE REFERENCE COMPONENTS
// ==========================================
function BaselineReferenceSection({
    baseline,
    zoneName,
}: {
    baseline?: BaselineTrace | null;
    zoneName?: string | null;
}) {
    if (!baseline) {
        return (
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 8,
                    padding: "12px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 11,
                    color: theme.text.muted,
                }}
            >
                <div style={{ fontWeight: 700, color: "#67e8f9", marginBottom: 4, textTransform: "uppercase" }}>
                    Baseline Reference
                </div>
                <div>No baseline reference data available.</div>
            </div>
        );
    }

    const isValid = baseline.baseline_available ?? (baseline as any).valid ?? false;
    const baselineIdDisplay =
        baseline.baseline_id !== undefined && baseline.baseline_id !== null
            ? `#${baseline.baseline_id}`
            : "—";

    const zoneDisplay = zoneName
        ? `${zoneName} (ID: ${baseline.zone_id})`
        : `Zone ${baseline.zone_id}`;

    const meanMagStr =
        baseline.mean_magnitude !== undefined && baseline.mean_magnitude !== null
            ? baseline.mean_magnitude.toFixed(3)
            : "—";
    const stdMagStr =
        baseline.std_magnitude !== undefined && baseline.std_magnitude !== null
            ? baseline.std_magnitude.toFixed(3)
            : "—";

    const meanEnergyStr =
        baseline.mean_energy !== undefined && baseline.mean_energy !== null
            ? baseline.mean_energy.toFixed(3)
            : "—";
    const stdEnergyStr =
        baseline.std_energy !== undefined && baseline.std_energy !== null
            ? baseline.std_energy.toFixed(3)
            : "—";

    const normalEventRateStr =
        baseline.normal_event_rate !== undefined && baseline.normal_event_rate !== null
            ? baseline.normal_event_rate.toFixed(2)
            : "—";

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <span
                        style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#f8fafc",
                            letterSpacing: "0.02em",
                            display: "block",
                        }}
                    >
                        Baseline reference
                    </span>
                    <span
                        style={{
                            fontSize: 9,
                            color: theme.text.muted,
                            letterSpacing: "0.02em",
                        }}
                    >
                        Zone statistical norms
                    </span>
                </div>
                <span
                    style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fontFamily: theme.typography.fontMono,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: isValid ? "rgba(34, 197, 94, 0.15)" : "rgba(245, 158, 11, 0.15)",
                        color: isValid ? "#4ade80" : "#fbbf24",
                        border: `1px solid ${isValid ? "rgba(34, 197, 94, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                    }}
                >
                    {isValid ? (
                        <>
                            <IconCheck /> VALID BASELINE
                        </>
                    ) : (
                        <>
                            <IconAlert /> BASELINE INVALID
                        </>
                    )}
                </span>
            </div>

            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                    background: "rgba(15, 23, 42, 0.4)",
                    border: "1px solid rgba(148, 163, 184, 0.08)",
                    borderRadius: 6,
                    padding: "6px 8px",
                }}
            >
                <div style={{ display: "flex", gap: 6 }}>
                    <span style={{ color: theme.text.muted }}>ZONE:</span>
                    <strong style={{ color: "#f8fafc" }}>{zoneDisplay}</strong>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                    <span style={{ color: theme.text.muted }}>BASELINE ID:</span>
                    <strong style={{ color: "#38bdf8" }}>{baselineIdDisplay}</strong>
                </div>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                }}
            >
                <div style={{ gridColumn: "span 2", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 2, paddingTop: 2 }}>
                    <span style={{ fontSize: 9, fontWeight: 700, color: "#38bdf8", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                        Magnitude Reference
                    </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>MEAN</span>
                    <strong style={{ color: "#38bdf8" }}>{meanMagStr}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>STD DEV</span>
                    <strong style={{ color: "#38bdf8" }}>{stdMagStr}</strong>
                </div>

                <div style={{ gridColumn: "span 2", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 2, paddingTop: 4 }}>
                    <span style={{ fontSize: 9, fontWeight: 700, color: "#fbbf24", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                        Energy Reference
                    </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>MEAN</span>
                    <strong style={{ color: "#fbbf24" }}>{meanEnergyStr}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>STD DEV</span>
                    <strong style={{ color: "#fbbf24" }}>{stdEnergyStr}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", gridColumn: "span 2", paddingTop: 4 }}>
                    <span style={{ color: theme.text.muted }}>NORMAL EVENT RATE</span>
                    <strong style={{ color: "#f8fafc" }}>{normalEventRateStr}</strong>
                </div>
            </div>
        </div>
    );
}

function CurrentVsBaselineCard({
    features,
    baseline,
}: {
    features?: FeatureExtractionTrace | null;
    baseline: BaselineTrace;
}) {
    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                fontFamily: theme.typography.fontSans,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                    Current event vs baseline juxtaposition
                </span>
                <span style={{ fontSize: 9, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                    REFERENCE CONTEXT
                </span>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                    background: "rgba(15, 23, 42, 0.4)",
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                    borderRadius: 6,
                    padding: "8px 10px",
                }}
            >
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <span style={{ color: theme.text.muted, fontSize: 9 }}>CURRENT EVENT PEAK</span>
                    <strong style={{ color: "#38bdf8", fontSize: 11 }}>
                        {features?.peak_amplitude !== undefined && features?.peak_amplitude !== null
                            ? features.peak_amplitude.toFixed(3)
                            : "—"}
                    </strong>
                    <span style={{ color: theme.text.muted, fontSize: 8.5 }}>
                        Baseline Mean: {baseline.mean_magnitude?.toFixed(3) ?? "—"} (σ={baseline.std_magnitude?.toFixed(3) ?? "—"})
                    </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <span style={{ color: theme.text.muted, fontSize: 9 }}>CURRENT EVENT ENERGY</span>
                    <strong style={{ color: "#fbbf24", fontSize: 11 }}>
                        {features?.energy !== undefined && features?.energy !== null
                            ? features.energy.toFixed(3)
                            : "—"}
                    </strong>
                    <span style={{ color: theme.text.muted, fontSize: 8.5 }}>
                        Baseline Mean: {baseline.mean_energy?.toFixed(3) ?? "—"} (σ={baseline.std_energy?.toFixed(3) ?? "—"})
                    </span>
                </div>
            </div>
        </div>
    );
}

// ==========================================
// 7. PAGE 6 — ANOMALY EVALUATION COMPONENT
// ==========================================
function AnomalyEvaluationSection({ anomaly }: { anomaly?: AnomalyEvaluationTrace | null }) {
    if (!anomaly) {
        return (
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 8,
                    padding: "12px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 11,
                    color: theme.text.muted,
                }}
            >
                <div style={{ fontWeight: 700, color: "#67e8f9", marginBottom: 4, textTransform: "uppercase" }}>
                    Anomaly Evaluation
                </div>
                <div>No anomaly evaluation data available.</div>
            </div>
        );
    }

    const isEvaluated = anomaly.evaluated ?? false;
    const isAnomalous = anomaly.is_anomalous ?? (anomaly as any).anomalous ?? false;
    const magZ = anomaly.magnitude_z_score ?? (anomaly as any).magnitude_z;
    const engZ = anomaly.energy_z_score ?? (anomaly as any).energy_z;
    const threshold = anomaly.z_threshold ?? (anomaly as any).threshold;
    const magAnom = anomaly.magnitude_anomalous;
    const engAnom = anomaly.energy_anomalous;
    const severity = anomaly.severity;
    const reasons = anomaly.reasons || [];

    const formatZScore = (val?: number | null) => {
        if (val === undefined || val === null || isNaN(val)) return "—";
        const prefix = val > 0 ? "+" : "";
        return `${prefix}${val.toFixed(2)} σ`;
    };

    const formatThreshold = (val?: number | null) => {
        if (val === undefined || val === null || isNaN(val)) return "—";
        return `${val.toFixed(2)} σ`;
    };

    const getSeverityColor = (sev?: string | null) => {
        if (!sev) return theme.text.muted;
        switch (sev.toUpperCase()) {
            case "CRITICAL":
                return "#f87171";
            case "HIGH":
                return "#f97316";
            case "MEDIUM":
                return "#fbbf24";
            case "LOW":
                return "#4ade80";
            default:
                return "#94a3b8";
        }
    };

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontFamily: theme.typography.fontSans,
            }}
        >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <span
                        style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#f8fafc",
                            letterSpacing: "0.02em",
                            display: "block",
                        }}
                    >
                        Anomaly evaluation
                    </span>
                    <span
                        style={{
                            fontSize: 9,
                            color: theme.text.muted,
                            letterSpacing: "0.02em",
                        }}
                    >
                        Statistical deviation analysis
                    </span>
                </div>
                <span
                    style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fontFamily: theme.typography.fontMono,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: isEvaluated
                            ? "rgba(34, 197, 94, 0.15)"
                            : "rgba(100, 116, 139, 0.2)",
                        color: isEvaluated ? "#4ade80" : "#94a3b8",
                        border: `1px solid ${
                            isEvaluated
                                ? "rgba(34, 197, 94, 0.3)"
                                : "rgba(100, 116, 139, 0.3)"
                        }`,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                    }}
                >
                    {isEvaluated ? (
                        <>
                            <IconCheck /> EVALUATED
                        </>
                    ) : (
                        "— NOT EVALUATED"
                    )}
                </span>
            </div>

            {/* 1. PRIMARY PROMINENT OUTCOME BANNER (First content element) */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: isEvaluated
                        ? isAnomalous
                            ? "rgba(245, 158, 11, 0.15)"
                            : "rgba(34, 197, 94, 0.15)"
                        : "rgba(15, 23, 42, 0.4)",
                    border: `1px solid ${
                        isEvaluated
                            ? isAnomalous
                                ? "rgba(245, 158, 11, 0.4)"
                                : "rgba(34, 197, 94, 0.4)"
                            : "rgba(148, 163, 184, 0.1)"
                    }`,
                    borderRadius: 6,
                    padding: "10px 12px",
                    fontFamily: theme.typography.fontMono,
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {isEvaluated && (
                        isAnomalous ? (
                            <span style={{ color: "#fbbf24", display: "inline-flex" }}>
                                <IconAlert />
                            </span>
                        ) : (
                            <span style={{ color: "#4ade80", display: "inline-flex" }}>
                                <IconCheck />
                            </span>
                        )
                    )}
                    <div>
                        <span style={{ fontSize: 8.5, color: theme.text.muted, display: "block", textTransform: "uppercase" }}>
                            Evaluation Outcome
                        </span>
                        <strong
                            style={{
                                fontSize: 13,
                                fontWeight: 800,
                                color: isEvaluated
                                    ? isAnomalous
                                        ? "#fbbf24"
                                        : "#4ade80"
                                    : theme.text.muted,
                                letterSpacing: "0.02em",
                            }}
                        >
                            {isEvaluated
                                ? isAnomalous
                                    ? "ANOMALY DETECTED"
                                    : "NO ANOMALY DETECTED"
                                : "NOT EVALUATED"}
                        </strong>
                    </div>
                </div>

                {severity && (
                    <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: 8.5, color: theme.text.muted, display: "block", textTransform: "uppercase" }}>
                            SEVERITY
                        </span>
                        <strong
                            style={{
                                fontSize: 10,
                                fontWeight: 800,
                                color: getSeverityColor(severity),
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: "rgba(15, 23, 42, 0.6)",
                                border: `1px solid ${getSeverityColor(severity)}40`,
                                display: "inline-block",
                            }}
                        >
                            {severity}
                        </strong>
                    </div>
                )}
            </div>

            {/* 2. Z-Score Deviation & Thresholds */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                    background: "rgba(15, 23, 42, 0.4)",
                    border: "1px solid rgba(148, 163, 184, 0.08)",
                    borderRadius: 6,
                    padding: "8px 10px",
                }}
            >
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <span style={{ color: theme.text.muted, fontSize: 9, textTransform: "uppercase" }}>
                        MAGNITUDE Z
                    </span>
                    <strong style={{ color: magAnom ? "#fbbf24" : "#38bdf8", fontSize: 12 }}>
                        {formatZScore(magZ)}
                    </strong>
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            color: magAnom === true ? "#fbbf24" : magAnom === false ? "#4ade80" : theme.text.muted,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 3,
                        }}
                    >
                        {magAnom === true ? (
                            <>
                                <IconAlert /> ANOMALOUS
                            </>
                        ) : magAnom === false ? (
                            <>
                                <IconCheck /> NORMAL
                            </>
                        ) : (
                            "—"
                        )}
                    </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <span style={{ color: theme.text.muted, fontSize: 9, textTransform: "uppercase" }}>
                        ENERGY Z
                    </span>
                    <strong style={{ color: engAnom ? "#fbbf24" : "#38bdf8", fontSize: 12 }}>
                        {formatZScore(engZ)}
                    </strong>
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            color: engAnom === true ? "#fbbf24" : engAnom === false ? "#4ade80" : theme.text.muted,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 3,
                        }}
                    >
                        {engAnom === true ? (
                            <>
                                <IconAlert /> ANOMALOUS
                            </>
                        ) : engAnom === false ? (
                            <>
                                <IconCheck /> NORMAL
                            </>
                        ) : (
                            "—"
                        )}
                    </span>
                </div>

                <div
                    style={{
                        gridColumn: "span 2",
                        display: "flex",
                        justifyContent: "space-between",
                        borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                        paddingTop: 6,
                        marginTop: 2,
                    }}
                >
                    <span style={{ color: theme.text.muted }}>DECISION THRESHOLD</span>
                    <strong style={{ color: "#f8fafc" }}>{formatThreshold(threshold)}</strong>
                </div>
            </div>

            {reasons.length > 0 && (
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                        paddingTop: 4,
                        borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                    }}
                >
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            color: theme.text.muted,
                            letterSpacing: "0.04em",
                            textTransform: "uppercase",
                        }}
                    >
                        Evidence / Reasons
                    </span>
                    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        {reasons.map((r, idx) => (
                            <div
                                key={idx}
                                style={{
                                    fontSize: 9.5,
                                    fontFamily: theme.typography.fontMono,
                                    color: "#cbd5e1",
                                    display: "flex",
                                    gap: 6,
                                    alignItems: "flex-start",
                                }}
                            >
                                <span style={{ color: "#fbbf24" }}>•</span>
                                <span>{r}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ==========================================
// 8. PAGE 7 — PERSISTENCE COMPONENT
// ==========================================
function PersistenceSection({ persistence }: { persistence?: PersistenceTrace | null }) {
    if (!persistence) {
        return (
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 8,
                    padding: "12px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 11,
                    color: theme.text.muted,
                }}
            >
                <div style={{ fontWeight: 700, color: "#67e8f9", marginBottom: 4, textTransform: "uppercase" }}>
                    Persistence
                </div>
                <div>No persistence trace available.</div>
            </div>
        );
    }

    const isEvaluated = persistence.evaluated ?? false;
    const isPersistent = persistence.is_persistent ?? (persistence as any).persistent;
    const totalEvents = persistence.total_events_in_window ?? (persistence as any).total_events;
    const anomalousEvents = persistence.anomalous_events_in_window ?? (persistence as any).anomalous_events;
    const anomalyRatio = persistence.anomaly_ratio;
    const maxConsecutive = persistence.max_consecutive_anomalies;
    const windowSeconds = persistence.window_duration_seconds ?? (persistence as any).window_seconds;
    const minEventCount = persistence.min_anomaly_count_required ?? (persistence as any).min_event_count;
    const minAnomalyRatio = persistence.min_anomaly_ratio_required ?? (persistence as any).min_anomaly_ratio;
    const reasons = persistence.reasons || [];

    const resultText =
        isPersistent === true
            ? "PERSISTENT"
            : isPersistent === false
            ? "NOT PERSISTENT"
            : "—";

    const resultColor =
        isPersistent === true
            ? "#fbbf24"
            : isPersistent === false
            ? "#4ade80"
            : theme.text.muted;

    const ratioDisplay =
        anomalyRatio !== undefined && anomalyRatio !== null && !isNaN(anomalyRatio)
            ? anomalyRatio.toFixed(2)
            : "—";

    const windowDisplay =
        windowSeconds !== undefined && windowSeconds !== null && !isNaN(windowSeconds)
            ? `${windowSeconds} s`
            : "—";

    const minRatioDisplay =
        minAnomalyRatio !== undefined && minAnomalyRatio !== null && !isNaN(minAnomalyRatio)
            ? minAnomalyRatio.toFixed(2)
            : "—";

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(148, 163, 184, 0.12)",
                borderRadius: 8,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontFamily: theme.typography.fontSans,
            }}
        >
            {/* Header with Title, Subtitle, and Evaluated Badge */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <span
                        style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#f8fafc",
                            letterSpacing: "0.02em",
                            display: "block",
                        }}
                    >
                        Persistence evaluation
                    </span>
                    <span
                        style={{
                            fontSize: 9,
                            color: theme.text.muted,
                            letterSpacing: "0.02em",
                        }}
                    >
                        Rolling temporal anomaly window
                    </span>
                </div>
                <span
                    style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fontFamily: theme.typography.fontMono,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: isEvaluated
                            ? "rgba(34, 197, 94, 0.15)"
                            : "rgba(100, 116, 139, 0.2)",
                        color: isEvaluated ? "#4ade80" : "#94a3b8",
                        border: `1px solid ${
                            isEvaluated
                                ? "rgba(34, 197, 94, 0.3)"
                                : "rgba(100, 116, 139, 0.3)"
                        }`,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                    }}
                >
                    {isEvaluated ? (
                        <>
                            <IconCheck /> EVALUATED
                        </>
                    ) : (
                        "— NOT EVALUATED"
                    )}
                </span>
            </div>

            {/* Primary Persistence Result & Observation Window */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: isEvaluated && isPersistent === true
                        ? "rgba(245, 158, 11, 0.12)"
                        : "rgba(15, 23, 42, 0.4)",
                    border: `1px solid ${
                        isEvaluated && isPersistent === true
                            ? "rgba(245, 158, 11, 0.35)"
                            : "rgba(148, 163, 184, 0.1)"
                    }`,
                    borderRadius: 6,
                    padding: "8px 10px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 10,
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ color: theme.text.muted }}>RESULT:</span>
                    <strong style={{ color: resultColor, fontSize: 11, display: "inline-flex", alignItems: "center", gap: 4 }}>
                        {isPersistent === true && <IconAlert />}
                        {isPersistent === false && <IconCheck />}
                        {resultText}
                    </strong>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ color: theme.text.muted }}>WINDOW:</span>
                    <strong style={{ color: "#f8fafc" }}>{windowDisplay}</strong>
                </div>
            </div>

            {/* Rolling Event Counts & Anomaly Statistics Grid */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px 12px",
                    fontSize: 10,
                    fontFamily: theme.typography.fontMono,
                    background: "rgba(15, 23, 42, 0.4)",
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                    borderRadius: 6,
                    padding: "8px 10px",
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>TOTAL EVENTS</span>
                    <strong style={{ color: "#f8fafc" }}>
                        {totalEvents !== undefined && totalEvents !== null ? totalEvents : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>ANOMALOUS EVENTS</span>
                    <strong style={{ color: anomalousEvents && anomalousEvents > 0 ? "#fbbf24" : "#f8fafc" }}>
                        {anomalousEvents !== undefined && anomalousEvents !== null ? anomalousEvents : "—"}
                    </strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>ANOMALY RATIO</span>
                    <strong style={{ color: "#38bdf8" }}>{ratioDisplay}</strong>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                    <span style={{ color: theme.text.muted }}>MAX CONSECUTIVE</span>
                    <strong style={{ color: "#f8fafc" }}>
                        {maxConsecutive !== undefined && maxConsecutive !== null ? maxConsecutive : "—"}
                    </strong>
                </div>
            </div>

            {/* Persistence Criteria Section */}
            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    background: "rgba(15, 23, 42, 0.4)",
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                    borderRadius: 6,
                    padding: "8px 10px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 10,
                }}
            >
                <span style={{ fontSize: 9, fontWeight: 700, color: "#67e8f9", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                    Persistence Criteria
                </span>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: theme.text.muted }}>MIN EVENTS</span>
                        <strong style={{ color: "#f8fafc" }}>
                            {minEventCount !== undefined && minEventCount !== null ? minEventCount : "—"}
                        </strong>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: theme.text.muted }}>MIN RATIO</span>
                        <strong style={{ color: "#f8fafc" }}>{minRatioDisplay}</strong>
                    </div>
                </div>
            </div>

            {/* Evidence / Reasons List */}
            {reasons.length > 0 && (
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                        paddingTop: 4,
                        borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                    }}
                >
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            color: theme.text.muted,
                            letterSpacing: "0.04em",
                            textTransform: "uppercase",
                        }}
                    >
                        Evidence / Reasons
                    </span>
                    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        {reasons.map((r, idx) => (
                            <div
                                key={idx}
                                style={{
                                    fontSize: 9.5,
                                    fontFamily: theme.typography.fontMono,
                                    color: "#cbd5e1",
                                    display: "flex",
                                    gap: 6,
                                    alignItems: "flex-start",
                                }}
                            >
                                <span style={{ color: "#fbbf24" }}>•</span>
                                <span>{r}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ==========================================
// 9. PAGE 8 — CORRELATION COMPONENT
// ==========================================
function CorrelationSection({ correlation }: { correlation?: CorrelationTrace | null }) {
    if (!correlation) {
        return (
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                    borderRadius: 8,
                    padding: "14px",
                    fontFamily: theme.typography.fontMono,
                    fontSize: 11,
                    color: theme.text.muted,
                }}
            >
                <div style={{ fontWeight: 700, color: "#67e8f9", marginBottom: 4, textTransform: "uppercase" }}>
                    Cross-Sensor Correlation
                </div>
                <div>No cross-sensor correlation trace available.</div>
            </div>
        );
    }

    const evaluated = correlation.evaluated ?? false;
    const isCorrelated = correlation.is_cross_sensor_correlated ?? false;
    const groupID = correlation.correlated_group_id || null;
    const sensors = correlation.participating_sensors || [];
    const eventIds = correlation.event_ids || [];
    const tempSpread = correlation.temporal_spread_ms;
    const toleranceSec = correlation.tolerance_seconds;
    const sourceHint = correlation.relative_source_hint || null;
    const reasons = correlation.reasons || [];

    const statusBadgeColor = !evaluated
        ? "#94a3b8"
        : isCorrelated
        ? "#f59e0b"
        : "#38bdf8";

    const statusBadgeBg = !evaluated
        ? "rgba(100, 116, 139, 0.2)"
        : isCorrelated
        ? "rgba(245, 158, 11, 0.15)"
        : "rgba(56, 189, 248, 0.15)";

    const statusBadgeBorder = !evaluated
        ? "rgba(100, 116, 139, 0.3)"
        : isCorrelated
        ? "rgba(245, 158, 11, 0.35)"
        : "rgba(56, 189, 248, 0.35)";

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Header & Primary Status Card */}
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: "1px solid rgba(148, 163, 184, 0.12)",
                    borderRadius: 8,
                    padding: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                    fontFamily: theme.typography.fontSans,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <span
                            style={{
                                fontSize: 12,
                                fontWeight: 700,
                                color: "#f8fafc",
                                letterSpacing: "0.02em",
                                display: "block",
                            }}
                        >
                            Cross-sensor correlation
                        </span>
                        <span
                            style={{
                                fontSize: 9,
                                color: theme.text.muted,
                                letterSpacing: "0.02em",
                            }}
                        >
                            Multi-transducer TDOA association
                        </span>
                    </div>

                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            fontFamily: theme.typography.fontMono,
                            padding: "1px 6px",
                            borderRadius: 4,
                            background: evaluated ? "rgba(34, 197, 94, 0.15)" : "rgba(100, 116, 139, 0.2)",
                            color: evaluated ? "#4ade80" : "#94a3b8",
                            border: `1px solid ${evaluated ? "rgba(34, 197, 94, 0.3)" : "rgba(100, 116, 139, 0.3)"}`,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                        }}
                    >
                        {evaluated ? (
                            <>
                                <IconCheck /> EVALUATED
                            </>
                        ) : (
                            "— NOT EVALUATED"
                        )}
                    </span>
                </div>

                {/* Main Outcome Banner */}
                <div
                    style={{
                        background: statusBadgeBg,
                        border: `1px solid ${statusBadgeBorder}`,
                        borderRadius: 6,
                        padding: "8px 12px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                    }}
                >
                    <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontSize: 9, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase" }}>
                            ASSOCIATION OUTCOME
                        </span>
                        <strong
                            style={{
                                fontSize: 11.5,
                                fontWeight: 800,
                                color: statusBadgeColor,
                                fontFamily: theme.typography.fontMono,
                                letterSpacing: "0.03em",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                            }}
                        >
                            {!evaluated
                                ? "CORRELATION NOT EVALUATED"
                                : isCorrelated
                                ? (
                                    <>
                                        <IconCheck /> CROSS-SENSOR CORRELATED
                                    </>
                                )
                                : "NO CROSS-SENSOR CORRELATION"}
                        </strong>
                    </div>

                    {groupID && (
                        <div style={{ textAlign: "right" }}>
                            <span style={{ fontSize: 8.5, color: theme.text.muted, fontFamily: theme.typography.fontMono, display: "block" }}>
                                GROUP ID
                            </span>
                            <span
                                style={{
                                    fontSize: 9.5,
                                    fontWeight: 700,
                                    color: "#f8fafc",
                                    fontFamily: theme.typography.fontMono,
                                    background: "rgba(15, 23, 42, 0.6)",
                                    padding: "2px 6px",
                                    borderRadius: 4,
                                    border: "1px solid rgba(148, 163, 184, 0.2)",
                                }}
                            >
                                {groupID}
                            </span>
                        </div>
                    )}
                </div>

                {/* Compact Grid of Temporal Parameters */}
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: "8px 12px",
                        fontSize: 10,
                        fontFamily: theme.typography.fontMono,
                        background: "rgba(15, 23, 42, 0.4)",
                        border: "1px solid rgba(148, 163, 184, 0.08)",
                        borderRadius: 6,
                        padding: "10px",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                        <span style={{ color: theme.text.muted }}>CORRELATION GROUP</span>
                        <strong style={{ color: groupID ? "#f8fafc" : theme.text.muted }}>
                            {groupID || "—"}
                        </strong>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4 }}>
                        <span style={{ color: theme.text.muted }}>CORRELATION TOLERANCE</span>
                        <strong style={{ color: "#f8fafc" }}>
                            {toleranceSec !== undefined && toleranceSec !== null
                                ? `${(toleranceSec * 1000).toFixed(1)} ms (${toleranceSec.toFixed(3)}s)`
                                : "—"}
                        </strong>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", paddingBottom: 4, gridColumn: "span 2" }}>
                        <span style={{ color: theme.text.muted }}>TEMPORAL SPREAD</span>
                        <strong style={{ color: tempSpread !== null && tempSpread !== undefined ? "#38bdf8" : theme.text.muted }}>
                            {tempSpread !== null && tempSpread !== undefined
                                ? `${tempSpread.toFixed(1)} ms`
                                : "—"}
                        </strong>
                    </div>
                </div>

                {/* Participating Sensors & Associated Event IDs */}
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                        background: "rgba(15, 23, 42, 0.4)",
                        border: "1px solid rgba(148, 163, 184, 0.08)",
                        borderRadius: 6,
                        padding: "10px",
                    }}
                >
                    <div>
                        <span style={{ fontSize: 9.5, fontWeight: 700, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                            PARTICIPATING SENSORS
                        </span>
                        {sensors.length > 0 ? (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                                {sensors.map((s, idx) => (
                                    <span
                                        key={idx}
                                        style={{
                                            fontSize: 9.5,
                                            fontWeight: 700,
                                            fontFamily: theme.typography.fontMono,
                                            padding: "2px 7px",
                                            borderRadius: 4,
                                            background: "rgba(56, 189, 248, 0.15)",
                                            color: "#38bdf8",
                                            border: "1px solid rgba(56, 189, 248, 0.3)",
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: 4,
                                        }}
                                    >
                                        <IconTransducer /> {s}
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <span style={{ fontSize: 10, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                                —
                            </span>
                        )}
                    </div>

                    <div style={{ borderTop: "1px solid rgba(148, 163, 184, 0.1)", paddingTop: 6 }}>
                        <span style={{ fontSize: 9.5, fontWeight: 700, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                            ASSOCIATED EVENT IDS
                        </span>
                        {eventIds.length > 0 ? (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                                {eventIds.map((eid, idx) => (
                                    <span
                                        key={idx}
                                        style={{
                                            fontSize: 9.5,
                                            fontWeight: 700,
                                            fontFamily: theme.typography.fontMono,
                                            padding: "2px 7px",
                                            borderRadius: 4,
                                            background: "rgba(245, 158, 11, 0.15)",
                                            color: "#fbbf24",
                                            border: "1px solid rgba(245, 158, 11, 0.3)",
                                        }}
                                    >
                                        #{eid}
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <span style={{ fontSize: 10, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                                —
                            </span>
                        )}
                    </div>
                </div>

                {/* Relative Source Indication - Primary Concise Interpretation */}
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.6)",
                        border: "1px solid rgba(56, 189, 248, 0.25)",
                        borderRadius: 6,
                        padding: "10px 12px",
                        display: "flex",
                        flexDirection: "column",
                        gap: 5,
                    }}
                >
                    <span style={{ fontSize: 10, fontWeight: 700, color: "#67e8f9", fontFamily: theme.typography.fontMono, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                        Relative Source Indication
                    </span>
                    <div
                        style={{
                            fontSize: 10.5,
                            fontWeight: 600,
                            fontFamily: theme.typography.fontMono,
                            color: sourceHint ? "#f8fafc" : theme.text.muted,
                            lineHeight: "1.4",
                            background: "rgba(15, 23, 42, 0.4)",
                            padding: "7px 10px",
                            borderRadius: 4,
                            border: "1px solid rgba(148, 163, 184, 0.1)",
                        }}
                    >
                        {sourceHint || "—"}
                    </div>
                </div>

                {/* Micro-Visual: Sensor Association Diagram (shown when 2+ sensors participate) */}
                {sensors.length >= 2 && (
                    <div
                        style={{
                            background: "rgba(15, 23, 42, 0.5)",
                            border: "1px solid rgba(56, 189, 248, 0.18)",
                            borderRadius: 6,
                            padding: "10px",
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                        }}
                    >
                        <span style={{ fontSize: 9, fontWeight: 700, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase" }}>
                            Transducer TDOA Association Link
                        </span>
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                background: "rgba(15, 23, 42, 0.6)",
                                padding: "8px 12px",
                                borderRadius: 5,
                                border: "1px solid rgba(148, 163, 184, 0.08)",
                            }}
                        >
                            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                <span style={{ color: "#38bdf8", display: "inline-flex" }}>
                                    <IconTransducer />
                                </span>
                                <span style={{ fontSize: 9.5, fontWeight: 700, fontFamily: theme.typography.fontMono, color: "#38bdf8" }}>
                                    {sensors[0]}
                                </span>
                            </div>

                            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", margin: "0 10px" }}>
                                <span style={{ fontSize: 8.5, fontFamily: theme.typography.fontMono, color: "#fbbf24", marginBottom: 2 }}>
                                    {tempSpread !== null && tempSpread !== undefined ? `Δt = ${tempSpread.toFixed(1)} ms` : "TDOA Linked"}
                                </span>
                                <div
                                    style={{
                                        width: "100%",
                                        height: 2,
                                        background: "linear-gradient(90deg, #38bdf8 0%, #fbbf24 50%, #38bdf8 100%)",
                                        borderRadius: 1,
                                    }}
                                />
                            </div>

                            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                <span style={{ fontSize: 9.5, fontWeight: 700, fontFamily: theme.typography.fontMono, color: "#38bdf8" }}>
                                    {sensors[1]}
                                </span>
                                <span style={{ color: "#38bdf8", display: "inline-flex" }}>
                                    <IconTransducer />
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Evidence / Reasons List — Visually Secondary Details */}
                {(() => {
                    const secondaryReasons = reasons.filter((r) => r && r.trim() !== sourceHint?.trim());
                    return (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingTop: 2, opacity: 0.85 }}>
                            <span style={{ fontSize: 9, fontWeight: 700, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase" }}>
                                Correlation Evidence & Reasons
                            </span>
                            {secondaryReasons.length > 0 ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                                    {secondaryReasons.map((r, idx) => (
                                        <div
                                            key={idx}
                                            style={{
                                                fontSize: 9,
                                                fontFamily: theme.typography.fontMono,
                                                color: "#94a3b8",
                                                background: "rgba(15, 23, 42, 0.3)",
                                                padding: "4px 8px",
                                                borderRadius: 4,
                                                border: "1px solid rgba(148, 163, 184, 0.06)",
                                            }}
                                        >
                                            • {r}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div style={{ fontSize: 9, fontFamily: theme.typography.fontMono, color: theme.text.muted, fontStyle: "italic" }}>
                                    No additional correlation remarks.
                                </div>
                            )}
                        </div>
                    );
                })()}
            </div>
        </div>
    );
}

// ==========================================
// ==========================================
// 10. PAGE 9 — HEALTH & ALERT COMPONENT
// ==========================================
function HealthAlertSection({
    health,
    alert,
}: {
    health?: HealthTrace | null;
    alert?: AlertTrace | null;
}) {
    const isHealthEvaluated = health?.evaluated ?? false;
    const healthScore = health?.health_score;
    const healthStatus = health?.health_status;
    const trend = health?.trend;
    const deductions = health?.deductions || null;
    const reason = health?.reason || null;
    const evidenceSummary = health?.evidence_summary || [];
    const disclaimer =
        health?.disclaimer ||
        "SHI is a prototype evidence-based monitoring indicator derived from observed signal/event behavior. It is not a certified structural safety score and does not independently establish structural damage or failure.";

    const alertGenerated = alert?.alert_generated ?? false;
    const alertId = alert?.alert_id;
    const alertSeverity = alert?.alert_severity;
    const alertStatus = alert?.alert_status;
    const alertTitle = alert?.alert_title;
    const alertMessage = alert?.alert_message;
    const alertTimestamp = alert?.timestamp;

    // Helper for Health Status Badge Color
    const getHealthStatusColor = (status?: HealthStatus | null) => {
        if (!status) return { text: "#94a3b8", bg: "rgba(100, 116, 139, 0.2)", border: "rgba(100, 116, 139, 0.3)" };
        switch (status) {
            case "HIGH_PRIORITY_INSPECTION":
                return { text: "#fca5a5", bg: "rgba(239, 68, 68, 0.2)", border: "rgba(239, 68, 68, 0.4)" };
            case "INSPECTION_ADVISED":
                return { text: "#f59e0b", bg: "rgba(245, 158, 11, 0.2)", border: "rgba(245, 158, 11, 0.4)" };
            case "MONITOR":
                return { text: "#fbbf24", bg: "rgba(251, 191, 36, 0.18)", border: "rgba(251, 191, 36, 0.35)" };
            case "NORMAL":
                return { text: "#4ade80", bg: "rgba(34, 197, 94, 0.18)", border: "rgba(34, 197, 94, 0.35)" };
            default:
                return { text: "#38bdf8", bg: "rgba(56, 189, 248, 0.18)", border: "rgba(56, 189, 248, 0.35)" };
        }
    };

    // Helper for Alert Severity Badge Color
    const getAlertSeverityColor = (severity?: AlertSeverity | null) => {
        if (!severity) return { text: "#94a3b8", bg: "rgba(100, 116, 139, 0.2)", border: "rgba(100, 116, 139, 0.3)" };
        switch (severity) {
            case "CRITICAL":
                return { text: "#fca5a5", bg: "rgba(239, 68, 68, 0.25)", border: "rgba(239, 68, 68, 0.45)" };
            case "HIGH":
                return { text: "#f59e0b", bg: "rgba(245, 158, 11, 0.22)", border: "rgba(245, 158, 11, 0.4)" };
            case "MEDIUM":
                return { text: "#fbbf24", bg: "rgba(251, 191, 36, 0.18)", border: "rgba(251, 191, 36, 0.35)" };
            case "LOW":
                return { text: "#38bdf8", bg: "rgba(56, 189, 248, 0.18)", border: "rgba(56, 189, 248, 0.35)" };
            default:
                return { text: "#cbd5e1", bg: "rgba(148, 163, 184, 0.15)", border: "rgba(148, 163, 184, 0.3)" };
        }
    };

    const statusColors = getHealthStatusColor(healthStatus);
    const alertColors = getAlertSeverityColor(alertSeverity);
    const deductionEntries = deductions ? Object.entries(deductions) : [];

    const totalDeductionVal = deductionEntries.reduce((acc, [, val]) => {
        const n = typeof val === "number" ? val : parseFloat(String(val));
        return acc + (isNaN(n) ? 0 : Math.abs(n));
    }, 0);

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* 1. PRIMARY STRUCTURAL HEALTH INDEX & COMPACT DEDUCTIONS CARD */}
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: `1px solid ${isHealthEvaluated ? statusColors.border : "rgba(148, 163, 184, 0.15)"}`,
                    borderRadius: 8,
                    padding: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                    fontFamily: theme.typography.fontSans,
                }}
            >
                {/* Header Row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span
                        style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: "#67e8f9",
                            letterSpacing: "0.05em",
                            textTransform: "uppercase",
                        }}
                    >
                        Structural Health Index
                    </span>
                    <span
                        style={{
                            fontSize: 9.5,
                            fontWeight: 700,
                            fontFamily: theme.typography.fontMono,
                            padding: "2px 7px",
                            borderRadius: 4,
                            background: isHealthEvaluated ? "rgba(34, 197, 94, 0.15)" : "rgba(100, 116, 139, 0.2)",
                            color: isHealthEvaluated ? "#4ade80" : "#94a3b8",
                            border: `1px solid ${isHealthEvaluated ? "rgba(34, 197, 94, 0.3)" : "rgba(100, 116, 139, 0.3)"}`,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                        }}
                    >
                        {isHealthEvaluated ? (
                            <>
                                <IconCheck /> EVALUATED
                            </>
                        ) : (
                            "— NOT EVALUATED"
                        )}
                    </span>
                </div>

                {/* Score & Health Status Hero Display */}
                <div
                    style={{
                        background: statusColors.bg,
                        border: `1px solid ${statusColors.border}`,
                        borderRadius: 6,
                        padding: "10px 12px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                    }}
                >
                    <div>
                        <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
                            <strong
                                style={{
                                    fontSize: 22,
                                    fontWeight: 800,
                                    color: healthScore !== null && healthScore !== undefined ? statusColors.text : theme.text.muted,
                                    fontFamily: theme.typography.fontMono,
                                    lineHeight: 1,
                                }}
                            >
                                {healthScore !== null && healthScore !== undefined ? healthScore.toFixed(1) : "—"}
                            </strong>
                            <span style={{ fontSize: 11, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                                / 100
                            </span>
                        </div>
                        <div
                            style={{
                                marginTop: 4,
                                fontSize: 10,
                                fontWeight: 700,
                                color: statusColors.text,
                                fontFamily: theme.typography.fontMono,
                                letterSpacing: "0.03em",
                                textTransform: "uppercase",
                            }}
                        >
                            {healthStatus ? healthStatus.replace(/_/g, " ") : "STATUS UNKNOWN"}
                        </div>
                    </div>

                    <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: 8.5, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase", display: "block" }}>
                            TREND
                        </span>
                        <span
                            style={{
                                fontSize: 10,
                                fontWeight: 700,
                                color: "#38bdf8",
                                fontFamily: theme.typography.fontMono,
                                letterSpacing: "0.03em",
                                textTransform: "uppercase",
                            }}
                        >
                            {trend ? trend.replace(/_/g, " ") : "INSUFFICIENT DATA"}
                        </span>
                    </div>
                </div>

                {/* Compact Deduction Breakdown Grid */}
                {deductionEntries.length > 0 && (
                    <div
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 5,
                            background: "rgba(15, 23, 42, 0.4)",
                            border: "1px solid rgba(148, 163, 184, 0.1)",
                            borderRadius: 6,
                            padding: "8px 10px",
                        }}
                    >
                        <span style={{ fontSize: 9.5, fontWeight: 700, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase" }}>
                            Score Deductions
                        </span>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 8px" }}>
                            {deductionEntries.map(([key, value]) => {
                                const rawNum = typeof value === "number" ? value : parseFloat(String(value));
                                const isZero = isNaN(rawNum) || rawNum === 0;
                                const formattedText = isZero ? "0 pts" : `−${Math.abs(rawNum).toFixed(0)} pts`;
                                return (
                                    <div
                                        key={key}
                                        style={{
                                            display: "flex",
                                            justifyContent: "space-between",
                                            alignItems: "center",
                                            fontSize: 9.5,
                                            fontFamily: theme.typography.fontMono,
                                            background: "rgba(15, 23, 42, 0.3)",
                                            padding: "3px 6px",
                                            borderRadius: 3,
                                            border: "1px solid rgba(148, 163, 184, 0.08)",
                                        }}
                                    >
                                        <span style={{ color: "#cbd5e1" }}>{key}</span>
                                        <span style={{ color: isZero ? "#94a3b8" : "#fca5a5", fontWeight: 700 }}>
                                            {formattedText}
                                        </span>
                                    </div>
                                );
                            })}
                            {totalDeductionVal > 0 && (
                                <div
                                    style={{
                                        gridColumn: "1 / -1",
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        fontSize: 9.5,
                                        fontWeight: 700,
                                        fontFamily: theme.typography.fontMono,
                                        background: "rgba(239, 68, 68, 0.12)",
                                        color: "#fca5a5",
                                        padding: "4px 7px",
                                        borderRadius: 3,
                                        border: "1px solid rgba(239, 68, 68, 0.25)",
                                        marginTop: 2,
                                    }}
                                >
                                    <span>total_deductions</span>
                                    <span>−{totalDeductionVal.toFixed(0)} pts</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* 2. SYSTEM ALERT DISPATCH — POSITIONED FOR FIRST-VIEWPORT ACCESSIBILITY */}
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    border: `1px solid ${alertGenerated ? alertColors.border : "rgba(148, 163, 184, 0.15)"}`,
                    borderRadius: 8,
                    padding: "10px 12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    fontFamily: theme.typography.fontSans,
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "#67e8f9", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                        System Alert Dispatch
                    </span>
                    <span
                        style={{
                            fontSize: 9,
                            fontWeight: 700,
                            fontFamily: theme.typography.fontMono,
                            padding: "1px 6px",
                            borderRadius: 4,
                            background: alertGenerated ? alertColors.bg : "rgba(34, 197, 94, 0.15)",
                            color: alertGenerated ? alertColors.text : "#4ade80",
                            border: `1px solid ${alertGenerated ? alertColors.border : "rgba(34, 197, 94, 0.3)"}`,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 3,
                        }}
                    >
                        {alertGenerated ? (
                            <>
                                <IconAlert /> ALERT ACTIVE
                            </>
                        ) : (
                            <>
                                <IconCheck /> NO ACTIVE ALERT
                            </>
                        )}
                    </span>
                </div>

                {alertGenerated ? (
                    <div
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                            background: alertColors.bg,
                            border: `1px solid ${alertColors.border}`,
                            borderRadius: 6,
                            padding: "8px 10px",
                        }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: `1px solid ${alertColors.border}`, paddingBottom: 4 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                <span style={{ fontSize: 10, fontWeight: 700, color: alertColors.text, fontFamily: theme.typography.fontMono }}>
                                    ALERT #{alertId ? alertId : "—"}
                                </span>
                                <span
                                    style={{
                                        fontSize: 8.5,
                                        fontWeight: 700,
                                        fontFamily: theme.typography.fontMono,
                                        padding: "1px 5px",
                                        borderRadius: 3,
                                        background: "rgba(15, 23, 42, 0.6)",
                                        color: alertColors.text,
                                        border: `1px solid ${alertColors.border}`,
                                    }}
                                >
                                    {alertSeverity || "SEVERITY"}
                                </span>
                            </div>

                            <span style={{ fontSize: 9, fontFamily: theme.typography.fontMono, color: theme.text.muted }}>
                                STATUS: <strong style={{ color: "#f8fafc" }}>{alertStatus || "ACTIVE"}</strong>
                            </span>
                        </div>

                        {alertTitle && (
                            <div style={{ fontSize: 10.5, fontWeight: 700, color: "#f8fafc", fontFamily: theme.typography.fontMono }}>
                                {alertTitle}
                            </div>
                        )}

                        {alertMessage && (
                            <div style={{ fontSize: 9.5, color: "#e2e8f0", fontFamily: theme.typography.fontMono, lineHeight: "1.35" }}>
                                {alertMessage}
                            </div>
                        )}

                        {alertTimestamp && (
                            <div style={{ fontSize: 8.5, color: theme.text.muted, fontFamily: theme.typography.fontMono, textAlign: "right" }}>
                                Dispatched: {alertTimestamp}
                            </div>
                        )}
                    </div>
                ) : (
                    <div
                        style={{
                            background: "rgba(15, 23, 42, 0.4)",
                            border: "1px dashed rgba(148, 163, 184, 0.2)",
                            borderRadius: 6,
                            padding: "8px 10px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            fontFamily: theme.typography.fontMono,
                            fontSize: 9.5,
                            color: theme.text.muted,
                        }}
                    >
                        <span>No active alert dispatched for this event trace.</span>
                        <span style={{ color: "#4ade80", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 3 }}>
                            <IconCheck /> STABLE
                        </span>
                    </div>
                )}
            </div>

            {/* 3. SUPPORTING EVIDENCE SUMMARY & REASONS */}
            {(reason || evidenceSummary.length > 0) && (
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        background: "rgba(15, 23, 42, 0.4)",
                        border: "1px solid rgba(148, 163, 184, 0.1)",
                        borderRadius: 6,
                        padding: "8px 10px",
                    }}
                >
                    <span style={{ fontSize: 9.5, fontWeight: 700, color: theme.text.muted, fontFamily: theme.typography.fontMono, textTransform: "uppercase" }}>
                        Supporting Evidence Summary
                    </span>

                    {reason && (
                        <div
                            style={{
                                fontSize: 9.5,
                                fontFamily: theme.typography.fontMono,
                                color: "#f8fafc",
                                background: "rgba(15, 23, 42, 0.5)",
                                padding: "4px 7px",
                                borderRadius: 4,
                                border: "1px solid rgba(148, 163, 184, 0.1)",
                            }}
                        >
                            <strong style={{ color: "#67e8f9" }}>Reason:</strong> {reason}
                        </div>
                    )}

                    {evidenceSummary.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 2, paddingTop: 2 }}>
                            {evidenceSummary.map((item, idx) => (
                                <div key={idx} style={{ fontSize: 9, fontFamily: theme.typography.fontMono, color: "#cbd5e1" }}>
                                    • {item}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* 4. CANONICAL DISCLAIMER */}
            <div
                style={{
                    fontSize: 8.5,
                    color: "#94a3b8",
                    fontStyle: "italic",
                    lineHeight: 1.35,
                    background: "rgba(15, 23, 42, 0.5)",
                    padding: "6px 8px",
                    borderRadius: 4,
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                }}
            >
                {disclaimer}
            </div>
        </div>
    );
}

// ==========================================
// 11. MAIN TELEMETRY PROCESSING INSPECTOR
// ==========================================
interface TelemetryProcessingInspectorProps {
    onClose: () => void;
    telemetry?: TelemetryLatestResponse | null;
    eventId?: number | null;
    identifier?: string | null;
    isOpen?: boolean;
}

export default function TelemetryProcessingInspector({
    onClose,
    telemetry,
    eventId,
    identifier,
    isOpen = true,
}: TelemetryProcessingInspectorProps) {
    const [isVisible, setIsVisible] = useState<boolean>(false);
    const [isClosing, setIsClosing] = useState<boolean>(false);
    const [currentStage, setCurrentStage] = useState<number>(1);
    const [navDirection, setNavDirection] = useState<"next" | "prev">("next");
    const [isZoomed, setIsZoomed] = useState<boolean>(false);
    const [hoveredWindowIdx, setHoveredWindowIdx] = useState<number | null>(null);
    const [signalViewMode, setSignalViewMode] = useState<"raw" | "conditioned">("raw");

    const [trace, setTrace] = useState<ProcessingTraceResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handleSelectStage = useCallback((targetStage: number) => {
        if (targetStage === currentStage) return;
        setNavDirection(targetStage > currentStage ? "next" : "prev");
        setCurrentStage(targetStage);
    }, [currentStage]);

    const handlePrevStage = useCallback(() => {
        if (currentStage > 1) {
            setNavDirection("prev");
            setCurrentStage((prev) => prev - 1);
        }
    }, [currentStage]);

    const handleNextStage = useCallback(() => {
        if (currentStage < STAGES.length) {
            setNavDirection("next");
            setCurrentStage((prev) => prev + 1);
        }
    }, [currentStage]);

    // Stage 02 RAW <-> CONDITIONED visual transition morph hook
    const rawSamples = trace?.ingestion?.samples_bounded || [];
    const conditionedSamples = trace?.conditioning?.conditioned_samples_bounded || [];
    const { displaySamples: stage2DisplaySamples, isTransitioning: isStage2Transitioning } = useSignalTransition({
        rawSamples,
        conditionedSamples,
        signalViewMode,
    });

    // Resolve target identifier based on priority:
    // 1. Explicit identifier prop
    // 2. Explicit eventId prop
    // 3. First event ID from telemetry.events
    // 4. telemetry.sensor_id
    // 5. "latest" fallback
    const targetIdentifier = useMemo(() => {
        if (identifier) return identifier;
        if (eventId !== undefined && eventId !== null) return String(eventId);
        if (telemetry?.events && telemetry.events.length > 0 && telemetry.events[0].event_id) {
            return String(telemetry.events[0].event_id);
        }
        if (telemetry?.sensor_id) {
            return telemetry.sensor_id;
        }
        return "latest";
    }, [identifier, eventId, telemetry]);

    // Fetch processing trace when inspector is open
    useEffect(() => {
        if (!isOpen) return;

        let isMounted = true;
        setLoading(true);
        setError(null);

        api.getProcessingTrace(targetIdentifier)
            .then((data) => {
                if (isMounted) {
                    setTrace(data);
                    setLoading(false);
                }
            })
            .catch((err: any) => {
                if (isMounted) {
                    console.warn(`[Inspector] Failed to load processing trace for '${targetIdentifier}':`, err);
                    setError(err.message || `Failed to load processing trace for '${targetIdentifier}'`);
                    setTrace(null);
                    setLoading(false);
                }
            });

        return () => {
            isMounted = false;
        };
    }, [isOpen, targetIdentifier]);

    // Entrance animation hook
    useEffect(() => {
        if (isOpen) {
            const timer = requestAnimationFrame(() => {
                setIsVisible(true);
            });
            return () => cancelAnimationFrame(timer);
        }
    }, [isOpen]);

    const handleClose = useCallback(() => {
        setIsClosing(true);
        setTimeout(() => {
            onClose();
        }, 350);
    }, [onClose]);

    if (!isOpen) return null;

    const prefersReducedMotion =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const isAnimated = isVisible && !isClosing;
    const currentSensorId = trace?.metadata.sensor_id || telemetry?.sensor_id || "PZT-Z1-01";
    const currentZoneName = trace?.metadata.zone_name || telemetry?.zone_name || "Zone 1 - Main Deck Girder";

    return (
        <aside
            className="custom-scrollbar"
            style={{
                position: "absolute",
                top: 76,
                right: 20,
                zIndex: 20,
                width: 420,
                maxWidth: "calc(100vw - 40px)",
                height: "calc(100dvh - 96px)",
                maxHeight: "calc(100dvh - 96px)",
                background: theme.surfaces.panel,
                backdropFilter: "blur(14px)",
                border: `1px solid ${theme.surfaces.border}`,
                borderRadius: 10,
                padding: 0,
                color: theme.text.primary,
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
                display: "flex",
                flexDirection: "column",
                fontFamily: theme.typography.fontSans,
                overflow: "hidden",
                boxSizing: "border-box",
                opacity: prefersReducedMotion ? 1 : isAnimated ? 1 : 0.15,
                transform: prefersReducedMotion
                    ? "none"
                    : isAnimated
                    ? "translateX(0)"
                    : "translateX(32px)",
                transition: prefersReducedMotion
                    ? "none"
                    : "opacity 350ms cubic-bezier(0.22, 1, 0.36, 1), transform 350ms cubic-bezier(0.22, 1, 0.36, 1)",
                willChange: "transform, opacity",
            }}
            aria-label="Telemetry Processing Inspector Panel"
        >
            {/* CSS Animation for Stage Transition & Accessibility */}
            <style>{`
                @keyframes stageSlideNext {
                    from {
                        opacity: 0;
                        transform: translateX(16px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
                @keyframes stageSlidePrev {
                    from {
                        opacity: 0;
                        transform: translateX(-16px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
                .stage-page-anim-next {
                    animation: stageSlideNext 260ms cubic-bezier(0.16, 1, 0.3, 1);
                }
                .stage-page-anim-prev {
                    animation: stageSlidePrev 260ms cubic-bezier(0.16, 1, 0.3, 1);
                }
                .stage-dot-btn:focus-visible {
                    outline: 2px solid #38bdf8;
                    outline-offset: 2px;
                }
                @media (prefers-reduced-motion: reduce) {
                    .stage-page-anim-next,
                    .stage-page-anim-prev {
                        animation: none !important;
                        transform: none !important;
                    }
                }
            `}</style>

            {/* Header Bar */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    background: "rgba(15, 23, 42, 0.6)",
                    borderBottom: "1px solid rgba(148, 163, 184, 0.15)",
                }}
            >
                <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <h2
                            style={{
                                margin: 0,
                                fontSize: 13,
                                fontWeight: 700,
                                letterSpacing: "0.06em",
                                color: "#67e8f9",
                                textTransform: "uppercase",
                            }}
                        >
                            Telemetry Processing Inspector
                        </h2>
                    </div>
                    <div
                        style={{
                            fontSize: 10,
                            color: theme.text.muted,
                            fontFamily: theme.typography.fontMono,
                            marginTop: 2,
                        }}
                    >
                        Target Node: {currentSensorId} · {currentZoneName}
                    </div>
                </div>

                <button
                    onClick={handleClose}
                    style={{
                        background: "rgba(30, 41, 59, 0.6)",
                        border: "1px solid rgba(148, 163, 184, 0.2)",
                        color: theme.text.secondary,
                        borderRadius: 6,
                        padding: "5px 9px",
                        fontSize: 11,
                        fontWeight: 600,
                        fontFamily: theme.typography.fontMono,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 5,
                        transition: "all 0.15s ease",
                    }}
                    title="Close Inspector & Return to Operations HUD"
                    aria-label="Close Inspector"
                >
                    <IconClose />
                    <span>Close</span>
                </button>
            </div>

            {/* Dynamic Sliding-Window Fading Stage Pagination */}
            <DynamicStagePagination
                currentStage={currentStage}
                onSelectStage={handleSelectStage}
                onPrevStage={handlePrevStage}
                onNextStage={handleNextStage}
            />

            {/* Content Body: Only Renders the Current Paginated Stage */}
            <div
                className="custom-scrollbar"
                style={{
                    flex: 1,
                    padding: 14,
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                }}
            >
                {/* 1. Loading State */}
                {loading && (
                    <div
                        style={{
                            background: "rgba(15, 23, 42, 0.5)",
                            border: "1px solid rgba(56, 189, 248, 0.3)",
                            borderRadius: 8,
                            padding: "16px 14px",
                            textAlign: "center",
                            fontFamily: theme.typography.fontMono,
                            fontSize: 11,
                            color: theme.text.muted,
                        }}
                    >
                        <div style={{ color: "#38bdf8", fontWeight: 700, marginBottom: 4 }}>
                            FETCHING PROCESSING TRACE...
                        </div>
                        <div style={{ fontSize: 10, color: "#94a3b8" }}>
                            Querying backend trace for identifier: &quot;{targetIdentifier}&quot;
                        </div>
                    </div>
                )}

                {/* 2. Error State */}
                {!loading && error && (
                    <div
                        style={{
                            background: "rgba(239, 68, 68, 0.1)",
                            border: "1px solid rgba(239, 68, 68, 0.3)",
                            borderRadius: 8,
                            padding: "14px",
                            fontFamily: theme.typography.fontMono,
                            fontSize: 11,
                        }}
                    >
                        <div style={{ fontWeight: 700, color: "#fca5a5", marginBottom: 4, display: "flex", alignItems: "center", gap: 5 }}>
                            <IconAlert />
                            <span>TRACE FETCH FAILED</span>
                        </div>
                        <div style={{ color: "#e2e8f0", fontSize: 10, marginBottom: 6 }}>
                            Could not load telemetry processing trace for identifier &quot;{targetIdentifier}&quot;.
                        </div>
                        <div style={{ fontSize: 9, color: "#cbd5e1", background: "rgba(15, 23, 42, 0.5)", padding: "6px 8px", borderRadius: 4 }}>
                            {error}
                        </div>
                    </div>
                )}

                {/* 3. Paginated Evidence Views */}
                {!loading && trace && (
                    <div
                        key={currentStage}
                        className={navDirection === "next" ? "stage-page-anim-next" : "stage-page-anim-prev"}
                        style={{ display: "flex", flexDirection: "column", gap: 12 }}
                    >
                        {/* STAGE 1: INGESTION */}
                        {currentStage === 1 && (
                            <>
                                <IngestionMetadataBox metadata={trace.metadata} />
                                <RawTelemetryGrid ingestion={trace.ingestion} />
                                <WaveformCanvas
                                    samples={trace.ingestion.samples_bounded || []}
                                    sampleRate={trace.ingestion.sample_rate_hz}
                                    totalSamplesCount={trace.ingestion.samples_count}
                                    peakAmplitude={trace.ingestion.peak_amplitude}
                                    showThreshold={false}
                                    showWindows={false}
                                    allowZoom={false}
                                    title="Raw Ingested Signal (Full Overview)"
                                    subBadge={trace.ingestion.is_bounded ? "BOUNDED SAMPLES" : "FULL SAMPLES"}
                                    subBadgeColor={trace.ingestion.is_bounded ? "#38bdf8" : "#4ade80"}
                                />
                            </>
                        )}

                        {/* STAGE 2: CONDITIONING */}
                        {currentStage === 2 && (
                            <>
                                <ConditioningParamsGrid
                                    conditioning={trace.conditioning}
                                    signalViewMode={signalViewMode}
                                    onSignalViewModeChange={setSignalViewMode}
                                    isTransitioning={isStage2Transitioning}
                                />
                                <WaveformCanvas
                                    samples={stage2DisplaySamples}
                                    sampleRate={trace.ingestion.sample_rate_hz}
                                    totalSamplesCount={trace.ingestion.samples_count}
                                    peakAmplitude={trace.ingestion.peak_amplitude}
                                    showThreshold={false}
                                    showWindows={false}
                                    allowZoom={false}
                                    title={
                                        isStage2Transitioning
                                            ? signalViewMode === "conditioned"
                                                ? "Conditioning Transformation (Raw → Conditioned)"
                                                : "Conditioning Reversion (Conditioned → Raw)"
                                            : signalViewMode === "conditioned"
                                            ? "Conditioned Signal (DC Removed + Filtered)"
                                            : "Raw / Unconditioned Signal"
                                    }
                                    subBadge={
                                        isStage2Transitioning
                                            ? "APPLYING CONDITIONED VIEW"
                                            : signalViewMode === "conditioned"
                                            ? "CONDITIONED"
                                            : "RAW / UNCONDITIONED"
                                    }
                                    subBadgeColor={
                                        isStage2Transitioning
                                            ? "#fbbf24"
                                            : signalViewMode === "conditioned"
                                            ? "#38bdf8"
                                            : "#94a3b8"
                                    }
                                />
                            </>
                        )}

                        {/* STAGE 3: EVENT DETECTION */}
                        {currentStage === 3 && (
                            <>
                                <EventDetectionParamsGrid eventDetection={trace.event_detection} />
                                <WaveformCanvas
                                    samples={
                                        trace.conditioning?.conditioned_samples_bounded ||
                                        trace.ingestion.samples_bounded ||
                                        []
                                    }
                                    sampleRate={trace.ingestion.sample_rate_hz}
                                    totalSamplesCount={trace.ingestion.samples_count}
                                    peakAmplitude={trace.ingestion.peak_amplitude}
                                    detectionThreshold={trace.event_detection.detection_threshold}
                                    windows={trace.event_detection.detected_windows}
                                    hoveredWindowIdx={hoveredWindowIdx}
                                    onHoverWindow={setHoveredWindowIdx}
                                    showThreshold={true}
                                    showWindows={true}
                                    allowZoom={true}
                                    isZoomed={isZoomed}
                                    onToggleZoom={() => setIsZoomed(!isZoomed)}
                                    title={
                                        isZoomed
                                            ? "Conditioned Signal (Activity Detail Zoom)"
                                            : "Conditioned Signal (Full Overview)"
                                    }
                                    subBadge="DETECTION THRESHOLD"
                                    subBadgeColor="#fbbf24"
                                />
                                <DetectedWindowsList
                                    windows={trace.event_detection.detected_windows || []}
                                    hoveredWindowIdx={hoveredWindowIdx}
                                    setHoveredWindowIdx={setHoveredWindowIdx}
                                />
                            </>
                        )}

                        {/* STAGE 4: FEATURE EXTRACTION */}
                        {currentStage === 4 && (
                            <>
                                <FeatureExtractionSection
                                    features={trace.features}
                                    metadataEventId={trace.metadata.event_id}
                                />
                                <WaveformCanvas
                                    samples={
                                        trace.conditioning?.conditioned_samples_bounded ||
                                        trace.ingestion.samples_bounded ||
                                        []
                                    }
                                    sampleRate={trace.ingestion.sample_rate_hz}
                                    totalSamplesCount={trace.ingestion.samples_count}
                                    peakAmplitude={trace.ingestion.peak_amplitude}
                                    detectionThreshold={trace.event_detection?.detection_threshold}
                                    windows={trace.event_detection?.detected_windows}
                                    hoveredWindowIdx={hoveredWindowIdx}
                                    onHoverWindow={setHoveredWindowIdx}
                                    showThreshold={true}
                                    showWindows={true}
                                    allowZoom={false}
                                    isZoomed={true}
                                    title="Extracted Event Activity (Magnified View)"
                                    subBadge={
                                        trace.features?.event_id
                                            ? `EVENT #${trace.features.event_id}`
                                            : "ACTIVE REGION"
                                    }
                                    subBadgeColor="#fbbf24"
                                />
                            </>
                        )}

                        {/* STAGE 5: BASELINE REFERENCE */}
                        {currentStage === 5 && (
                            <>
                                <BaselineReferenceSection
                                    baseline={trace.baseline}
                                    zoneName={trace.metadata.zone_name}
                                />
                                <CurrentVsBaselineCard
                                    features={trace.features}
                                    baseline={trace.baseline}
                                />
                            </>
                        )}

                        {/* STAGE 6: ANOMALY EVALUATION */}
                        {currentStage === 6 && (
                            <>
                                <AnomalyEvaluationSection anomaly={trace.anomaly} />
                            </>
                        )}

                        {/* STAGE 7: PERSISTENCE */}
                        {currentStage === 7 && (
                            <>
                                <PersistenceSection persistence={trace.persistence} />
                            </>
                        )}

                        {/* STAGE 8: CROSS-SENSOR CORRELATION */}
                        {currentStage === 8 && (
                            <>
                                <CorrelationSection correlation={trace.correlation} />
                            </>
                        )}

                        {/* STAGE 9: HEALTH & ALERT */}
                        {currentStage === 9 && (
                            <>
                                <HealthAlertSection health={trace.health} alert={trace.alert} />
                            </>
                        )}
                    </div>
                )}

                {/* 4. Empty State (No Identifier / No Data) */}
                {!loading && !trace && !error && (
                    <div
                        style={{
                            background: "rgba(15, 23, 42, 0.5)",
                            border: "1px dashed rgba(148, 163, 184, 0.2)",
                            borderRadius: 8,
                            padding: "14px",
                            textAlign: "center",
                            fontFamily: theme.typography.fontMono,
                            fontSize: 11,
                            color: theme.text.muted,
                        }}
                    >
                        <div style={{ color: "#38bdf8", fontWeight: 700, marginBottom: 4 }}>
                            INSPECTION SESSION IDLE
                        </div>
                        <div>Select a telemetry event to inspect.</div>
                    </div>
                )}
            </div>
        </aside>
    );
}
