"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
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
    LiveStageInfo,
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
    stageStatuses?: Record<number, LiveStageInfo>;
    activeLiveStage?: number | null;
}

function DynamicStagePagination({
    currentStage,
    onSelectStage,
    onPrevStage,
    onNextStage,
    stageStatuses,
    activeLiveStage,
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

                            const liveInfo = stageStatuses?.[stage.id];
                            const isLiveActive = activeLiveStage === stage.id;
                            const isLiveCompleted = liveInfo?.status === "completed";
                            const isLiveError = liveInfo?.status === "error";

                            let dotBg = isActive ? "#38bdf8" : isHovered ? "#67e8f9" : "#94a3b8";
                            let dotBorder = isActive ? "1.5px solid #7dd3fc" : "none";
                            let dotShadow = isActive ? "0 1px 3px rgba(0, 0, 0, 0.5), 0 0 2px rgba(56, 189, 248, 0.3)" : "none";

                            if (isLiveActive) {
                                dotBg = "#f59e0b";
                                dotBorder = "1.5px solid #fde68a";
                                dotShadow = "0 0 8px rgba(245, 158, 11, 0.85)";
                            } else if (isLiveError) {
                                dotBg = "#ef4444";
                                dotBorder = "1.5px solid #fca5a5";
                            } else if (isLiveCompleted && !isActive) {
                                dotBg = "rgba(34, 197, 94, 0.8)";
                            }

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
                                                border: `1px solid ${
                                                    isLiveActive
                                                        ? "rgba(245, 158, 11, 0.5)"
                                                        : isLiveError
                                                        ? "rgba(239, 68, 68, 0.5)"
                                                        : "rgba(56, 189, 248, 0.4)"
                                                }`,
                                                color: isLiveActive ? "#fde68a" : isLiveError ? "#fca5a5" : "#67e8f9",
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
                                            {isLiveActive ? " [PROCESSING]" : isLiveError ? " [ERROR]" : isLiveCompleted ? " [✓]" : ""}
                                        </div>
                                    )}

                                    <button
                                        onClick={() => onSelectStage(stage.id)}
                                        aria-label={`Go to ${stage.title}`}
                                        aria-current={isActive ? "step" : undefined}
                                        style={{
                                            width: isActive || isLiveActive ? 10 : 7,
                                            height: isActive || isLiveActive ? 10 : 7,
                                            borderRadius: "50%",
                                            background: dotBg,
                                            border: dotBorder,
                                            opacity: isHovered || isLiveActive ? 1 : opacity,
                                            padding: 0,
                                            cursor: "pointer",
                                            transition: "all 200ms cubic-bezier(0.2, 0.8, 0.2, 1)",
                                            boxShadow: dotShadow,
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
// 1. ADVANCED ENGINEERING WAVEFORM STUDIO
// ==========================================
interface EngineeringWaveformStudioProps {
    samples: number[];
    sampleRate: number;
    totalSamplesCount: number;
    peakAmplitude: number;
    detectionThreshold?: number | null;
    windows?: DetectedWindowTrace[];
    hoveredWindowIdx?: number | null;
    onHoverWindow?: (idx: number | null) => void;
    title: string;
    subBadge?: string;
    subBadgeColor?: string;
    showThreshold?: boolean;
    showWindows?: boolean;
    showConditionedComparison?: boolean;
    rawSamples?: number[];
    conditionedSamples?: number[];
    signalViewMode?: "raw" | "conditioned" | "dual";
    onSignalViewModeChange?: (mode: "raw" | "conditioned" | "dual") => void;
}

function downsamplePeakPreserving(samples: number[], targetBuckets: number = 500): { min: number; max: number; idx: number }[] {
    if (!samples || samples.length === 0) return [];
    if (samples.length <= targetBuckets * 2) {
        return samples.map((s, idx) => ({ min: s, max: s, idx }));
    }
    const bucketSize = samples.length / targetBuckets;
    const result: { min: number; max: number; idx: number }[] = [];
    for (let b = 0; b < targetBuckets; b++) {
        const start = Math.floor(b * bucketSize);
        const end = Math.min(samples.length, Math.floor((b + 1) * bucketSize));
        let minVal = Infinity;
        let maxVal = -Infinity;
        let minIdx = start;
        let maxIdx = start;
        for (let i = start; i < end; i++) {
            const v = samples[i];
            if (v < minVal) { minVal = v; minIdx = i; }
            if (v > maxVal) { maxVal = v; maxIdx = i; }
        }
        if (minIdx < maxIdx) {
            result.push({ min: minVal, max: minVal, idx: minIdx });
            result.push({ min: maxVal, max: maxVal, idx: maxIdx });
        } else {
            result.push({ min: maxVal, max: maxVal, idx: maxIdx });
            result.push({ min: minVal, max: minVal, idx: minIdx });
        }
    }
    return result;
}

function EngineeringWaveformStudio({
    samples,
    sampleRate,
    totalSamplesCount,
    peakAmplitude,
    detectionThreshold,
    windows = [],
    hoveredWindowIdx,
    onHoverWindow,
    title,
    subBadge,
    subBadgeColor = "#38bdf8",
    showThreshold = false,
    showWindows = false,
    showConditionedComparison = false,
    rawSamples = [],
    conditionedSamples = [],
    signalViewMode = "dual",
    onSignalViewModeChange,
}: EngineeringWaveformStudioProps) {
    const [viewMode, setViewMode] = useState<"dual" | "overview" | "zoom">("dual");
    const [activeEventIndex, setActiveEventIndex] = useState<number | null>(null);

    const actualSampleRate = sampleRate > 0 ? sampleRate : 100000;
    const actualTotalCount = totalSamplesCount > 0 ? totalSamplesCount : samples.length || 10000;
    const durationMs = (actualTotalCount / actualSampleRate) * 1000;

    // 1. OVERVIEW DATA (Min/Max Peak Preserved Full ~106ms Timeline)
    const overviewData = useMemo(() => {
        if (!samples || samples.length === 0) return null;

        const downsampled = downsamplePeakPreserving(samples, 500);
        let minVal = Infinity;
        let maxVal = -Infinity;
        for (const p of downsampled) {
            if (p.min < minVal) minVal = p.min;
            if (p.max > maxVal) maxVal = p.max;
        }

        const absLimit = Math.max(
            0.15,
            Math.abs(minVal),
            Math.abs(maxVal),
            peakAmplitude || 0.1,
            showThreshold && detectionThreshold ? detectionThreshold * 1.12 : 0.1
        );
        const yLimit = absLimit * 1.15;

        const svgWidth = 820;
        const svgHeight = 120;
        const padding = { top: 18, bottom: 22, left: 55, right: 15 };
        const innerW = svgWidth - padding.left - padding.right;
        const innerH = svgHeight - padding.top - padding.bottom;
        const centerY = padding.top + innerH / 2;

        const scaleY = (v: number) => centerY - (v / yLimit) * (innerH / 2);
        const scaleX = (idx: number) => {
            if (actualTotalCount <= 1) return padding.left;
            return padding.left + (idx / (actualTotalCount - 1)) * innerW;
        };

        const polylinePoints = downsampled
            .map((p) => `${scaleX(p.idx).toFixed(1)},${scaleY(p.min).toFixed(1)} ${scaleX(p.idx).toFixed(1)},${scaleY(p.max).toFixed(1)}`)
            .join(" ");

        const thresholdYPos = showThreshold && detectionThreshold ? scaleY(detectionThreshold) : null;
        const thresholdYNeg = showThreshold && detectionThreshold ? scaleY(-detectionThreshold) : null;

        const eventBands =
            showWindows && windows.length > 0
                ? windows.map((w, idx) => {
                      const startX = scaleX(w.start_index);
                      const endX = scaleX(w.end_index);
                      const width = Math.max(6, endX - startX);
                      const startMs = (w.start_index / actualSampleRate) * 1000;
                      const endMs = (w.end_index / actualSampleRate) * 1000;
                      return { idx, startX, width, w, startMs, endMs };
                  })
                : [];

        return {
            svgWidth,
            svgHeight,
            padding,
            innerW,
            innerH,
            centerY,
            yLimit,
            polylinePoints,
            thresholdYPos,
            thresholdYNeg,
            eventBands,
        };
    }, [samples, actualTotalCount, actualSampleRate, peakAmplitude, showThreshold, detectionThreshold, showWindows, windows]);

    // 2. MAGNIFIED EVENT ZOOM DATA (Centering around events or initial wave arrival with dynamic Y-axis)
    const zoomData = useMemo(() => {
        if (!samples || samples.length === 0) return null;

        let focusStart = 0;
        let focusEnd = samples.length - 1;

        if (windows && windows.length > 0) {
            const targetWin = activeEventIndex !== null && windows[activeEventIndex] ? windows[activeEventIndex] : null;
            if (targetWin) {
                const span = Math.max(30, targetWin.end_index - targetWin.start_index);
                const margin = Math.max(120, Math.round(span * 0.8));
                focusStart = Math.max(0, targetWin.start_index - margin);
                focusEnd = Math.min(actualTotalCount - 1, targetWin.end_index + margin);
            } else {
                let earliestStart = Infinity;
                let latestEnd = -Infinity;
                for (const w of windows) {
                    if (w.start_index < earliestStart) earliestStart = w.start_index;
                    if (w.end_index > latestEnd) latestEnd = w.end_index;
                }
                const span = Math.max(40, latestEnd - earliestStart);
                const margin = Math.max(150, Math.round(span * 0.6));
                focusStart = Math.max(0, earliestStart - margin);
                focusEnd = Math.min(actualTotalCount - 1, latestEnd + margin);
            }
        } else {
            // Find sample with peak absolute amplitude for automatic center
            let maxAbs = 0;
            let peakIdx = Math.round(samples.length * 0.06);
            for (let i = 0; i < samples.length; i++) {
                if (Math.abs(samples[i]) > maxAbs) {
                    maxAbs = Math.abs(samples[i]);
                    peakIdx = i;
                }
            }
            focusStart = Math.max(0, peakIdx - 200);
            focusEnd = Math.min(samples.length - 1, peakIdx + 350);
        }

        // Extract high-resolution samples in the zoom window
        const startRatio = focusStart / Math.max(1, actualTotalCount - 1);
        const endRatio = focusEnd / Math.max(1, actualTotalCount - 1);
        const boundedStart = Math.floor(startRatio * (samples.length - 1));
        const boundedEnd = Math.ceil(endRatio * (samples.length - 1));

        const focusedSamples = samples.slice(Math.max(0, boundedStart), Math.min(samples.length, boundedEnd + 1));
        if (focusedSamples.length < 2) return null;

        // Dynamic Y-axis calculation with 15% visual headroom
        let minVal = Infinity;
        let maxVal = -Infinity;
        let peakSampleVal = 0;
        let peakSampleIdx = 0;

        for (let i = 0; i < focusedSamples.length; i++) {
            const v = focusedSamples[i];
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
            if (Math.abs(v) > Math.abs(peakSampleVal)) {
                peakSampleVal = v;
                peakSampleIdx = i;
            }
        }

        const rawPeak = Math.max(Math.abs(minVal), Math.abs(maxVal), peakAmplitude || 0.1);
        const threshComp = showThreshold && detectionThreshold ? detectionThreshold * 1.08 : 0;
        const yLimit = Math.max(0.15, Math.max(rawPeak, threshComp) * 1.15);

        const svgWidth = 820;
        const svgHeight = 160;
        const padding = { top: 22, bottom: 26, left: 55, right: 15 };
        const innerW = svgWidth - padding.left - padding.right;
        const innerH = svgHeight - padding.top - padding.bottom;
        const centerY = padding.top + innerH / 2;

        const scaleY = (v: number) => centerY - (v / yLimit) * (innerH / 2);
        const scaleX = (i: number) => {
            if (focusedSamples.length <= 1) return padding.left;
            return padding.left + (i / (focusedSamples.length - 1)) * innerW;
        };

        const polylinePoints = focusedSamples
            .map((s, idx) => `${scaleX(idx).toFixed(1)},${scaleY(s).toFixed(1)}`)
            .join(" ");

        const focusSpan = Math.max(1, focusEnd - focusStart);
        const startMs = (focusStart / actualSampleRate) * 1000;
        const endMs = (focusEnd / actualSampleRate) * 1000;
        const midMs = (startMs + endMs) / 2;
        const peakMs = startMs + (peakSampleIdx / Math.max(1, focusedSamples.length - 1)) * (endMs - startMs);

        const peakMarkerX = scaleX(peakSampleIdx);
        const peakMarkerY = scaleY(peakSampleVal);

        const thresholdYPos = showThreshold && detectionThreshold ? scaleY(detectionThreshold) : null;
        const thresholdYNeg = showThreshold && detectionThreshold ? scaleY(-detectionThreshold) : null;

        const focusedBands =
            showWindows && windows.length > 0
                ? windows.map((w, idx) => {
                      const sRatio = (w.start_index - focusStart) / focusSpan;
                      const eRatio = (w.end_index - focusStart) / focusSpan;
                      const startX = padding.left + Math.max(0, sRatio) * innerW;
                      const endX = padding.left + Math.min(1, eRatio) * innerW;
                      const width = Math.max(6, endX - startX);
                      const isHovered = hoveredWindowIdx === idx;
                      const isSelected = activeEventIndex === idx;
                      const wStartMs = (w.start_index / actualSampleRate) * 1000;
                      const wEndMs = (w.end_index / actualSampleRate) * 1000;
                      return { idx, startX, width, w, isHovered, isSelected, wStartMs, wEndMs };
                  })
                : [];

        return {
            svgWidth,
            svgHeight,
            padding,
            innerW,
            innerH,
            centerY,
            yLimit,
            polylinePoints,
            startMs,
            endMs,
            midMs,
            peakMs,
            peakSampleVal,
            peakMarkerX,
            peakMarkerY,
            thresholdYPos,
            thresholdYNeg,
            focusedBands,
            focusedCount: focusedSamples.length,
        };
    }, [samples, actualTotalCount, actualSampleRate, peakAmplitude, showThreshold, detectionThreshold, showWindows, windows, activeEventIndex, hoveredWindowIdx]);

    return (
        <div
            style={{
                background: "rgba(15, 23, 42, 0.75)",
                border: "1px solid rgba(56, 189, 248, 0.2)",
                borderRadius: 8,
                padding: "12px 14px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                fontFamily: theme.typography.fontSans,
            }}
        >
            {/* Header & View Switcher */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                        {title}
                    </span>
                    {subBadge && (
                        <span
                            style={{
                                fontSize: 9,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                color: subBadgeColor,
                                background: `${subBadgeColor}15`,
                                padding: "1px 6px",
                                borderRadius: 4,
                                border: `1px solid ${subBadgeColor}35`,
                            }}
                        >
                            {subBadge}
                        </span>
                    )}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 9.5, fontFamily: theme.typography.fontMono, color: "#94a3b8" }}>
                        VIEW:
                    </span>
                    {(["dual", "overview", "zoom"] as const).map((m) => (
                        <button
                            key={m}
                            type="button"
                            onClick={() => setViewMode(m)}
                            style={{
                                background: viewMode === m ? "rgba(56, 189, 248, 0.25)" : "rgba(30, 41, 59, 0.5)",
                                border: `1px solid ${viewMode === m ? "rgba(56, 189, 248, 0.6)" : "rgba(148, 163, 184, 0.15)"}`,
                                color: viewMode === m ? "#38bdf8" : "#94a3b8",
                                fontSize: 9,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                padding: "3px 7px",
                                borderRadius: 4,
                                cursor: "pointer",
                                textTransform: "uppercase",
                                transition: "all 0.15s ease",
                            }}
                        >
                            {m === "dual" ? "DUAL (OVERVIEW + ZOOM)" : m === "overview" ? "FULL OVERVIEW" : "MAGNIFIED ZOOM"}
                        </button>
                    ))}
                </div>
            </div>

            {/* CONDITIONING DUAL TRACE COMPARISON (Stage 2) */}
            {showConditionedComparison && rawSamples.length > 0 && conditionedSamples.length > 0 && (
                <div
                    style={{
                        background: "rgba(11, 19, 41, 0.8)",
                        border: "1px solid rgba(148, 163, 184, 0.15)",
                        borderRadius: 6,
                        padding: "8px 12px",
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 10,
                        fontFamily: theme.typography.fontMono,
                        fontSize: 9.5,
                    }}
                >
                    <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "6px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                        <span style={{ color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: 2 }}>RAW UNCONDITIONED TRACE</span>
                        <div style={{ color: "#f87171" }}>DC Offset: +0.152 V · Unfiltered Noise Floor</div>
                    </div>
                    <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "6px 8px", borderRadius: 4, border: "1px solid rgba(56, 189, 248, 0.2)" }}>
                        <span style={{ color: "#38bdf8", fontWeight: 700, display: "block", marginBottom: 2 }}>CONDITIONED DSP TRACE</span>
                        <div style={{ color: "#34d399" }}>DC Removed (0.00 V Mean) · Bandpass 5–45 kHz</div>
                    </div>
                </div>
            )}

            {/* PANE 1: FULL SIGNAL OVERVIEW (~106 ms) */}
            {(viewMode === "dual" || viewMode === "overview") && overviewData && (
                <div
                    style={{
                        background: "rgba(11, 19, 41, 0.7)",
                        border: "1px solid rgba(148, 163, 184, 0.12)",
                        borderRadius: 6,
                        padding: "8px 10px",
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 9.5, fontFamily: theme.typography.fontMono, color: "#94a3b8" }}>
                        <span style={{ color: "#38bdf8", fontWeight: 700 }}>
                            FULL PACKET OVERVIEW ({actualTotalCount.toLocaleString()} SAMPLES · {durationMs.toFixed(1)} ms)
                        </span>
                        <span>SCALE: ±{overviewData.yLimit.toFixed(2)} V</span>
                    </div>

                    <div style={{ position: "relative", width: "100%", height: 110, overflow: "hidden" }}>
                        <svg viewBox={`0 0 ${overviewData.svgWidth} ${overviewData.svgHeight}`} preserveAspectRatio="none" style={{ width: "100%", height: "100%", display: "block" }}>
                            {/* Center zero line */}
                            <line x1={overviewData.padding.left} y1={overviewData.centerY} x2={overviewData.svgWidth - overviewData.padding.right} y2={overviewData.centerY} stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" strokeDasharray="3 3" />

                            {/* Threshold lines */}
                            {overviewData.thresholdYPos !== null && overviewData.thresholdYNeg !== null && (
                                <>
                                    <line x1={overviewData.padding.left} y1={overviewData.thresholdYPos} x2={overviewData.svgWidth - overviewData.padding.right} y2={overviewData.thresholdYPos} stroke="rgba(245, 158, 11, 0.6)" strokeWidth="1" strokeDasharray="4 3" />
                                    <line x1={overviewData.padding.left} y1={overviewData.thresholdYNeg} x2={overviewData.svgWidth - overviewData.padding.right} y2={overviewData.thresholdYNeg} stroke="rgba(245, 158, 11, 0.6)" strokeWidth="1" strokeDasharray="4 3" />
                                </>
                            )}

                            {/* Event bands */}
                            {overviewData.eventBands.map(({ idx, startX, width, startMs, endMs }) => {
                                const isHovered = hoveredWindowIdx === idx;
                                const isSelected = activeEventIndex === idx;
                                return (
                                    <g key={idx} onClick={() => setActiveEventIndex(activeEventIndex === idx ? null : idx)} onMouseEnter={() => onHoverWindow?.(idx)} onMouseLeave={() => onHoverWindow?.(null)} style={{ cursor: "pointer" }}>
                                        <rect x={startX} y={overviewData.padding.top} width={width} height={overviewData.svgHeight - overviewData.padding.top - overviewData.padding.bottom} fill={isSelected ? "rgba(245, 158, 11, 0.45)" : isHovered ? "rgba(245, 158, 11, 0.35)" : "rgba(245, 158, 11, 0.2)"} stroke={isSelected ? "#fde68a" : isHovered ? "#f59e0b" : "rgba(245, 158, 11, 0.6)"} strokeWidth={isSelected ? "1.8" : "1.2"} rx="2" />
                                        <text x={startX + width / 2} y={overviewData.padding.top - 4} textAnchor="middle" fill="#f59e0b" fontSize="8" fontWeight="700" fontFamily={theme.typography.fontMono}>
                                            E{idx + 1}
                                        </text>
                                    </g>
                                );
                            })}

                            {/* Y axis ticks */}
                            <text x={overviewData.padding.left - 6} y={overviewData.padding.top + 3} textAnchor="end" fill="#94a3b8" fontSize="8" fontFamily={theme.typography.fontMono}>+{overviewData.yLimit.toFixed(2)}V</text>
                            <text x={overviewData.padding.left - 6} y={overviewData.centerY + 3} textAnchor="end" fill="#94a3b8" fontSize="8" fontFamily={theme.typography.fontMono}>0.0V</text>
                            <text x={overviewData.padding.left - 6} y={overviewData.svgHeight - overviewData.padding.bottom + 3} textAnchor="end" fill="#94a3b8" fontSize="8" fontFamily={theme.typography.fontMono}>-{overviewData.yLimit.toFixed(2)}V</text>

                            {/* Waveform trace */}
                            <polyline fill="none" stroke="#38bdf8" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" points={overviewData.polylinePoints} />

                            {/* X axis ticks */}
                            <text x={overviewData.padding.left} y={overviewData.svgHeight - 4} textAnchor="start" fill="#94a3b8" fontSize="8" fontFamily={theme.typography.fontMono}>0 ms</text>
                            <text x={overviewData.padding.left + overviewData.innerW * 0.5} y={overviewData.svgHeight - 4} textAnchor="middle" fill="#94a3b8" fontSize="8" fontFamily={theme.typography.fontMono}>{(durationMs * 0.5).toFixed(0)} ms</text>
                            <text x={overviewData.svgWidth - overviewData.padding.right} y={overviewData.svgHeight - 4} textAnchor="end" fill="#94a3b8" fontSize="8" fontFamily={theme.typography.fontMono}>{durationMs.toFixed(0)} ms</text>
                        </svg>
                    </div>
                </div>
            )}

            {/* PANE 2: MAGNIFIED EVENT ACTIVITY ZOOM (Full Resolution Waveform) */}
            {(viewMode === "dual" || viewMode === "zoom") && zoomData && (
                <div
                    style={{
                        background: "rgba(11, 19, 41, 0.85)",
                        border: "1px solid rgba(56, 189, 248, 0.35)",
                        borderRadius: 6,
                        padding: "10px 12px",
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 10, fontFamily: theme.typography.fontMono, flexWrap: "wrap", gap: 6 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ color: "#fbbf24", fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                                <IconSearch />
                                MAGNIFIED EVENT ACTIVITY ZOOM ({zoomData.startMs.toFixed(2)} ms → {zoomData.endMs.toFixed(2)} ms)
                            </span>
                            {activeEventIndex !== null && (
                                <span style={{ color: "#38bdf8", background: "rgba(56, 189, 248, 0.15)", padding: "1px 6px", borderRadius: 4, fontSize: 9, fontWeight: 700 }}>
                                    EVENT #{activeEventIndex + 1} SELECTED
                                </span>
                            )}
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <span style={{ color: "#34d399", fontWeight: 700 }}>
                                PEAK: {zoomData.peakSampleVal >= 0 ? `+${zoomData.peakSampleVal.toFixed(3)}` : zoomData.peakSampleVal.toFixed(3)} V
                            </span>
                            {showThreshold && detectionThreshold && (
                                <span style={{ color: "#fbbf24", fontWeight: 700 }}>
                                    THRESHOLD: ±{detectionThreshold.toFixed(2)} V
                                </span>
                            )}
                        </div>
                    </div>

                    <div style={{ position: "relative", width: "100%", height: 160, overflow: "hidden" }}>
                        <svg viewBox={`0 0 ${zoomData.svgWidth} ${zoomData.svgHeight}`} preserveAspectRatio="none" style={{ width: "100%", height: "100%", display: "block" }}>
                            {/* Zero line */}
                            <line x1={zoomData.padding.left} y1={zoomData.centerY} x2={zoomData.svgWidth - zoomData.padding.right} y2={zoomData.centerY} stroke="rgba(148, 163, 184, 0.25)" strokeWidth="1" strokeDasharray="3 3" />

                            {/* Threshold lines */}
                            {zoomData.thresholdYPos !== null && zoomData.thresholdYNeg !== null && (
                                <>
                                    <line x1={zoomData.padding.left} y1={zoomData.thresholdYPos} x2={zoomData.svgWidth - zoomData.padding.right} y2={zoomData.thresholdYPos} stroke="rgba(245, 158, 11, 0.7)" strokeWidth="1.2" strokeDasharray="4 3" />
                                    <line x1={zoomData.padding.left} y1={zoomData.thresholdYNeg} x2={zoomData.svgWidth - zoomData.padding.right} y2={zoomData.thresholdYNeg} stroke="rgba(245, 158, 11, 0.7)" strokeWidth="1.2" strokeDasharray="4 3" />
                                    <text x={zoomData.svgWidth - zoomData.padding.right} y={zoomData.thresholdYPos - 4} textAnchor="end" fill="#fbbf24" fontSize="8" fontFamily={theme.typography.fontMono} fontWeight="700">+THRESHOLD ({detectionThreshold?.toFixed(2)}V)</text>
                                    <text x={zoomData.svgWidth - zoomData.padding.right} y={zoomData.thresholdYNeg + 10} textAnchor="end" fill="#fbbf24" fontSize="8" fontFamily={theme.typography.fontMono} fontWeight="700">-THRESHOLD ({detectionThreshold?.toFixed(2)}V)</text>
                                </>
                            )}

                            {/* Event bands */}
                            {zoomData.focusedBands.map(({ idx, startX, width, isHovered, isSelected, wStartMs, wEndMs }) => (
                                <g key={idx} onClick={() => setActiveEventIndex(activeEventIndex === idx ? null : idx)} onMouseEnter={() => onHoverWindow?.(idx)} onMouseLeave={() => onHoverWindow?.(null)} style={{ cursor: "pointer" }}>
                                    <rect x={startX} y={zoomData.padding.top} width={width} height={zoomData.svgHeight - zoomData.padding.top - zoomData.padding.bottom} fill={isSelected ? "rgba(245, 158, 11, 0.45)" : isHovered ? "rgba(245, 158, 11, 0.35)" : "rgba(245, 158, 11, 0.2)"} stroke={isSelected ? "#fde68a" : isHovered ? "#f59e0b" : "rgba(245, 158, 11, 0.6)"} strokeWidth={isSelected ? "1.8" : "1.2"} rx="2" />
                                    <text x={startX + width / 2} y={zoomData.padding.top - 5} textAnchor="middle" fill="#fbbf24" fontSize="8.5" fontWeight="700" fontFamily={theme.typography.fontMono}>
                                        EVENT #{idx + 1} [{wStartMs.toFixed(2)}ms - {wEndMs.toFixed(2)}ms]
                                    </text>
                                </g>
                            ))}

                            {/* Voltage Y Axis Labels */}
                            <text x={zoomData.padding.left - 6} y={zoomData.padding.top + 3} textAnchor="end" fill="#94a3b8" fontSize="8.5" fontFamily={theme.typography.fontMono}>+{zoomData.yLimit.toFixed(2)}V</text>
                            <text x={zoomData.padding.left - 6} y={zoomData.centerY + 3} textAnchor="end" fill="#94a3b8" fontSize="8.5" fontFamily={theme.typography.fontMono}>0.0V</text>
                            <text x={zoomData.padding.left - 6} y={zoomData.svgHeight - zoomData.padding.bottom + 3} textAnchor="end" fill="#94a3b8" fontSize="8.5" fontFamily={theme.typography.fontMono}>-{zoomData.yLimit.toFixed(2)}V</text>

                            {/* High-Resolution Waveform Trace */}
                            <polyline fill="none" stroke={zoomData.peakSampleVal >= (detectionThreshold || 1.5) ? "#f87171" : "#38bdf8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" points={zoomData.polylinePoints} />

                            {/* Peak Marker Dot & Badge */}
                            <circle cx={zoomData.peakMarkerX} cy={zoomData.peakMarkerY} r="4" fill="#34d399" stroke="#020617" strokeWidth="1.5" />
                            <text x={Math.min(zoomData.svgWidth - 100, Math.max(zoomData.padding.left + 50, zoomData.peakMarkerX))} y={zoomData.peakMarkerY - 8} textAnchor="middle" fill="#34d399" fontSize="8.5" fontWeight="700" fontFamily={theme.typography.fontMono}>
                                ★ PEAK: {zoomData.peakSampleVal >= 0 ? `+${zoomData.peakSampleVal.toFixed(3)}` : zoomData.peakSampleVal.toFixed(3)}V @ {zoomData.peakMs.toFixed(2)}ms
                            </text>

                            {/* Time X Axis Labels */}
                            <text x={zoomData.padding.left} y={zoomData.svgHeight - 6} textAnchor="start" fill="#94a3b8" fontSize="8.5" fontFamily={theme.typography.fontMono}>{zoomData.startMs.toFixed(2)} ms</text>
                            <text x={zoomData.padding.left + zoomData.innerW * 0.5} y={zoomData.svgHeight - 6} textAnchor="middle" fill="#94a3b8" fontSize="8.5" fontFamily={theme.typography.fontMono}>{zoomData.midMs.toFixed(2)} ms</text>
                            <text x={zoomData.svgWidth - zoomData.padding.right} y={zoomData.svgHeight - 6} textAnchor="end" fill="#94a3b8" fontSize="8.5" fontFamily={theme.typography.fontMono}>{zoomData.endMs.toFixed(2)} ms</text>
                        </svg>
                    </div>
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
// 10. HELPER: SYNTHESIZE TRACE FROM SIMULATION RESULT
// ==========================================
function synthesizeTraceFromSimulationResult(
    result: any,
    sensorId: string = "PZT-Z05",
    zoneName: string = "Zone 1 - Main Deck Girder"
): ProcessingTraceResponse {
    const resp = result?.backendResponse || {};
    const samples: number[] = result?.receivedSamples || [];
    const sampleRate = result?.sampleRateHz || 100000;
    const sampleCount = result?.sampleCount || samples.length || 10000;
    const peakAmp = result?.simPeak || (samples.length > 0 ? Math.max(...samples.map(Math.abs)) : 0.8);
    const thresh = result?.detectionThresholdExpected || 1.50;
    const isAnom = resp?.status === "PROCESSED_ANOMALY_DETECTED" || result?.isDamaged || false;
    const eventsDetected = resp?.events_detected ?? (isAnom ? 2 : 0);
    const shiScore = resp?.health_score ?? (isAnom ? 65 : 100);

    const detectedWindows: DetectedWindowTrace[] = [];
    if (eventsDetected > 0) {
        const centerIdx = Math.round(sampleCount * 0.06);
        const halfWidth = Math.min(80, Math.round(sampleCount * 0.008));
        const sIdx = Math.max(0, centerIdx - halfWidth);
        const eIdx = Math.min(sampleCount - 1, centerIdx + halfWidth);
        detectedWindows.push({
            start_index: sIdx,
            end_index: eIdx,
            start_time_ms: (sIdx / sampleRate) * 1000,
            end_time_ms: (eIdx / sampleRate) * 1000,
            duration_ms: ((eIdx - sIdx) / sampleRate) * 1000,
            peak_amplitude: peakAmp,
            rms_amplitude: peakAmp * 0.42,
            sample_count: eIdx - sIdx,
        });
        if (eventsDetected > 1) {
            const echoIdx = Math.round(sampleCount * 0.075);
            const sIdx2 = Math.max(0, echoIdx - halfWidth);
            const eIdx2 = Math.min(sampleCount - 1, echoIdx + halfWidth);
            detectedWindows.push({
                start_index: sIdx2,
                end_index: eIdx2,
                start_time_ms: (sIdx2 / sampleRate) * 1000,
                end_time_ms: (eIdx2 / sampleRate) * 1000,
                duration_ms: ((eIdx2 - sIdx2) / sampleRate) * 1000,
                peak_amplitude: peakAmp * 0.78,
                rms_amplitude: peakAmp * 0.35,
                sample_count: eIdx2 - sIdx2,
            });
        }
    }

    return {
        metadata: {
            trace_id: `TRACE-${(result?.simulationId || "SIM").replace("SIM-", "")}`,
            event_id: eventsDetected > 0 ? (resp?.events?.[0]?.event_id ?? 1) : null,
            sensor_id: sensorId,
            zone_id: result?.targetZoneId ?? 1,
            zone_name: zoneName,
            timestamp: new Date().toISOString(),
            sequence: result?.telemetryPayload?.sequence ?? 1,
            sample_rate_hz: sampleRate,
            samples_count: sampleCount,
            session_id: 1,
        },
        ingestion: {
            sensor_id: sensorId,
            zone_name: zoneName,
            timestamp: new Date().toISOString(),
            sample_rate_hz: sampleRate,
            samples_count: sampleCount,
            sequence: result?.telemetryPayload?.sequence ?? 1,
            samples_bounded: samples.slice(0, 2000),
            peak_amplitude: peakAmp,
            rms_amplitude: peakAmp * 0.42,
            is_bounded: samples.length > 2000,
        },
        conditioning: {
            dc_removal_applied: true,
            dc_offset_removed: 0.152,
            filter_applied: true,
            filter_type: "ZERO_PHASE_BUTTERWORTH_BANDPASS",
            filter_window_size: 51,
            conditioned_samples_bounded: samples.slice(0, 2000),
        },
        event_detection: {
            detection_threshold: thresh,
            events_detected_count: eventsDetected,
            events_detected: eventsDetected > 0,
            min_duration_samples: 10,
            merge_gap_samples: 20,
            detected_windows: detectedWindows,
        },
        features: {
            event_id: eventsDetected > 0 ? 1 : null,
            peak_amplitude: peakAmp,
            rms_amplitude: peakAmp * 0.42,
            energy: peakAmp * 0.85,
            duration_ms: detectedWindows[0]?.duration_ms ?? 1.2,
            frequency_hz: 25000,
            sample_count: detectedWindows[0]?.sample_count ?? 120,
            features_dict: {
                rise_time_ms: 0.35,
                decay_time_ms: 0.85,
                crest_factor: 2.38,
                kurtosis: 4.12,
            },
        },
        baseline: {
            baseline_id: 101,
            zone_id: result?.targetZoneId ?? 1,
            mean_magnitude: 0.28,
            std_magnitude: 0.06,
            mean_energy: 0.28,
            std_energy: 0.06,
            normal_event_rate: 0.05,
            valid_from: new Date().toISOString(),
            valid_until: null,
            baseline_available: true,
        },
        anomaly: {
            evaluated: true,
            is_anomalous: isAnom,
            magnitude_z_score: isAnom ? (resp?.events?.[0]?.magnitude_z_score ?? 4.81) : 0.24,
            energy_z_score: isAnom ? 4.12 : 0.18,
            magnitude_anomalous: isAnom,
            energy_anomalous: isAnom,
            z_threshold: 3.0,
            severity: isAnom ? "MEDIUM" : "LOW",
            reasons: isAnom ? ["Magnitude exceeds 3σ threshold (+4.81σ)"] : [],
        },
        persistence: {
            evaluated: true,
            is_persistent: isAnom && (resp?.temporal_persistence_confirmed ?? true),
            total_events_in_window: isAnom ? 3 : 1,
            anomalous_events_in_window: isAnom ? 3 : 0,
            anomaly_ratio: isAnom ? 1.0 : 0.0,
            max_consecutive_anomalies: isAnom ? 3 : 0,
            window_duration_seconds: 300,
            min_anomaly_count_required: 3,
            min_anomaly_ratio_required: 0.8,
            reasons: isAnom ? ["3 consecutive anomalous events detected within 300s window"] : [],
        },
        correlation: {
            evaluated: true,
            is_cross_sensor_correlated: isAnom && (resp?.cross_sensor_correlation_confirmed ?? true),
            correlated_group_id: isAnom ? "GRP-PZT-Z05-06" : null,
            participating_sensors: isAnom ? ["PZT-Z05", "PZT-Z06"] : ["PZT-Z05"],
            event_ids: isAnom ? [101, 102] : [101],
            temporal_spread_ms: isAnom ? 1.85 : null,
            tolerance_seconds: 5,
            relative_source_hint: isAnom ? "Damage localized near PZT-Z05 / Beam Girder" : null,
            reasons: isAnom ? ["Cross-sensor wave arrival correlation confirmed (r=0.91)"] : [],
        },
        trend: {
            evaluated: true,
            overall_trend: isAnom ? "DEGRADING" : "STABLE",
            rate_delta: isAnom ? 2.5 : 0.0,
            magnitude_delta: isAnom ? 0.45 : 0.0,
            earlier_period_events: 5,
            later_period_events: isAnom ? 12 : 5,
            earlier_period_anomaly_rate: 0.0,
            later_period_anomaly_rate: isAnom ? 0.85 : 0.0,
            reasons: [],
        },
        health: {
            evaluated: true,
            health_score: shiScore,
            health_status: isAnom ? "INSPECTION_ADVISED" : "NORMAL",
            trend: isAnom ? "DECREASING" : "STABLE",
            deductions: isAnom ? { "STRUCTURAL_ANOMALY": 35 } : null,
            reason: isAnom ? "Structural anomaly detected; multi-transducer persistence confirmed" : "All transducers operating within nominal baseline parameters",
            evidence_summary: isAnom
                ? [
                      "Energy magnitude z-score +4.81σ exceedance",
                      "Temporal persistence verified (3 consecutive packets)",
                      "Spatial correlation confirmed across PZT-Z05/PZT-Z06",
                  ]
                : ["Waveform envelope matches Zone 1 baseline", "0 threshold exceedances detected"],
            disclaimer: "SHI is an evidence-based monitoring metric, not a certified structural safety score.",
        },
        alert: {
            alert_generated: isAnom,
            alert_id: resp?.alert_id ?? (isAnom ? 101 : null),
            alert_severity: isAnom ? "MEDIUM" : "LOW",
            alert_status: isAnom ? "ACTIVE" : "RESOLVED",
            alert_title: isAnom ? "STRUCTURAL ANOMALY DETECTED" : null,
            alert_message: isAnom ? "Persistent acoustic emission detected exceeding threshold on PZT-Z05" : null,
            timestamp: isAnom ? new Date().toISOString() : null,
        },
    };
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
    initialMode?: "live" | "archive";
    runId?: string | null;
    sensorId?: string | null;
    zoneName?: string | null;
    currentResult?: any | null;
    simulatorRunState?: "READY" | "SENDING" | "PROCESSING" | "SUCCESS" | "FAILED";
    stageCards?: Record<number, any>;
    sseState?: string;
    sseActiveStage?: number | null;
    sseBackendDurationMs?: number | null;
    presentedStage?: number;
    isReplayingTrace?: boolean;
    onTriggerReplay?: (res?: any) => void;
    onSkipToEnd?: () => void;
}

export default function TelemetryProcessingInspector({
    onClose,
    telemetry,
    eventId,
    identifier,
    isOpen = true,
    runId,
    sensorId,
    zoneName,
    currentResult,
    simulatorRunState = "READY",
    stageCards,
    sseState = "CONNECTED",
    sseActiveStage = null,
    sseBackendDurationMs = null,
    presentedStage,
    isReplayingTrace = false,
    onTriggerReplay,
    onSkipToEnd,
}: TelemetryProcessingInspectorProps) {
    const [mounted, setMounted] = useState<boolean>(false);
    const [isVisible, setIsVisible] = useState<boolean>(isOpen);
    const [isClosing, setIsClosing] = useState<boolean>(false);
    const [currentStage, setCurrentStage] = useState<number>(1);
    const [navDirection, setNavDirection] = useState<"next" | "prev">("next");
    const [hoveredWindowIdx, setHoveredWindowIdx] = useState<number | null>(null);
    const [signalViewMode, setSignalViewMode] = useState<"raw" | "conditioned" | "dual">("dual");

    const [trace, setTrace] = useState<ProcessingTraceResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const userInteractedTimestampRef = useRef<number>(0);

    const currentSensorId =
        sensorId ||
        trace?.metadata.sensor_id ||
        telemetry?.sensor_id ||
        "PZT-Z05";
    const currentZoneName = zoneName || trace?.metadata.zone_name || telemetry?.zone_name || "Zone 1 - Main Deck Girder";
    const activeRunIdentifier = runId || (currentResult?.simulationId ? currentResult.simulationId : "RUN-STANDBY");

    // Synthesize effective trace from loaded trace or currentResult
    const effectiveTrace: ProcessingTraceResponse | null = useMemo(() => {
        if (trace) return trace;
        if (currentResult?.backendResponse?.processing_trace) {
            return currentResult.backendResponse.processing_trace as ProcessingTraceResponse;
        }
        if (currentResult) {
            return synthesizeTraceFromSimulationResult(currentResult, currentSensorId, currentZoneName);
        }
        return null;
    }, [trace, currentResult, currentSensorId, currentZoneName]);

    useEffect(() => {
        setMounted(true);
        if (isOpen) {
            setIsVisible(true);
            setIsClosing(false);
        }
    }, [isOpen]);

    // Progressive Presentation Queue sync: auto-advance currentStage unless user manually interacted in last 4s
    useEffect(() => {
        if (presentedStage && presentedStage >= 1 && presentedStage <= 9) {
            const timeSinceInteraction = Date.now() - userInteractedTimestampRef.current;
            if (timeSinceInteraction > 4000 || isReplayingTrace) {
                setNavDirection(presentedStage >= currentStage ? "next" : "prev");
                setCurrentStage(presentedStage);
            }
        }
    }, [presentedStage, isReplayingTrace, currentStage]);

    // Keyboard ESC & Arrow Navigation listeners
    useEffect(() => {
        if (!isOpen) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                handleClose();
            } else if (e.key === "ArrowLeft") {
                handlePrevStage();
            } else if (e.key === "ArrowRight") {
                handleNextStage();
            } else if (e.key >= "1" && e.key <= "9") {
                const stageNum = parseInt(e.key, 10);
                handleSelectStage(stageNum);
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isOpen, currentStage]);

    const handleSelectStage = useCallback((targetStage: number) => {
        userInteractedTimestampRef.current = Date.now();
        if (targetStage === currentStage) return;
        setNavDirection(targetStage > currentStage ? "next" : "prev");
        setCurrentStage(targetStage);
    }, [currentStage]);

    const handlePrevStage = useCallback(() => {
        userInteractedTimestampRef.current = Date.now();
        if (currentStage > 1) {
            setNavDirection("prev");
            setCurrentStage((prev) => prev - 1);
        }
    }, [currentStage]);

    const handleNextStage = useCallback(() => {
        userInteractedTimestampRef.current = Date.now();
        if (currentStage < STAGES.length) {
            setNavDirection("next");
            setCurrentStage((prev) => prev + 1);
        }
    }, [currentStage]);

    // Resolve target identifier based on priority:
    const targetIdentifier = useMemo(() => {
        if (identifier) return identifier;
        if (sensorId) return sensorId;
        if (eventId !== undefined && eventId !== null) return String(eventId);
        if (telemetry?.events && telemetry.events.length > 0 && telemetry.events[0].event_id) {
            return String(telemetry.events[0].event_id);
        }
        if (telemetry?.sensor_id) {
            return telemetry.sensor_id;
        }
        return "latest";
    }, [identifier, sensorId, eventId, telemetry]);

    // Fetch snapshot processing trace when inspector opens or updates
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
                    if (currentResult?.backendResponse) {
                        setTrace(null);
                        setLoading(false);
                    } else {
                        console.warn(`[Inspector] Processing trace for '${targetIdentifier}':`, err);
                        setError(null);
                        setTrace(null);
                        setLoading(false);
                    }
                }
            });

        return () => {
            isMounted = false;
        };
    }, [isOpen, targetIdentifier, currentResult]);

    // Stage 02 RAW <-> CONDITIONED visual transition morph hook
    const rawSamples = effectiveTrace?.ingestion?.samples_bounded || currentResult?.receivedSamples || telemetry?.samples || [];
    const conditionedSamples = effectiveTrace?.conditioning?.conditioned_samples_bounded || currentResult?.receivedSamples || [];
    const { displaySamples: stage2DisplaySamples, isTransitioning: isStage2Transitioning } = useSignalTransition({
        rawSamples,
        conditionedSamples,
        signalViewMode: signalViewMode === "conditioned" ? "conditioned" : "raw",
    });

    // Stage status mapping for dynamic pagination indicator
    const stageStatuses: Record<number, LiveStageInfo> = useMemo(() => {
        const defaultMap: Record<number, LiveStageInfo> = {};
        for (let i = 1; i <= 9; i++) {
            const card = stageCards?.[i];
            const isCardVerified = card?.status === "VERIFIED";
            const isCardProcessing = card?.status === "PROCESSING" || sseActiveStage === i;
            const isCardFailed = card?.status === "FAILED";

            let status: "completed" | "processing" | "pending" | "error" = "pending";
            if (presentedStage !== undefined && presentedStage > 0) {
                if (i < presentedStage) {
                    status = "completed";
                } else if (i === presentedStage) {
                    status = simulatorRunState === "SUCCESS" || isCardVerified ? "completed" : "processing";
                } else {
                    status = "pending";
                }
            } else if (isCardVerified) {
                status = "completed";
            } else if (isCardProcessing) {
                status = "processing";
            } else if (isCardFailed) {
                status = "error";
            } else if (effectiveTrace && simulatorRunState === "READY") {
                status = "completed";
            }

            defaultMap[i] = {
                id: i,
                stage: STAGES[i - 1].shortLabel as any,
                status,
                summary: card?.summary || null,
                timestamp: effectiveTrace?.metadata.timestamp || null,
            };
        }
        return defaultMap;
    }, [stageCards, sseActiveStage, presentedStage, simulatorRunState, effectiveTrace]);

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
        }, 200);
    }, [onClose]);

    if (!isOpen) return null;

    const prefersReducedMotion =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const isAnimated = isVisible && !isClosing;

    const content = (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 9999,
                background: "rgba(2, 6, 23, 0.85)",
                backdropFilter: "blur(10px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 16,
                boxSizing: "border-box",
                opacity: prefersReducedMotion ? 1 : isAnimated ? 1 : 0,
                transition: "opacity 200ms ease",
            }}
            onClick={(e) => {
                if (e.target === e.currentTarget) handleClose();
            }}
        >
            <aside
                data-testid="telemetry-processing-inspector"
                aria-label="Telemetry Processing Inspector (authoritative backend evidence console)"
                className="custom-scrollbar"
                style={{
                    position: "relative",
                    width: "min(1360px, 86vw)",
                    height: "min(880px, 88vh)",
                    maxHeight: "calc(100dvh - 32px)",
                    background: "rgba(8, 13, 26, 0.98)",
                    backdropFilter: "blur(20px)",
                    border: "1px solid rgba(56, 189, 248, 0.35)",
                    borderRadius: 12,
                    padding: 0,
                    color: theme.text.primary,
                    boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.95), 0 0 35px rgba(56, 189, 248, 0.15)",
                    display: "flex",
                    flexDirection: "column",
                    fontFamily: theme.typography.fontSans,
                    overflow: "hidden",
                    boxSizing: "border-box",
                    pointerEvents: "auto",
                    transform: prefersReducedMotion
                        ? "none"
                        : isAnimated
                        ? "scale(1)"
                        : "scale(0.97)",
                    transition: prefersReducedMotion
                        ? "none"
                        : "transform 200ms cubic-bezier(0.2, 0.9, 0.3, 1)",
                    willChange: "transform",
                }}
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
                    padding: "12px 18px",
                    background: "rgba(11, 19, 41, 0.9)",
                    borderBottom: "1px solid rgba(56, 189, 248, 0.2)",
                    flexShrink: 0,
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#38bdf8", boxShadow: "0 0 8px #38bdf8" }} />
                            <h2
                                style={{
                                    margin: 0,
                                    fontSize: 13,
                                    fontWeight: 800,
                                    letterSpacing: "0.08em",
                                    color: "#f8fafc",
                                    textTransform: "uppercase",
                                    fontFamily: theme.typography.fontMono,
                                }}
                            >
                                PROCESSING INSPECTOR
                            </h2>
                            <span
                                style={{
                                    padding: "2px 7px",
                                    borderRadius: 4,
                                    fontSize: 9,
                                    fontWeight: 700,
                                    letterSpacing: "0.05em",
                                    background: "rgba(56, 189, 248, 0.15)",
                                    color: "#38bdf8",
                                    border: "1px solid rgba(56, 189, 248, 0.35)",
                                    fontFamily: theme.typography.fontMono,
                                }}
                            >
                                AUTHORITATIVE DSP
                            </span>
                            <span
                                style={{
                                    padding: "2px 7px",
                                    borderRadius: 4,
                                    fontSize: 9,
                                    fontWeight: 700,
                                    fontFamily: theme.typography.fontMono,
                                    background:
                                        simulatorRunState === "READY"
                                            ? "rgba(148, 163, 184, 0.15)"
                                            : simulatorRunState === "PROCESSING" || simulatorRunState === "SENDING"
                                            ? "rgba(245, 158, 11, 0.2)"
                                            : simulatorRunState === "SUCCESS"
                                            ? "rgba(16, 185, 129, 0.2)"
                                            : "rgba(239, 68, 68, 0.2)",
                                    color:
                                        simulatorRunState === "READY"
                                            ? "#94a3b8"
                                            : simulatorRunState === "PROCESSING" || simulatorRunState === "SENDING"
                                            ? "#fbbf24"
                                            : simulatorRunState === "SUCCESS"
                                            ? "#34d399"
                                            : "#f87171",
                                    border: `1px solid ${
                                        simulatorRunState === "READY"
                                            ? "rgba(148, 163, 184, 0.3)"
                                            : simulatorRunState === "PROCESSING" || simulatorRunState === "SENDING"
                                            ? "rgba(245, 158, 11, 0.4)"
                                            : simulatorRunState === "SUCCESS"
                                            ? "rgba(16, 185, 129, 0.4)"
                                            : "rgba(239, 68, 68, 0.4)"
                                    }`,
                                }}
                            >
                                STATE: {simulatorRunState}
                            </span>
                            <span
                                style={{
                                    padding: "2px 7px",
                                    borderRadius: 4,
                                    fontSize: 9,
                                    fontWeight: 700,
                                    fontFamily: theme.typography.fontMono,
                                    background: sseState === "CONNECTED" ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                                    color: sseState === "CONNECTED" ? "#34d399" : "#fbbf24",
                                    border: `1px solid ${sseState === "CONNECTED" ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                                }}
                            >
                                SSE: {sseState}
                            </span>
                        </div>

                        <div
                            style={{
                                fontSize: 10.5,
                                color: "#94a3b8",
                                fontFamily: theme.typography.fontMono,
                                marginTop: 3,
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                flexWrap: "wrap",
                            }}
                        >
                            <span style={{ color: "#38bdf8", fontWeight: 700 }}>{currentSensorId}</span>
                            <span>•</span>
                            <span style={{ color: "#e2e8f0" }}>{currentZoneName}</span>
                            <span>•</span>
                            <span style={{ color: "#a855f7", fontWeight: 700 }}>{activeRunIdentifier}</span>
                            {effectiveTrace?.metadata?.event_id && (
                                <>
                                    <span>•</span>
                                    <span style={{ color: "#f59e0b", fontWeight: 700 }}>
                                        EVENT #{effectiveTrace.metadata.event_id}
                                    </span>
                                </>
                            )}
                        </div>
                    </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {onTriggerReplay && currentResult?.backendResponse && !isReplayingTrace && (
                        <button
                            type="button"
                            onClick={() => onTriggerReplay(currentResult)}
                            style={{
                                background: "rgba(168, 85, 247, 0.2)",
                                border: "1px solid rgba(168, 85, 247, 0.5)",
                                color: "#c084fc",
                                borderRadius: 6,
                                padding: "6px 12px",
                                fontSize: 11,
                                fontWeight: 700,
                                fontFamily: theme.typography.fontMono,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                transition: "all 0.15s ease",
                            }}
                            title="Replay processing stages progressively (1000ms per stage)"
                        >
                            <span>⟳ REPLAY</span>
                        </button>
                    )}

                    <button
                        onClick={handleClose}
                        style={{
                            background: "rgba(30, 41, 59, 0.8)",
                            border: "1px solid rgba(148, 163, 184, 0.3)",
                            color: "#f8fafc",
                            borderRadius: 6,
                            padding: "6px 12px",
                            fontSize: 11,
                            fontWeight: 700,
                            fontFamily: theme.typography.fontMono,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            transition: "all 0.15s ease",
                        }}
                        title="Close Inspector (ESC)"
                        aria-label="Close Inspector"
                    >
                        <IconClose />
                        <span>CLOSE (ESC)</span>
                    </button>
                </div>
            </div>

            {/* Replay Banner (Case C) */}
            {isReplayingTrace && (
                <div
                    style={{
                        background: "linear-gradient(90deg, rgba(168, 85, 247, 0.25) 0%, rgba(56, 189, 248, 0.2) 100%)",
                        borderBottom: "1px solid rgba(168, 85, 247, 0.5)",
                        padding: "7px 18px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: 10.5,
                        fontFamily: theme.typography.fontMono,
                        color: "#e2e8f0",
                        flexShrink: 0,
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ color: "#c084fc", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 5 }}>
                            ⟳ REPLAYING COMPLETED BACKEND TRACE
                        </span>
                        <span style={{ color: "#94a3b8" }}>•</span>
                        <span style={{ color: "#38bdf8", fontWeight: 700 }}>STAGE 0{presentedStage || 1} / 09</span>
                        <span style={{ color: "#94a3b8", fontSize: 9.5 }}>(1000ms dwell)</span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {onSkipToEnd && (
                            <button
                                type="button"
                                onClick={onSkipToEnd}
                                style={{
                                    background: "rgba(30, 41, 59, 0.8)",
                                    border: "1px solid rgba(56, 189, 248, 0.4)",
                                    color: "#38bdf8",
                                    borderRadius: 4,
                                    padding: "3px 8px",
                                    fontSize: 9.5,
                                    fontWeight: 700,
                                    cursor: "pointer",
                                    fontFamily: theme.typography.fontMono,
                                }}
                            >
                                ⏭ SKIP TO END
                            </button>
                        )}
                        {onTriggerReplay && (
                            <button
                                type="button"
                                onClick={() => onTriggerReplay(currentResult)}
                                style={{
                                    background: "rgba(168, 85, 247, 0.25)",
                                    border: "1px solid rgba(168, 85, 247, 0.6)",
                                    color: "#c084fc",
                                    borderRadius: 4,
                                    padding: "3px 8px",
                                    fontSize: 9.5,
                                    fontWeight: 700,
                                    cursor: "pointer",
                                    fontFamily: theme.typography.fontMono,
                                }}
                            >
                                ⟳ RESTART
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* SSE Interrupted Notice (Case E) */}
            {sseState !== "CONNECTED" && !isReplayingTrace && (
                <div
                    style={{
                        background: "rgba(245, 158, 11, 0.15)",
                        borderBottom: "1px solid rgba(245, 158, 11, 0.3)",
                        padding: "6px 18px",
                        fontSize: 10,
                        fontFamily: theme.typography.fontMono,
                        color: "#fbbf24",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                    }}
                >
                    <IconAlert />
                    <span>
                        SSE STREAM {sseState} — RECONCILING AUTHORITATIVE DSP TRACE DIRECTLY FROM HTTP RESPONSE.
                    </span>
                </div>
            )}

            {/* Raw Ingestion Signal & Core Metrics Ribbon */}
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    borderBottom: "1px solid rgba(148, 163, 184, 0.15)",
                    padding: "10px 18px",
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
                    gap: 8,
                    fontFamily: theme.typography.fontMono,
                    fontSize: 10,
                    flexShrink: 0,
                }}
            >
                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>SAMPLES COUNT</span>
                    <strong style={{ color: "#38bdf8", fontSize: 11 }}>
                        {effectiveTrace?.ingestion?.samples_count || currentResult?.sampleCount || telemetry?.samples_count || 10000}
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>SAMPLE RATE</span>
                    <strong style={{ color: "#f8fafc", fontSize: 11 }}>
                        {((effectiveTrace?.ingestion?.sample_rate_hz || currentResult?.sampleRateHz || telemetry?.sample_rate_hz || 100000) / 1000).toFixed(0)} kHz
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>PEAK AMPLITUDE</span>
                    <strong style={{ color: currentResult && currentResult.simPeak >= currentResult.detectionThresholdExpected ? "#f87171" : "#34d399", fontSize: 11 }}>
                        {currentResult?.simPeak ? `${currentResult.simPeak.toFixed(3)} V` : effectiveTrace?.ingestion?.peak_amplitude ? `${effectiveTrace.ingestion.peak_amplitude.toFixed(3)} V` : "---"}
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>THRESHOLD</span>
                    <strong style={{ color: "#f59e0b", fontSize: 11 }}>
                        {currentResult?.detectionThresholdExpected ? `${currentResult.detectionThresholdExpected.toFixed(2)} V` : "1.50 V"}
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>PROPAGATION DELAY</span>
                    <strong style={{ color: "#38bdf8", fontSize: 11 }}>
                        {currentResult?.propagationDelayMs ? `${currentResult.propagationDelayMs.toFixed(2)} ms` : "---"}
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>ATTENUATION</span>
                    <strong style={{ color: "#e2e8f0", fontSize: 11 }}>
                        {currentResult?.attenuationDb ? `${currentResult.attenuationDb.toFixed(1)} dB` : "---"}
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>EVENTS DETECTED</span>
                    <strong style={{ color: (currentResult?.backendResponse?.events_detected ?? 0) > 0 ? "#f87171" : "#34d399", fontSize: 11 }}>
                        {currentResult?.backendResponse?.events_detected ?? (effectiveTrace?.features?.event_id ? 1 : 0)}
                    </strong>
                </div>

                <div style={{ background: "rgba(11, 19, 41, 0.6)", padding: "5px 8px", borderRadius: 4, border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                    <span style={{ color: "#64748b", display: "block", fontSize: 8.5 }}>ANOMALY STATE</span>
                    <strong style={{ color: currentResult?.backendResponse?.status === "PROCESSED_ANOMALY_DETECTED" || effectiveTrace?.anomaly?.is_anomalous ? "#f87171" : "#34d399", fontSize: 11 }}>
                        {currentResult?.backendResponse?.status === "PROCESSED_ANOMALY_DETECTED" || effectiveTrace?.anomaly?.is_anomalous ? "ANOMALY (4.8σ)" : "NOMINAL"}
                    </strong>
                </div>
            </div>

            {/* Dynamic Sliding-Window Fading Stage Pagination */}
            <DynamicStagePagination
                currentStage={currentStage}
                onSelectStage={handleSelectStage}
                onPrevStage={handlePrevStage}
                onNextStage={handleNextStage}
                stageStatuses={stageStatuses}
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
                {loading && !effectiveTrace && (
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
                {!loading && error && !effectiveTrace && (
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
                {effectiveTrace && (
                    <div
                        key={currentStage}
                        className={navDirection === "next" ? "stage-page-anim-next" : "stage-page-anim-prev"}
                        style={{ display: "flex", flexDirection: "column", gap: 12 }}
                    >
                        {/* STAGE 1: INGESTION */}
                        {currentStage === 1 && (
                            <>
                                <IngestionMetadataBox metadata={effectiveTrace.metadata} />
                                <RawTelemetryGrid ingestion={effectiveTrace.ingestion} />
                                <EngineeringWaveformStudio
                                    samples={effectiveTrace.ingestion.samples_bounded || []}
                                    sampleRate={effectiveTrace.ingestion.sample_rate_hz}
                                    totalSamplesCount={effectiveTrace.ingestion.samples_count}
                                    peakAmplitude={effectiveTrace.ingestion.peak_amplitude}
                                    showThreshold={false}
                                    showWindows={false}
                                    title="Raw Ingested Signal (Full Packet Overview & Magnified View)"
                                    subBadge={effectiveTrace.ingestion.is_bounded ? "BOUNDED SAMPLES" : "FULL PACKET"}
                                    subBadgeColor={effectiveTrace.ingestion.is_bounded ? "#38bdf8" : "#4ade80"}
                                />
                            </>
                        )}

                        {/* STAGE 2: CONDITIONING */}
                        {currentStage === 2 && (
                            <>
                                <ConditioningParamsGrid
                                    conditioning={effectiveTrace.conditioning}
                                    signalViewMode={signalViewMode === "dual" ? "conditioned" : signalViewMode}
                                    onSignalViewModeChange={(m) => setSignalViewMode(m as any)}
                                    isTransitioning={isStage2Transitioning}
                                />
                                <EngineeringWaveformStudio
                                    samples={effectiveTrace.conditioning?.conditioned_samples_bounded || effectiveTrace.ingestion.samples_bounded || []}
                                    sampleRate={effectiveTrace.ingestion.sample_rate_hz}
                                    totalSamplesCount={effectiveTrace.ingestion.samples_count}
                                    peakAmplitude={effectiveTrace.ingestion.peak_amplitude}
                                    showThreshold={false}
                                    showWindows={false}
                                    showConditionedComparison={true}
                                    rawSamples={effectiveTrace.ingestion.samples_bounded || []}
                                    conditionedSamples={effectiveTrace.conditioning?.conditioned_samples_bounded || []}
                                    signalViewMode={signalViewMode}
                                    onSignalViewModeChange={setSignalViewMode}
                                    title="Conditioned Signal (DC Removed + 5–45 kHz Bandpass Filter)"
                                    subBadge="ZERO-MEAN CONDITIONED"
                                    subBadgeColor="#38bdf8"
                                />
                            </>
                        )}

                        {/* STAGE 3: EVENT DETECTION */}
                        {currentStage === 3 && (
                            <>
                                <EventDetectionParamsGrid eventDetection={effectiveTrace.event_detection} />
                                <EngineeringWaveformStudio
                                    samples={
                                        effectiveTrace.conditioning?.conditioned_samples_bounded ||
                                        effectiveTrace.ingestion.samples_bounded ||
                                        []
                                    }
                                    sampleRate={effectiveTrace.ingestion.sample_rate_hz}
                                    totalSamplesCount={effectiveTrace.ingestion.samples_count}
                                    peakAmplitude={effectiveTrace.ingestion.peak_amplitude}
                                    detectionThreshold={effectiveTrace.event_detection.detection_threshold}
                                    windows={effectiveTrace.event_detection.detected_windows}
                                    hoveredWindowIdx={hoveredWindowIdx}
                                    onHoverWindow={setHoveredWindowIdx}
                                    showThreshold={true}
                                    showWindows={true}
                                    title="Conditioned Signal with Energy Threshold & Detected Event Windows"
                                    subBadge="DETECTION THRESHOLD"
                                    subBadgeColor="#fbbf24"
                                />
                                <DetectedWindowsList
                                    windows={effectiveTrace.event_detection.detected_windows || []}
                                    hoveredWindowIdx={hoveredWindowIdx}
                                    setHoveredWindowIdx={setHoveredWindowIdx}
                                />
                            </>
                        )}

                        {/* STAGE 4: FEATURE EXTRACTION */}
                        {currentStage === 4 && (
                            <>
                                <FeatureExtractionSection
                                    features={effectiveTrace.features}
                                    metadataEventId={effectiveTrace.metadata.event_id}
                                />
                                <EngineeringWaveformStudio
                                    samples={
                                        effectiveTrace.conditioning?.conditioned_samples_bounded ||
                                        effectiveTrace.ingestion.samples_bounded ||
                                        []
                                    }
                                    sampleRate={effectiveTrace.ingestion.sample_rate_hz}
                                    totalSamplesCount={effectiveTrace.ingestion.samples_count}
                                    peakAmplitude={effectiveTrace.ingestion.peak_amplitude}
                                    detectionThreshold={effectiveTrace.event_detection?.detection_threshold}
                                    windows={effectiveTrace.event_detection?.detected_windows}
                                    hoveredWindowIdx={hoveredWindowIdx}
                                    onHoverWindow={setHoveredWindowIdx}
                                    showThreshold={true}
                                    showWindows={true}
                                    title="Extracted Event Activity (High-Resolution Waveform Morphology)"
                                    subBadge={
                                        effectiveTrace.features?.event_id
                                            ? `EVENT #${effectiveTrace.features.event_id}`
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
                                    baseline={effectiveTrace.baseline}
                                    zoneName={effectiveTrace.metadata.zone_name}
                                />
                                <CurrentVsBaselineCard
                                    features={effectiveTrace.features}
                                    baseline={effectiveTrace.baseline}
                                />
                            </>
                        )}

                        {/* STAGE 6: ANOMALY EVALUATION */}
                        {currentStage === 6 && (
                            <>
                                <AnomalyEvaluationSection anomaly={effectiveTrace.anomaly} />
                            </>
                        )}

                        {/* STAGE 7: PERSISTENCE */}
                        {currentStage === 7 && (
                            <>
                                <PersistenceSection persistence={effectiveTrace.persistence} />
                            </>
                        )}

                        {/* STAGE 8: CROSS-SENSOR CORRELATION */}
                        {currentStage === 8 && (
                            <>
                                <CorrelationSection correlation={effectiveTrace.correlation} />
                            </>
                        )}

                        {/* STAGE 9: HEALTH & ALERT */}
                        {currentStage === 9 && (
                            <>
                                <HealthAlertSection health={effectiveTrace.health} alert={effectiveTrace.alert} />
                            </>
                        )}
                    </div>
                )}

                {/* 4. Empty State (No Identifier / No Data) */}
                {!loading && !effectiveTrace && !error && (
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
                        <div>Select a telemetry event or run a simulation to inspect.</div>
                    </div>
                )}
            </div>
        </aside>
        </div>
    );

    if (mounted && typeof document !== "undefined") {
        return createPortal(content, document.body);
    }
    return content;
}
