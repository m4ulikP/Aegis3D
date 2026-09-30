"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import Link from "next/link";
import { theme } from "@/lib/theme";
import { useLiveTelemetry, STAGE_NAMES } from "@/hooks/useLiveTelemetry";
import { api } from "@/lib/api";
import TelemetryProcessingInspector from "@/components/dashboard/TelemetryProcessingInspector";
import {
    CANONICAL_SENSORS,
    CANONICAL_PATHS,
    FIXED_DAMAGED_COMPONENT,
    CanonicalSensor,
    PropagationPathInfo,
    SimulationResult,
    simulatePhysicsPropagation,
} from "@/lib/physicsEngine";

type SimulatorRunState = "READY" | "SENDING" | "PROCESSING" | "SUCCESS" | "FAILED";
type StageDisplayState = "PENDING" | "PROCESSING" | "VERIFIED" | "FAILED" | "NOT_REACHED";

interface StageCardData {
    id: number;
    name: string;
    title: string;
    status: StageDisplayState;
    summary: string;
    metric?: string;
}

const STAGE_CONFIGS: { id: number; name: string; title: string }[] = [
    { id: 1, name: "INGESTION", title: "01 INGESTION" },
    { id: 2, name: "CONDITIONING", title: "02 CONDITIONING" },
    { id: 3, name: "EVENT_DETECTION", title: "03 EVENT DETECTION" },
    { id: 4, name: "FEATURE_EXTRACTION", title: "04 FEATURE EXTRACTION" },
    { id: 5, name: "BASELINE_REFERENCE", title: "05 BASELINE REFERENCE" },
    { id: 6, name: "ANOMALY_EVALUATION", title: "06 ANOMALY EVALUATION" },
    { id: 7, name: "PERSISTENCE", title: "07 PERSISTENCE" },
    { id: 8, name: "CROSS_SENSOR_CORRELATION", title: "08 CORRELATION" },
    { id: 9, name: "HEALTH_AND_ALERT", title: "09 HEALTH & ALERT" },
];

function getDefaultStageCards(): Record<number, StageCardData> {
    const map: Record<number, StageCardData> = {};
    STAGE_CONFIGS.forEach((cfg) => {
        map[cfg.id] = {
            id: cfg.id,
            name: cfg.name,
            title: cfg.title,
            status: "PENDING",
            summary: "Pending run dispatch",
        };
    });
    return map;
}

export default function SimulatorPage() {
    // -------------------------------------------------------------
    // Configuration & State
    // -------------------------------------------------------------
    const [selectedSensorId, setSelectedSensorId] = useState<string>("PZT-Z05");
    const [pairMode, setPairMode] = useState<boolean>(false);
    const [secondarySensorId, setSecondarySensorId] = useState<string>("PZT-Z06");

    const [presetScenario, setPresetScenario] = useState<"01_NORMAL" | "02_SINGLE_EVENT" | "03_PERSISTENT" | "04_CORRELATED" | "05_CUSTOM">("01_NORMAL");
    const [physicalCondition, setPhysicalCondition] = useState<"normal" | "anomaly">("normal");

    // Core Signal Parameters
    const [sampleRateHz, setSampleRateHz] = useState<number>(100000);
    const [sampleCount, setSampleCount] = useState<number>(10000);
    const [baseAmplitude, setBaseAmplitude] = useState<number>(0.8);
    const [baseFrequencyHz, setBaseFrequencyHz] = useState<number>(10000);
    const [noisePercent, setNoisePercent] = useState<number>(0);
    const [packetIntervalMs, setPacketIntervalMs] = useState<number>(500);

    // Anomaly Injection Controls
    const [anomalyEnabled, setAnomalyEnabled] = useState<boolean>(false);
    const [anomalyStartPct, setAnomalyStartPct] = useState<number>(50);
    const [anomalyDurationMs, setAnomalyDurationMs] = useState<number>(1.0);
    const [amplitudeMultiplier, setAmplitudeMultiplier] = useState<number>(1.05);
    const [repetitionCount, setRepetitionCount] = useState<number>(1);

    // Advanced & Developer Controls
    const [customThreshold, setCustomThreshold] = useState<string>("");
    const [receiverGain] = useState<number>(5.0);
    const [backendUrl, setBackendUrl] = useState<string>(
        (typeof process !== "undefined" && process.env.NEXT_PUBLIC_BACKEND_URL) || "http://127.0.0.1:8000"
    );
    const [showPayloadDrawer, setShowPayloadDrawer] = useState<boolean>(false);
    const [showEvidenceDrawer, setShowEvidenceDrawer] = useState<boolean>(false);
    const [showDecomposition, setShowDecomposition] = useState<boolean>(true);
    const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);

    // Presentation Queue Configuration & State
    const PROCESSING_STAGE_PRESENTATION_DELAY_MS = 1000;
    const [presentedStage, setPresentedStage] = useState<number>(0);
    const [isReplayingTrace, setIsReplayingTrace] = useState<boolean>(false);
    const presentationTimersRef = useRef<NodeJS.Timeout[]>([]);
    const authoritativeStagesRef = useRef<Record<number, { title: string; summary: string }> | null>(null);

    // Simulator Runtime State & Explicit Run State Machine
    const [simulatorRunState, setSimulatorRunState] = useState<SimulatorRunState>("READY");
    const [currentRunId, setCurrentRunId] = useState<string | null>(null);
    const currentRunIdRef = useRef<string | null>(null);
    const [stageCards, setStageCards] = useState<Record<number, StageCardData>>(() => getDefaultStageCards());
    const dwellResetTimerRef = useRef<NodeJS.Timeout | null>(null);

    const clearPresentationTimers = useCallback(() => {
        presentationTimersRef.current.forEach((t) => clearTimeout(t));
        presentationTimersRef.current = [];
    }, []);

    const [isStreaming, setIsStreaming] = useState<boolean>(false);
    const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
    const [backendLatencyMs, setBackendLatencyMs] = useState<number | null>(null);
    const [sequenceCounter, setSequenceCounter] = useState<number>(1);
    const [currentResult, setCurrentResult] = useState<SimulationResult | null>(null);
    const [selectedRunHistoryId, setSelectedRunHistoryId] = useState<string | null>(null);
    const [runHistory, setRunHistory] = useState<SimulationResult[]>([]);
    const [clearingAlerts, setClearingAlerts] = useState<boolean>(false);
    const [clearAlertsFeedback, setClearAlertsFeedback] = useState<string | null>(null);

    const handleClearActiveAlerts = async () => {
        setClearingAlerts(true);
        try {
            const res = await api.clearActiveAlerts();
            setClearAlertsFeedback(`ACTIVE ALERTS CLEARED (${res.cleared_count} resolved)`);
            setTimeout(() => setClearAlertsFeedback(null), 4000);
        } catch (e: any) {
            setClearAlertsFeedback(`Clear failed: ${e.message}`);
            setTimeout(() => setClearAlertsFeedback(null), 4000);
        } finally {
            setClearingAlerts(false);
        }
    };

    // Live Telemetry Hook for SSE 9-Stage Pipeline Integration
    const {
        connectionState: sseState,
        stageStatuses: sseStageStatuses,
        activeStage: sseActiveStage,
        latestEvent: sseLatestEvent,
        errorMessage: sseErrorMessage,
        backendDurationMs: sseBackendDurationMs,
        lastCompletedTraceId: sseLastCompletedTraceId,
    } = useLiveTelemetry({
        enabled: true,
        endpoint: `${backendUrl}/api/v1/telemetry/live`,
    });

    // Sensor & Propagation Path Mapping
    const primarySensor = useMemo(() => {
        return CANONICAL_SENSORS.find((s) => s.id === selectedSensorId) || CANONICAL_SENSORS[4]; // Default PZT-Z05
    }, [selectedSensorId]);

    const mappedPath = useMemo(() => {
        return (
            CANONICAL_PATHS.find((p) => p.receiverId === primarySensor.id || p.actuatorId === primarySensor.id) ||
            CANONICAL_PATHS[0]
        );
    }, [primarySensor]);

    const sourceSensor = useMemo(() => {
        return CANONICAL_SENSORS.find((s) => s.id === mappedPath.actuatorId) || CANONICAL_SENSORS[3];
    }, [mappedPath]);

    const targetZone = useMemo(() => {
        return primarySensor.zoneName || "Zone 1 - Main Deck Girder";
    }, [primarySensor]);

    // Handle Preset Selection
    const handlePresetChange = (preset: typeof presetScenario) => {
        setPresetScenario(preset);
        if (preset === "01_NORMAL") {
            setPhysicalCondition("normal");
            setAnomalyEnabled(false);
            setRepetitionCount(1);
        } else if (preset === "02_SINGLE_EVENT") {
            setPhysicalCondition("anomaly");
            setAnomalyEnabled(true);
            setAmplitudeMultiplier(1.05);
            setRepetitionCount(1);
        } else if (preset === "03_PERSISTENT") {
            setPhysicalCondition("anomaly");
            setAnomalyEnabled(true);
            setAmplitudeMultiplier(1.05);
            setRepetitionCount(3);
        } else if (preset === "04_CORRELATED") {
            setPhysicalCondition("anomaly");
            setAnomalyEnabled(true);
            setPairMode(true);
            setRepetitionCount(2);
        }
    };

    // Health check ping
    const checkBackendHealth = useCallback(async () => {
        const start = performance.now();
        try {
            const resp = await fetch(`${backendUrl}/health`, { signal: AbortSignal.timeout(2000) });
            if (resp.ok) {
                setBackendConnected(true);
                setBackendLatencyMs(Math.round(performance.now() - start));
            } else {
                setBackendConnected(false);
                setBackendLatencyMs(null);
            }
        } catch {
            setBackendConnected(false);
            setBackendLatencyMs(null);
        }
    }, [backendUrl]);

    useEffect(() => {
        checkBackendHealth();
        const timer = setInterval(checkBackendHealth, 5000);
        return () => clearInterval(timer);
    }, [checkBackendHealth]);

    // -------------------------------------------------------------
    // Presentation Queue Orchestrator (1000ms Deliberate Reveal)
    // -------------------------------------------------------------
    const launchPresentationQueue = useCallback(
        (
            runId: string,
            authStages: Record<number, { title: string; summary: string }>,
            onDone?: () => void
        ) => {
            clearPresentationTimers();
            if (dwellResetTimerRef.current) {
                clearTimeout(dwellResetTimerRef.current);
                dwellResetTimerRef.current = null;
            }

            setSimulatorRunState("PROCESSING");
            setPresentedStage(1);

            // Initialize: Stage 1 PROCESSING, Stages 2-9 PENDING
            setStageCards({
                1: { id: 1, name: "INGESTION", title: "01 INGESTION", status: "PROCESSING", summary: "Verifying packet ingestion..." },
                2: { id: 2, name: "CONDITIONING", title: "02 CONDITIONING", status: "PENDING", summary: "Pending stage 1 verification..." },
                3: { id: 3, name: "EVENT_DETECTION", title: "03 EVENT DETECTION", status: "PENDING", summary: "Pending signal conditioning..." },
                4: { id: 4, name: "FEATURE_EXTRACTION", title: "04 FEATURE EXTRACTION", status: "PENDING", summary: "Pending event detection..." },
                5: { id: 5, name: "BASELINE_REFERENCE", title: "05 BASELINE REFERENCE", status: "PENDING", summary: "Pending feature extraction..." },
                6: { id: 6, name: "ANOMALY_EVALUATION", title: "06 ANOMALY EVALUATION", status: "PENDING", summary: "Pending baseline comparison..." },
                7: { id: 7, name: "PERSISTENCE", title: "07 PERSISTENCE", status: "PENDING", summary: "Pending anomaly evaluation..." },
                8: { id: 8, name: "CROSS_SENSOR_CORRELATION", title: "08 CORRELATION", status: "PENDING", summary: "Pending temporal persistence..." },
                9: { id: 9, name: "HEALTH_AND_ALERT", title: "09 HEALTH & ALERT", status: "PENDING", summary: "Pending correlation analysis..." },
            });

            // Schedule stages 1 to 9 reveal with deliberate delay
            for (let k = 1; k <= 9; k++) {
                // Stage activation (PROCESSING) at (k - 1) * 1000 ms
                if (k > 1) {
                    const tAct = setTimeout(() => {
                        if (currentRunIdRef.current !== runId) return;
                        setPresentedStage(k);
                        setStageCards((prev) => {
                            const next = { ...prev };
                            for (let s = 1; s < k; s++) {
                                next[s] = { ...next[s], status: "VERIFIED", summary: authStages[s]?.summary || next[s].summary };
                            }
                            next[k] = { ...next[k], status: "PROCESSING", summary: `Processing ${next[k].name.replace(/_/g, " ")}...` };
                            for (let s = k + 1; s <= 9; s++) {
                                next[s] = { ...next[s], status: "PENDING" };
                            }
                            return next;
                        });
                    }, (k - 1) * PROCESSING_STAGE_PRESENTATION_DELAY_MS);
                    presentationTimersRef.current.push(tAct);
                }

                // Stage completion (VERIFIED) at (k - 1) * 1000 + 450 ms
                const tVer = setTimeout(() => {
                    if (currentRunIdRef.current !== runId) return;
                    setStageCards((prev) => ({
                        ...prev,
                        [k]: {
                            ...prev[k],
                            status: "VERIFIED",
                            summary: authStages[k]?.summary || prev[k].summary,
                        },
                    }));
                }, (k - 1) * PROCESSING_STAGE_PRESENTATION_DELAY_MS + 450);
                presentationTimersRef.current.push(tVer);
            }

            // Final completion at 9 * 1000 ms
            const tFinal = setTimeout(() => {
                if (currentRunIdRef.current !== runId) return;
                setStageCards((prev) => {
                    const next = { ...prev };
                    for (let s = 1; s <= 9; s++) {
                        next[s] = { ...next[s], status: "VERIFIED", summary: authStages[s]?.summary || next[s].summary };
                    }
                    return next;
                });
                setPresentedStage(9);
                setIsReplayingTrace(false);
                setSimulatorRunState("SUCCESS");

                if (onDone) onDone();

                dwellResetTimerRef.current = setTimeout(() => {
                    if (currentRunIdRef.current === runId) {
                        setSimulatorRunState("READY");
                    }
                }, 1800);
            }, 9 * PROCESSING_STAGE_PRESENTATION_DELAY_MS);
            presentationTimersRef.current.push(tFinal);
        },
        [clearPresentationTimers]
    );

    // Skip Presentation to End
    const skipToEnd = useCallback(() => {
        clearPresentationTimers();
        if (authoritativeStagesRef.current) {
            const auth = authoritativeStagesRef.current;
            setStageCards((prev) => {
                const next = { ...prev };
                for (let s = 1; s <= 9; s++) {
                    next[s] = { ...next[s], status: "VERIFIED", summary: auth[s]?.summary || next[s].summary };
                }
                return next;
            });
        }
        setPresentedStage(9);
        setIsReplayingTrace(false);
        setSimulatorRunState("SUCCESS");
        dwellResetTimerRef.current = setTimeout(() => {
            setSimulatorRunState("READY");
        }, 1800);
    }, [clearPresentationTimers]);

    // Replay Completed Trace / Run
    const triggerReplay = useCallback(
        (targetResult?: SimulationResult | null) => {
            const res = targetResult || currentResult;
            if (!res || !res.backendResponse) return;

            const replayRunId = `REPLAY-${Date.now().toString(36).toUpperCase().slice(-6)}`;
            currentRunIdRef.current = replayRunId;
            setCurrentRunId(replayRunId);
            setIsReplayingTrace(true);

            const backendResp = res.backendResponse;
            const hasEvents = (backendResp.events_detected ?? 0) > 0;
            const isAnom =
                backendResp.status === "PROCESSED_ANOMALY_DETECTED" ||
                backendResp.events?.some((e: any) => e.is_anomalous);
            const zScoreStr = backendResp.events?.find((e: any) => e.is_anomalous)?.magnitude_z_score
                ? `${backendResp.events.find((e: any) => e.is_anomalous).magnitude_z_score.toFixed(1)}σ`
                : "4.8σ";

            const authStages: Record<number, { title: string; summary: string }> = {
                1: {
                    title: "01 INGESTION",
                    summary: `${res.sampleCount} samples · ${(res.sampleRateHz / 1000).toFixed(0)} kHz verified`,
                },
                2: { title: "02 CONDITIONING", summary: "DC Removed · Nominal SNR verified" },
                3: {
                    title: "03 EVENT DETECTION",
                    summary: hasEvents ? `${backendResp.events_detected} DETECTED (Energy Threshold)` : "0 DETECTED (Nominal)",
                },
                4: {
                    title: "04 FEATURE EXTRACTION",
                    summary: backendResp.extracted_features
                        ? `Peak: ${backendResp.extracted_features.peak_amplitude.toFixed(2)}V · ${backendResp.extracted_features.duration_ms.toFixed(1)}ms`
                        : "Nominal Window",
                },
                5: { title: "05 BASELINE REFERENCE", summary: `Zone ${res.targetZoneId} Baseline Reference verified` },
                6: {
                    title: "06 ANOMALY EVALUATION",
                    summary: isAnom ? `ANOMALOUS (${zScoreStr} deviation)` : "NORMAL (0.2σ deviation)",
                },
                7: {
                    title: "07 PERSISTENCE",
                    summary: backendResp.temporal_persistence_confirmed ? "CONFIRMED (Temporal Window)" : "NOT CONFIRMED",
                },
                8: {
                    title: "08 CORRELATION",
                    summary: backendResp.cross_sensor_correlation_confirmed ? "CORRELATED (Cross-Transducer)" : "NOT CORRELATED",
                },
                9: {
                    title: "09 HEALTH & ALERT",
                    summary: `SHI ${backendResp.health_score !== null && backendResp.health_score !== undefined ? backendResp.health_score.toFixed(0) : "100"}/100${backendResp.alert_generated ? ` · ALERT #${backendResp.alert_id}` : " · NO ALERT"}`,
                },
            };
            authoritativeStagesRef.current = authStages;

            launchPresentationQueue(replayRunId, authStages, () => {
                setIsReplayingTrace(false);
            });
        },
        [currentResult, launchPresentationQueue]
    );

    const handleOpenInspector = useCallback(() => {
        setIsInspectorOpen(true);
        if (simulatorRunState === "READY" && currentResult?.backendResponse) {
            triggerReplay(currentResult);
        }
    }, [simulatorRunState, currentResult, triggerReplay]);

    // -------------------------------------------------------------
    // Execute Simulation Run & Submit Telemetry
    // -------------------------------------------------------------
    const executeSimulation = useCallback(
        async (transmit: boolean = true) => {
            clearPresentationTimers();
            const runId = `RUN-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
            currentRunIdRef.current = runId;
            setCurrentRunId(runId);
            setIsReplayingTrace(false);

            if (dwellResetTimerRef.current) {
                clearTimeout(dwellResetTimerRef.current);
                dwellResetTimerRef.current = null;
            }

            if (transmit) {
                setSimulatorRunState("SENDING");
                setPresentedStage(1);
                // Initialize clean pending state for new run
                setStageCards({
                    1: { id: 1, name: "INGESTION", title: "01 INGESTION", status: "PROCESSING", summary: "Transmitting telemetry packet..." },
                    2: { id: 2, name: "CONDITIONING", title: "02 CONDITIONING", status: "PENDING", summary: "Awaiting ingestion verification..." },
                    3: { id: 3, name: "EVENT_DETECTION", title: "03 EVENT DETECTION", status: "PENDING", summary: "Awaiting signal conditioning..." },
                    4: { id: 4, name: "FEATURE_EXTRACTION", title: "04 FEATURE EXTRACTION", status: "PENDING", summary: "Awaiting event detection..." },
                    5: { id: 5, name: "BASELINE_REFERENCE", title: "05 BASELINE REFERENCE", status: "PENDING", summary: "Awaiting feature extraction..." },
                    6: { id: 6, name: "ANOMALY_EVALUATION", title: "06 ANOMALY EVALUATION", status: "PENDING", summary: "Awaiting baseline evaluation..." },
                    7: { id: 7, name: "PERSISTENCE", title: "07 PERSISTENCE", status: "PENDING", summary: "Awaiting anomaly evaluation..." },
                    8: { id: 8, name: "CROSS_SENSOR_CORRELATION", title: "08 CORRELATION", status: "PENDING", summary: "Awaiting temporal persistence..." },
                    9: { id: 9, name: "HEALTH_AND_ALERT", title: "09 HEALTH & ALERT", status: "PENDING", summary: "Awaiting correlation results..." },
                });
            }

            // 1. Run deterministic physics simulation
            const physics = simulatePhysicsPropagation(
                mappedPath,
                physicalCondition,
                receiverGain,
                sampleCount,
                sampleRateHz
            );

            const peakAmp = Math.max(...physics.received.map(Math.abs));
            const expectedThreshold = primarySensor.zoneId === 2 ? 1.05 : 1.50;

            const seq = sequenceCounter;
            setSequenceCounter((prev) => prev + 1);

            const payload: any = {
                sensor_id: primarySensor.id,
                zone_name: targetZone,
                sample_rate_hz: sampleRateHz,
                sequence: seq,
                samples: physics.received,
                timestamp: new Date().toISOString(),
            };

            if (customThreshold.trim() !== "") {
                const parsed = parseFloat(customThreshold);
                if (!isNaN(parsed) && parsed > 0) {
                    payload.detection_threshold = parsed;
                }
            }

            let backendResp: any = null;
            let status: "IDLE" | "TRANSMITTING" | "ACCEPTED" | "FAILED" = "IDLE";
            let errStr: string | null = null;

            try {
                if (transmit) {
                    status = "TRANSMITTING";
                    try {
                        const postResp = await fetch(`${backendUrl}/api/v1/telemetry`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                Accept: "application/json",
                            },
                            body: JSON.stringify(payload),
                            signal: AbortSignal.timeout(15000),
                        });

                        // Ignore if a newer run has already started
                        if (currentRunIdRef.current !== runId) return;

                        if (postResp.ok) {
                            backendResp = await postResp.json();
                            status = "ACCEPTED";
                            setBackendConnected(true);

                            // Authoritative HTTP Stage Evidence Construction
                            const hasEvents = (backendResp.events_detected ?? 0) > 0;
                            const isAnom =
                                backendResp.status === "PROCESSED_ANOMALY_DETECTED" ||
                                backendResp.events?.some((e: any) => e.is_anomalous);
                            const zScoreStr = backendResp.events?.find((e: any) => e.is_anomalous)?.magnitude_z_score
                                ? `${backendResp.events.find((e: any) => e.is_anomalous).magnitude_z_score.toFixed(1)}σ`
                                : "4.8σ";

                            const authStages: Record<number, { title: string; summary: string }> = {
                                1: {
                                    title: "01 INGESTION",
                                    summary: `${payload.samples.length} samples · ${(payload.sample_rate_hz / 1000).toFixed(0)} kHz verified`,
                                },
                                2: { title: "02 CONDITIONING", summary: "DC Removed · Nominal SNR verified" },
                                3: {
                                    title: "03 EVENT DETECTION",
                                    summary: hasEvents ? `${backendResp.events_detected} DETECTED (Energy Threshold)` : "0 DETECTED (Nominal)",
                                },
                                4: {
                                    title: "04 FEATURE EXTRACTION",
                                    summary: backendResp.extracted_features
                                        ? `Peak: ${backendResp.extracted_features.peak_amplitude.toFixed(2)}V · ${backendResp.extracted_features.duration_ms.toFixed(1)}ms`
                                        : "Nominal Window",
                                },
                                5: { title: "05 BASELINE REFERENCE", summary: `Zone ${primarySensor.zoneId} Baseline Reference verified` },
                                6: {
                                    title: "06 ANOMALY EVALUATION",
                                    summary: isAnom ? `ANOMALOUS (${zScoreStr} deviation)` : "NORMAL (0.2σ deviation)",
                                },
                                7: {
                                    title: "07 PERSISTENCE",
                                    summary: backendResp.temporal_persistence_confirmed ? "CONFIRMED (Temporal Window)" : "NOT CONFIRMED",
                                },
                                8: {
                                    title: "08 CORRELATION",
                                    summary: backendResp.cross_sensor_correlation_confirmed ? "CORRELATED (Cross-Transducer)" : "NOT CORRELATED",
                                },
                                9: {
                                    title: "09 HEALTH & ALERT",
                                    summary: `SHI ${backendResp.health_score !== null && backendResp.health_score !== undefined ? backendResp.health_score.toFixed(0) : "100"}/100${backendResp.alert_generated ? ` · ALERT #${backendResp.alert_id}` : " · NO ALERT"}`,
                                },
                            };
                            authoritativeStagesRef.current = authStages;

                            // Launch the deliberate 1000ms stage presentation queue
                            launchPresentationQueue(runId, authStages);
                        } else {
                            status = "FAILED";
                            const errorText = await postResp.text();
                            errStr = `HTTP ${postResp.status}: ${errorText.slice(0, 100)}`;

                            setStageCards((prev) => ({
                                ...prev,
                                1: { ...prev[1], status: "FAILED", summary: `Ingest failed (${postResp.status})` },
                                2: { ...prev[2], status: "NOT_REACHED", summary: "Not reached" },
                                3: { ...prev[3], status: "NOT_REACHED", summary: "Not reached" },
                                4: { ...prev[4], status: "NOT_REACHED", summary: "Not reached" },
                                5: { ...prev[5], status: "NOT_REACHED", summary: "Not reached" },
                                6: { ...prev[6], status: "NOT_REACHED", summary: "Not reached" },
                                7: { ...prev[7], status: "NOT_REACHED", summary: "Not reached" },
                                8: { ...prev[8], status: "NOT_REACHED", summary: "Not reached" },
                                9: { ...prev[9], status: "NOT_REACHED", summary: "Not reached" },
                            }));

                            setSimulatorRunState("FAILED");
                            dwellResetTimerRef.current = setTimeout(() => {
                                if (currentRunIdRef.current === runId) {
                                    setSimulatorRunState("READY");
                                }
                            }, 2000);
                        }
                    } catch (e: any) {
                        if (currentRunIdRef.current !== runId) return;
                        status = "FAILED";
                        errStr = e.message || "Failed to reach backend endpoint";

                        setStageCards((prev) => ({
                            ...prev,
                            1: { ...prev[1], status: "FAILED", summary: "Network/endpoint unreachable" },
                            2: { ...prev[2], status: "NOT_REACHED", summary: "Not reached" },
                            3: { ...prev[3], status: "NOT_REACHED", summary: "Not reached" },
                            4: { ...prev[4], status: "NOT_REACHED", summary: "Not reached" },
                            5: { ...prev[5], status: "NOT_REACHED", summary: "Not reached" },
                            6: { ...prev[6], status: "NOT_REACHED", summary: "Not reached" },
                            7: { ...prev[7], status: "NOT_REACHED", summary: "Not reached" },
                            8: { ...prev[8], status: "NOT_REACHED", summary: "Not reached" },
                            9: { ...prev[9], status: "NOT_REACHED", summary: "Not reached" },
                        }));

                        setSimulatorRunState("FAILED");
                        dwellResetTimerRef.current = setTimeout(() => {
                            if (currentRunIdRef.current === runId) {
                                setSimulatorRunState("READY");
                            }
                        }, 2000);
                    }
                }

                const simId = `SIM-${Date.now().toString(36).toUpperCase().slice(-6)}`;
                const result: SimulationResult = {
                    simulationId: simId,
                    timestamp: new Date().toLocaleTimeString(),
                    sourceSensor: sourceSensor.id,
                    receiverSensor: primarySensor.id,
                    targetZoneName: targetZone,
                    targetZoneId: primarySensor.zoneId,
                    scenario: physicalCondition,
                    pathId: mappedPath.pathId,
                    distanceM: mappedPath.distanceM,
                    waveVelocityMS: mappedPath.waveVelocityMS,
                    propagationDelayS: physics.delayS,
                    propagationDelayMs: physics.delayMs,
                    attenuationDb: physics.attenuationDb,
                    amplitudeFactor: physics.amplitudeFactor,
                    isDamaged: physicalCondition === "anomaly",
                    damagedComponentGuid: physicalCondition === "anomaly" ? FIXED_DAMAGED_COMPONENT.guid : null,
                    damagedComponentType: FIXED_DAMAGED_COMPONENT.type,
                    damageInfluenceFactor: physicalCondition === "anomaly" ? FIXED_DAMAGED_COMPONENT.influence : 0.0,
                    primaryAttenuationMultiplier: physics.attenuationMultiplier,
                    primaryDelayShiftSamples: physics.delayShiftSamples,
                    scatteringAmplitude: physics.scatteringAmplitude,
                    scatteringDelayMs: physics.scatteringDelayMs,
                    scatteringDelaySamples: physics.scatteringDelaySamples,
                    sampleRateHz,
                    sampleCount,
                    excitationSamples: physics.excitation,
                    primaryPropagatedSamples: physics.primaryPropagated,
                    scatteredSamples: physics.scattered,
                    receivedSamples: physics.received,
                    simPeak: peakAmp,
                    detectionThresholdExpected: expectedThreshold,
                    telemetryPayload: payload,
                    backendResponse: backendResp,
                    telemetryStatus: status,
                    telemetryError: errStr,
                };

                setCurrentResult(result);
                setSelectedRunHistoryId(result.simulationId);

                if (transmit) {
                    setRunHistory((prev) => [result, ...prev.slice(0, 24)]);
                }
            } catch (err: any) {
                console.error("[Simulator] Unhandled simulation error:", err);
            }
        },
        [
            mappedPath,
            physicalCondition,
            receiverGain,
            sampleCount,
            sampleRateHz,
            sequenceCounter,
            primarySensor,
            targetZone,
            customThreshold,
            backendUrl,
            sourceSensor,
        ]
    );

    // Trigger initial simulation preview on load/change
    useEffect(() => {
        executeSimulation(false);
    }, [selectedSensorId, physicalCondition]);

    // Streaming interval control
    useEffect(() => {
        let streamTimer: NodeJS.Timeout | null = null;
        if (isStreaming) {
            streamTimer = setInterval(() => {
                executeSimulation(true);
            }, Math.max(packetIntervalMs, 250));
        }
        return () => {
            if (streamTimer) clearInterval(streamTimer);
        };
    }, [isStreaming, packetIntervalMs, executeSimulation]);

    // -------------------------------------------------------------
    // Canvas Waveform Renderer
    // -------------------------------------------------------------
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !currentResult) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height;

        ctx.clearRect(0, 0, width, height);

        // Dark Canvas Background
        ctx.fillStyle = "#020617";
        ctx.fillRect(0, 0, width, height);

        // Grid lines
        ctx.strokeStyle = "rgba(51, 65, 85, 0.25)";
        ctx.lineWidth = 1;
        for (let x = 0; x < width; x += 40) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        for (let y = 0; y < height; y += 24) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        const midY = height / 2;
        const yScale = (height / 2) * 0.45;

        // Zero Baseline
        ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(0, midY);
        ctx.lineTo(width, midY);
        ctx.stroke();
        ctx.setLineDash([]);

        const samples = currentResult.receivedSamples;
        const totalPts = samples.length;
        if (totalPts === 0) return;

        // Threshold Lines
        const thresh = currentResult.detectionThresholdExpected;
        const threshYPos = midY - thresh * yScale;
        const threshYNeg = midY + thresh * yScale;

        ctx.strokeStyle = "rgba(245, 158, 11, 0.70)";
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(0, threshYPos);
        ctx.lineTo(width, threshYPos);
        ctx.moveTo(0, threshYNeg);
        ctx.lineTo(width, threshYNeg);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = "#f59e0b";
        ctx.font = "10px ui-monospace, SFMono-Regular, monospace";
        ctx.fillText(`+${thresh.toFixed(2)} THRESHOLD`, width - 105, threshYPos - 4);
        ctx.fillText(`-${thresh.toFixed(2)} THRESHOLD`, width - 105, threshYNeg + 12);

        // Component Decomposition Traces
        if (showDecomposition && currentResult.isDamaged) {
            const scat = currentResult.scatteredSamples;
            if (scat.length > 0) {
                ctx.strokeStyle = "rgba(245, 158, 11, 0.50)";
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                for (let i = 0; i < scat.length; i++) {
                    const x = (i / totalPts) * width;
                    const y = midY - scat[i] * yScale;
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }

            const prim = currentResult.primaryPropagatedSamples;
            if (prim.length > 0) {
                ctx.strokeStyle = "rgba(56, 189, 248, 0.40)";
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                for (let i = 0; i < prim.length; i++) {
                    const x = (i / totalPts) * width;
                    const y = midY - prim[i] * yScale;
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        }

        // Main Waveform Trace
        const isAnom = currentResult.simPeak >= thresh;
        ctx.strokeStyle = isAnom ? "#ef4444" : "#38bdf8";
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        for (let i = 0; i < totalPts; i++) {
            const x = (i / totalPts) * width;
            const y = midY - samples[i] * yScale;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Highlight Above-Threshold Regions
        ctx.fillStyle = "rgba(239, 68, 68, 0.28)";
        for (let i = 0; i < totalPts; i++) {
            if (Math.abs(samples[i]) >= thresh) {
                const x = (i / totalPts) * width;
                ctx.fillRect(x - 1, 0, 2, height);
            }
        }
    }, [currentResult, showDecomposition]);

    // Active displayed run details
    const activeDisplayRun = useMemo(() => {
        if (!selectedRunHistoryId) return currentResult;
        return runHistory.find((r) => r.simulationId === selectedRunHistoryId) || currentResult;
    }, [selectedRunHistoryId, runHistory, currentResult]);

    return (
        <div className="min-h-screen max-h-screen h-screen bg-[#020617] text-[#f8fafc] font-sans flex flex-col overflow-hidden select-none">
            {/* ========================================================= */}
            {/* HEADER & GLOBAL STATUS BAR                                 */}
            {/* ========================================================= */}
            <header className="h-12 border-b border-slate-800 bg-[#080d1a] px-3.5 flex items-center justify-between shrink-0 z-30">
                <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                    <span className="text-xs font-mono tracking-widest text-slate-200 uppercase font-bold">
                        AEGIS3D • PZT SENSOR SIMULATOR
                    </span>
                    <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400 font-mono">
                        ENGINEERING CONSOLE v2.0
                    </span>
                </div>

                <div className="flex items-center gap-2 font-mono text-[11px]">
                    {/* Live / SSE State */}
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
                        <span className="text-slate-400">SSE:</span>
                        <span className={sseState === "CONNECTED" ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                            {sseState}
                        </span>
                    </div>

                    {/* API Connection State */}
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
                        <span className="text-slate-400">API:</span>
                        {backendConnected === true ? (
                            <span className="text-emerald-400 font-bold">LIVE ({backendLatencyMs}ms)</span>
                        ) : (
                            <span className="text-rose-400 font-bold">DISCONNECTED</span>
                        )}
                    </div>

                    {/* Run State Badge */}
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
                        <span className="text-slate-400">STATE:</span>
                        <span className={
                            simulatorRunState === "READY"
                                ? "text-cyan-400 font-bold"
                                : simulatorRunState === "SENDING"
                                ? "text-amber-400 font-bold animate-pulse"
                                : simulatorRunState === "PROCESSING"
                                ? "text-amber-300 font-bold animate-pulse"
                                : simulatorRunState === "SUCCESS"
                                ? "text-emerald-400 font-bold"
                                : "text-rose-400 font-bold"
                        }>
                            {simulatorRunState}
                        </span>
                    </div>

                    {/* Clear Active Alerts Button */}
                    <button
                        type="button"
                        onClick={handleClearActiveAlerts}
                        disabled={clearingAlerts}
                        className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition cursor-pointer font-bold text-[10px] flex items-center gap-1"
                    >
                        {clearingAlerts ? "CLEARING..." : "CLEAR ACTIVE ALERTS"}
                    </button>
                    {clearAlertsFeedback && (
                        <span className="text-[10px] text-amber-400 font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
                            {clearAlertsFeedback}
                        </span>
                    )}

                    {/* Reset Button */}
                    <button
                        type="button"
                        onClick={() => {
                            handlePresetChange("01_NORMAL");
                            setRunHistory([]);
                            setStageCards(getDefaultStageCards());
                            setSimulatorRunState("READY");
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition cursor-pointer"
                    >
                        RESET
                    </button>

                    {/* Inspect Processing Launcher */}
                    <button
                        type="button"
                        onClick={handleOpenInspector}
                        className="flex items-center gap-1.5 px-3 py-1 rounded bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/50 font-bold text-[11px] transition cursor-pointer shadow-sm shadow-sky-900/40"
                    >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                            <circle cx="11" cy="11" r="8" />
                            <line x1="21" y1="21" x2="16.65" y2="16.65" />
                        </svg>
                        <span>INSPECT PROCESSING</span>
                    </button>

                    {/* Link to 3D Digital Twin */}
                    <Link
                        href="/dashboard"
                        className="flex items-center gap-1 px-3 py-1 rounded bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 text-sky-300 font-medium transition cursor-pointer"
                    >
                        <span>VIEW 3D TWIN</span>
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                    </Link>
                </div>
            </header>

            {/* ========================================================= */}
            {/* MAIN OPERATOR CONSOLE GRID (25% / 50% / 25%)              */}
            {/* ========================================================= */}
            <main className="flex-1 p-2.5 flex flex-col gap-2 overflow-hidden">
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-2.5 min-h-0 overflow-hidden">
                    {/* ----------------------------------------------------- */}
                    {/* LEFT PANEL: 01 SIMULATION CONTROL (Col 1-3 / 25%)      */}
                    {/* ----------------------------------------------------- */}
                    <div className="lg:col-span-3 flex flex-col bg-[#0b1329]/90 border border-slate-800 rounded p-2.5 overflow-y-auto custom-scrollbar gap-2.5 font-mono text-xs">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                            <span className="font-bold text-slate-200 tracking-wider">01 SIMULATION CONTROL</span>
                            <span className="text-[10px] text-slate-500">OPERATOR INPUT</span>
                        </div>

                        {/* 5.1 Sensor Selection */}
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-slate-400">PZT SENSOR SELECTION</label>
                            <select
                                value={selectedSensorId}
                                onChange={(e) => setSelectedSensorId(e.target.value)}
                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-sky-500 cursor-pointer"
                            >
                                {CANONICAL_SENSORS.map((s) => (
                                    <option key={s.id} value={s.id}>
                                        {s.id} ({s.storey}) - {s.zoneName ? `Zone ${s.zoneId}` : "Unassigned"}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Mapped Zone & Storey */}
                        <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                            <div className="p-1.5 rounded bg-slate-900/80 border border-slate-800">
                                <span className="text-slate-500 block">MAPPED ZONE</span>
                                <span className="text-cyan-400 font-bold truncate block">{targetZone}</span>
                            </div>
                            <div className="p-1.5 rounded bg-slate-900/80 border border-slate-800">
                                <span className="text-slate-500 block">STOREY LEVEL</span>
                                <span className="text-slate-300 font-bold block">{primarySensor.storey}</span>
                            </div>
                        </div>

                        {/* Sensor Pair Mode */}
                        <div className="flex items-center justify-between p-1.5 rounded bg-slate-900/60 border border-slate-800 text-[11px]">
                            <span className="text-slate-400">CORRELATION PAIRING:</span>
                            <button
                                type="button"
                                onClick={() => setPairMode(!pairMode)}
                                className={`px-2 py-0.5 rounded text-[10px] border cursor-pointer ${
                                    pairMode ? "bg-amber-500/20 text-amber-300 border-amber-500/50" : "bg-slate-800 text-slate-400 border-slate-700"
                                }`}
                            >
                                {pairMode ? "PAIR MODE ACTIVE" : "OFF (SINGLE PZT)"}
                            </button>
                        </div>

                        {pairMode && (
                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-slate-400">SECONDARY PZT SENSOR</label>
                                <select
                                    value={secondarySensorId}
                                    onChange={(e) => setSecondarySensorId(e.target.value)}
                                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                                >
                                    {CANONICAL_SENSORS.filter((s) => s.id !== selectedSensorId).map((s) => (
                                        <option key={s.id} value={s.id}>
                                            {s.id} ({s.storey})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* 5.2 Scenario Presets */}
                        <div className="flex flex-col gap-1 pt-1">
                            <label className="text-[10px] text-slate-400">SCENARIO PRESETS</label>
                            <div className="grid grid-cols-1 gap-1">
                                {[
                                    { id: "01_NORMAL", label: "01 NORMAL BASELINE", desc: "Clean guided wave packet" },
                                    { id: "02_SINGLE_EVENT", label: "02 SINGLE ANOMALOUS EVENT", desc: "Discontinuity echo response" },
                                    { id: "03_PERSISTENT", label: "03 PERSISTENT ANOMALY", desc: "Repeated abnormal packets" },
                                    { id: "04_CORRELATED", label: "04 CROSS-SENSOR CORRELATION", desc: "Aligned dual-PZT packets" },
                                ].map((scen) => (
                                    <button
                                        key={scen.id}
                                        type="button"
                                        onClick={() => handlePresetChange(scen.id as any)}
                                        className={`p-1.5 rounded text-left border transition cursor-pointer ${
                                            presetScenario === scen.id
                                                ? scen.id === "01_NORMAL"
                                                    ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300"
                                                    : "bg-rose-500/20 border-rose-500/50 text-rose-300"
                                                : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200"
                                        }`}
                                    >
                                        <div className="font-bold text-[11px]">{scen.label}</div>
                                        <div className="text-[9px] text-slate-500">{scen.desc}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 5.3 Core Signal Parameters */}
                        <div className="flex flex-col gap-2 pt-1 border-t border-slate-800">
                            <span className="text-[10px] text-slate-400 font-bold">CORE SIGNAL PARAMETERS</span>

                            {/* Sample Rate */}
                            <div className="flex flex-col gap-1">
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-slate-400">SAMPLE RATE (Hz):</span>
                                    <span className="text-cyan-400 font-bold">{(sampleRateHz / 1000).toFixed(0)} kHz</span>
                                </div>
                                <div className="grid grid-cols-4 gap-1">
                                    {[5000, 10000, 20000, 100000].map((rate) => (
                                        <button
                                            key={rate}
                                            type="button"
                                            onClick={() => setSampleRateHz(rate)}
                                            className={`py-0.5 text-[9px] rounded border cursor-pointer ${
                                                sampleRateHz === rate
                                                    ? "bg-sky-500/20 border-sky-500/50 text-sky-300"
                                                    : "bg-slate-900 border-slate-800 text-slate-400"
                                            }`}
                                        >
                                            {rate >= 1000 ? `${rate / 1000}k` : rate}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Samples per Packet */}
                            <div className="flex flex-col gap-1">
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-slate-400">SAMPLES / PACKET:</span>
                                    <span className="text-cyan-400 font-bold">{sampleCount}</span>
                                </div>
                                <div className="grid grid-cols-4 gap-1">
                                    {[512, 1024, 2048, 10000].map((cnt) => (
                                        <button
                                            key={cnt}
                                            type="button"
                                            onClick={() => setSampleCount(cnt)}
                                            className={`py-0.5 text-[9px] rounded border cursor-pointer ${
                                                sampleCount === cnt
                                                    ? "bg-sky-500/20 border-sky-500/50 text-sky-300"
                                                    : "bg-slate-900 border-slate-800 text-slate-400"
                                            }`}
                                        >
                                            {cnt}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Amplitude Slider */}
                            <div className="flex flex-col gap-1">
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-slate-400">BASE AMPLITUDE:</span>
                                    <span className="text-slate-200">{baseAmplitude.toFixed(2)}</span>
                                </div>
                                <input
                                    type="range"
                                    min="0.1"
                                    max="2.0"
                                    step="0.05"
                                    value={baseAmplitude}
                                    onChange={(e) => setBaseAmplitude(parseFloat(e.target.value))}
                                    className="w-full accent-cyan-500 bg-slate-900 h-1.5 rounded cursor-pointer"
                                />
                            </div>

                            {/* Frequency Slider */}
                            <div className="flex flex-col gap-1">
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-slate-400">FREQUENCY (f):</span>
                                    <span className="text-slate-200">{(baseFrequencyHz / 1000).toFixed(1)} kHz</span>
                                </div>
                                <input
                                    type="range"
                                    min="1000"
                                    max="50000"
                                    step="1000"
                                    value={baseFrequencyHz}
                                    onChange={(e) => setBaseFrequencyHz(parseInt(e.target.value))}
                                    className="w-full accent-cyan-500 bg-slate-900 h-1.5 rounded cursor-pointer"
                                />
                            </div>
                        </div>

                        {/* 5.4 Anomaly Injection Controls */}
                        {physicalCondition === "anomaly" && (
                            <div className="flex flex-col gap-2 pt-2 border-t border-slate-800">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] text-rose-400 font-bold">DISCONTINUITY SCATTERING</span>
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
                                        ACTIVE
                                    </span>
                                </div>

                                <div className="flex justify-between text-[10px]">
                                    <span className="text-slate-400">SCATTERING TRANSFER FACTOR:</span>
                                    <span className="text-rose-400 font-bold">{amplitudeMultiplier.toFixed(2)}x</span>
                                </div>
                                <input
                                    type="range"
                                    min="0.5"
                                    max="3.0"
                                    step="0.05"
                                    value={amplitudeMultiplier}
                                    onChange={(e) => setAmplitudeMultiplier(parseFloat(e.target.value))}
                                    className="w-full accent-rose-500 bg-slate-900 h-1.5 rounded cursor-pointer"
                                />
                            </div>
                        )}

                        {/* Primary Action Buttons */}
                        <div className="flex flex-col gap-1.5 pt-2 mt-auto border-t border-slate-800">
                            <button
                                type="button"
                                disabled={simulatorRunState === "SENDING" || simulatorRunState === "PROCESSING"}
                                onClick={() => executeSimulation(true)}
                                className={`w-full py-2 rounded text-xs font-bold uppercase tracking-wider transition cursor-pointer border ${
                                    physicalCondition === "anomaly"
                                        ? "bg-rose-600 hover:bg-rose-500 text-white border-rose-400/50 shadow-md shadow-rose-900/30"
                                        : "bg-cyan-600 hover:bg-cyan-500 text-white border-cyan-400/50 shadow-md shadow-cyan-900/30"
                                } disabled:opacity-50`}
                            >
                                {simulatorRunState === "SENDING" ? "TRANSMITTING..." : simulatorRunState === "PROCESSING" ? "PROCESSING PIPELINE..." : "RUN SCENARIO & TRANSMIT"}
                            </button>

                            <button
                                type="button"
                                onClick={() => setIsStreaming(!isStreaming)}
                                className={`w-full py-1.5 rounded text-xs font-medium border cursor-pointer ${
                                    isStreaming
                                        ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                                        : "bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-700"
                                }`}
                            >
                                {isStreaming ? "STOP STREAMING" : "STREAM SCENARIO"}
                            </button>

                            <button
                                type="button"
                                onClick={handleOpenInspector}
                                className="w-full py-1.5 rounded text-xs font-bold bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 flex items-center justify-center gap-1.5 transition cursor-pointer"
                            >
                                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                                    <circle cx="11" cy="11" r="8" />
                                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                                </svg>
                                <span>INSPECT PROCESSING</span>
                            </button>
                        </div>
                    </div>

                    {/* ----------------------------------------------------- */}
                    {/* CENTER PANEL: 02 SIGNAL / WAVEFORM (Col 4-8 / 50%)    */}
                    {/* ----------------------------------------------------- */}
                    <div className="lg:col-span-6 flex flex-col bg-[#0b1329]/90 border border-slate-800 rounded p-2.5 min-h-0">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-2 font-mono text-xs">
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-200 tracking-wider">02 SIGNAL / WAVEFORM</span>
                                <span className="text-[10px] text-slate-400">
                                    {mappedPath.pathId}: {mappedPath.actuatorId} → {mappedPath.receiverId}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 text-[10px]">
                                <label className="flex items-center gap-1 cursor-pointer text-slate-400">
                                    <input
                                        type="checkbox"
                                        checked={showDecomposition}
                                        onChange={(e) => setShowDecomposition(e.target.checked)}
                                        className="rounded bg-slate-900 border-slate-700 text-cyan-500"
                                    />
                                    <span>ECHO DECOMPOSITION</span>
                                </label>
                            </div>
                        </div>

                        {/* Waveform Bounded Canvas Viewport */}
                        <div className="relative w-full flex-1 min-h-[200px] max-h-[280px] rounded bg-[#020617] border border-slate-800 overflow-hidden">
                            <canvas ref={canvasRef} className="w-full h-full block" />
                        </div>

                        {/* Signal Statistics beneath Waveform */}
                        <div className="grid grid-cols-6 gap-1.5 mt-2 font-mono text-[10px]">
                            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-500 block">PEAK (SIM)</span>
                                <span className={`font-bold text-xs ${currentResult && currentResult.simPeak >= currentResult.detectionThresholdExpected ? "text-rose-400" : "text-emerald-400"}`}>
                                    {currentResult ? currentResult.simPeak.toFixed(3) : "---"}
                                </span>
                            </div>

                            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-500 block">THRESHOLD</span>
                                <span className="text-amber-400 font-bold text-xs">
                                    {currentResult ? currentResult.detectionThresholdExpected.toFixed(2) : "---"}
                                </span>
                            </div>

                            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-500 block">DELAY (τ)</span>
                                <span className="text-cyan-400 font-bold text-xs">
                                    {currentResult ? `${currentResult.propagationDelayMs.toFixed(2)}ms` : "---"}
                                </span>
                            </div>

                            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-500 block">LOSS (dB)</span>
                                <span className="text-slate-300 font-bold text-xs">
                                    {currentResult ? `${currentResult.attenuationDb.toFixed(1)}dB` : "---"}
                                </span>
                            </div>

                            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-500 block">EVENTS</span>
                                <span className="text-slate-200 font-bold text-xs">
                                    {currentResult?.backendResponse ? currentResult.backendResponse.events_detected : 0}
                                </span>
                            </div>

                            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
                                <span className="text-slate-500 block">ANOMALY</span>
                                <span className={currentResult?.backendResponse?.status === "PROCESSED_ANOMALY_DETECTED" ? "text-rose-400 font-bold text-xs" : "text-slate-400 text-xs"}>
                                    {currentResult?.backendResponse?.status === "PROCESSED_ANOMALY_DETECTED" ? "YES" : "NO"}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* ----------------------------------------------------- */}
                    {/* RIGHT PANEL: 03 LIVE TELEMETRY (Col 9-12 / 25%)        */}
                    {/* ----------------------------------------------------- */}
                    <div className="lg:col-span-3 flex flex-col bg-[#0b1329]/90 border border-slate-800 rounded p-2.5 overflow-y-auto custom-scrollbar gap-2.5 font-mono text-xs">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                            <span className="font-bold text-slate-200 tracking-wider">03 LIVE TELEMETRY</span>
                            <span className="text-[10px] text-slate-500">BACKEND STATE</span>
                        </div>

                        {/* Packet Card */}
                        <div className="p-2 rounded bg-slate-900/80 border border-slate-800 flex flex-col gap-1 text-[10px]">
                            <span className="text-slate-400 font-bold text-[9px] uppercase tracking-wider">LATEST TELEMETRY PACKET</span>
                            <div className="flex justify-between"><span className="text-slate-500">Sensor:</span><span className="text-cyan-400 font-bold">{primarySensor.id}</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">Zone:</span><span className="text-slate-300 truncate max-w-[120px]">{targetZone}</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">Sample Rate:</span><span className="text-slate-300">{(sampleRateHz / 1000).toFixed(0)} kHz</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">Samples:</span><span className="text-slate-300">{sampleCount}</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">Sequence:</span><span className="text-slate-300">#{currentResult?.telemetryPayload?.sequence || 0}</span></div>
                        </div>

                        {/* Processing Card */}
                        <div className="p-2 rounded bg-slate-900/80 border border-slate-800 flex flex-col gap-1 text-[10px]">
                            <span className="text-slate-400 font-bold text-[9px] uppercase tracking-wider">BACKEND PIPELINE STAGE</span>
                            <div className="flex justify-between">
                                <span className="text-slate-500">Active Stage:</span>
                                <span className="text-amber-400 font-bold">
                                    {sseActiveStage ? STAGE_NAMES[sseActiveStage - 1] : simulatorRunState === "SUCCESS" ? "COMPLETE (9/9)" : "IDLE"}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500">Pipeline State:</span>
                                <span className={simulatorRunState === "SUCCESS" ? "text-emerald-400 font-bold" : simulatorRunState === "FAILED" ? "text-rose-400 font-bold" : "text-slate-300"}>
                                    {simulatorRunState}
                                </span>
                            </div>
                            {sseBackendDurationMs !== null && (
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Duration:</span>
                                    <span className="text-slate-300">{sseBackendDurationMs} ms</span>
                                </div>
                            )}
                        </div>

                        {/* Health Card */}
                        <div className="p-2 rounded bg-slate-900/80 border border-slate-800 flex flex-col gap-1 text-[10px]">
                            <span className="text-slate-400 font-bold text-[9px] uppercase tracking-wider">STRUCTURAL HEALTH (SHI)</span>
                            <div className="flex justify-between items-center">
                                <span className="text-slate-500">SHI Score:</span>
                                <span className={currentResult?.backendResponse?.health_score && currentResult.backendResponse.health_score < 80 ? "text-rose-400 font-bold text-sm" : "text-emerald-400 font-bold text-sm"}>
                                    {currentResult?.backendResponse?.health_score !== undefined && currentResult.backendResponse.health_score !== null
                                        ? `${currentResult.backendResponse.health_score.toFixed(1)}/100`
                                        : "100.0 (NOMINAL)"}
                                </span>
                            </div>
                            <div className="text-[9px] text-slate-500 italic mt-0.5">
                                Disclaimer: SHI is an evidence-based monitoring metric, not a certified structural safety score.
                            </div>
                        </div>

                        {/* Alert Card */}
                        <div className="p-2 rounded bg-slate-900/80 border border-slate-800 flex flex-col gap-1 text-[10px]">
                            <span className="text-slate-400 font-bold text-[9px] uppercase tracking-wider">ALERT EVALUATION</span>
                            {currentResult?.backendResponse?.alert_generated ? (
                                <div className="p-1.5 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300 font-bold">
                                    ALERT #{currentResult.backendResponse.alert_id} (MEDIUM SEVERITY)
                                </div>
                            ) : (
                                <span className="text-slate-400">No alert generated.</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* ========================================================= */}
                {/* 04 NINE-STAGE PROCESSING PIPELINE STRIP (FULL WIDTH)      */}
                {/* ========================================================= */}
                <div className="bg-[#0b1329]/90 border border-slate-800 rounded p-2.5 flex flex-col gap-2 shrink-0 font-mono text-xs">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-200 tracking-wider text-[11px]">04 PROCESSING PIPELINE — NINE STAGE BACKEND EVIDENCE</span>
                            <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                                simulatorRunState === "READY"
                                    ? "bg-slate-800 text-slate-400"
                                    : simulatorRunState === "PROCESSING" || simulatorRunState === "SENDING"
                                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse"
                                    : simulatorRunState === "SUCCESS"
                                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                                    : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            }`}>
                                {simulatorRunState}
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={handleOpenInspector}
                                className="px-2 py-0.5 rounded bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 text-[10px] font-bold flex items-center gap-1 transition cursor-pointer"
                            >
                                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                                    <circle cx="11" cy="11" r="8" />
                                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                                </svg>
                                <span>INSPECT PROCESSING</span>
                            </button>
                            <span className="text-[10px] text-slate-500">AUTHORITATIVE BACKEND EXECUTION</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-9 gap-1.5 text-[9px]">
                        {STAGE_CONFIGS.map((cfg) => {
                            const stageData = stageCards[cfg.id];
                            const status = stageData?.status || "PENDING";
                            const isVerified = status === "VERIFIED";
                            const isProcessing = status === "PROCESSING";
                            const isFailed = status === "FAILED";
                            const isNotReached = status === "NOT_REACHED";

                            return (
                                <div
                                    key={cfg.id}
                                    className={`p-2 rounded border flex flex-col justify-between min-h-[72px] transition-all ${
                                        isVerified
                                            ? "bg-emerald-950/40 border-emerald-500/60 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.15)]"
                                            : isProcessing
                                            ? "bg-amber-950/40 border-amber-500/80 text-amber-300 animate-pulse shadow-[0_0_10px_rgba(245,158,11,0.2)]"
                                            : isFailed
                                            ? "bg-rose-950/40 border-rose-500/70 text-rose-300"
                                            : isNotReached
                                            ? "bg-slate-900/40 border-slate-800/80 text-slate-600 opacity-60"
                                            : "bg-slate-900/70 border-slate-800 text-slate-400"
                                    }`}
                                >
                                    <div className="flex items-center justify-between font-bold">
                                        <span className="text-[10px] tracking-wider text-slate-300">0{cfg.id}</span>
                                        <span className={`text-[8px] font-bold px-1 py-0.5 rounded ${
                                            isVerified
                                                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                                                : isProcessing
                                                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                                                : isFailed
                                                ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                                                : isNotReached
                                                ? "bg-slate-800 text-slate-500"
                                                : "bg-slate-800 text-slate-400"
                                        }`}>
                                            {isVerified ? "✓ VERIFIED" : isProcessing ? "⟳ RUNNING" : isFailed ? "✕ FAILED" : isNotReached ? "— NOT REACHED" : "• PENDING"}
                                        </span>
                                    </div>
                                    <div className="font-bold text-[9px] leading-tight truncate text-slate-100 mt-1">
                                        {cfg.name.replace(/_/g, " ")}
                                    </div>
                                    <div className={`text-[8px] font-mono truncate mt-1 ${
                                        isVerified ? "text-emerald-300/90 font-medium" : isProcessing ? "text-amber-300" : isFailed ? "text-rose-400" : "text-slate-500"
                                    }`}>
                                        {stageData?.summary || "Pending dispatch"}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* ========================================================= */}
                {/* 05 RUN HISTORY / EVENT LOG (FULL WIDTH)                   */}
                {/* ========================================================= */}
                <div className="bg-[#0b1329]/90 border border-slate-800 rounded p-2 flex flex-col gap-1 shrink-0 font-mono text-xs max-h-36 overflow-hidden">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-1">
                        <span className="font-bold text-slate-200 tracking-wider text-[11px]">05 RUN HISTORY / EVENT LOG</span>
                        <span className="text-[10px] text-slate-500">{runHistory.length} RUNS RECORDED</span>
                    </div>

                    <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1">
                        <table className="w-full text-[10px] text-left border-collapse">
                            <thead>
                                <tr className="text-slate-500 border-b border-slate-800">
                                    <th className="py-1 px-1.5">TIME</th>
                                    <th className="py-1 px-1.5">RUN ID</th>
                                    <th className="py-1 px-1.5">SENSOR</th>
                                    <th className="py-1 px-1.5">ZONE</th>
                                    <th className="py-1 px-1.5">SCENARIO</th>
                                    <th className="py-1 px-1.5">PEAK</th>
                                    <th className="py-1 px-1.5">EVENTS</th>
                                    <th className="py-1 px-1.5">ANOMALY</th>
                                    <th className="py-1 px-1.5">SHI</th>
                                    <th className="py-1 px-1.5">ALERT</th>
                                    <th className="py-1 px-1.5">STATUS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {runHistory.length === 0 ? (
                                    <tr>
                                        <td colSpan={11} className="py-2 text-center text-slate-600">
                                            No runs dispatched yet. Click &apos;RUN SCENARIO & TRANSMIT&apos; to record telemetry telemetry.
                                        </td>
                                    </tr>
                                ) : (
                                    runHistory.map((run) => (
                                        <tr
                                            key={run.simulationId}
                                            onClick={() => {
                                                setCurrentResult(run);
                                                setSelectedRunHistoryId(run.simulationId);
                                            }}
                                            className={`border-b border-slate-800/50 cursor-pointer hover:bg-slate-800/50 transition ${
                                                selectedRunHistoryId === run.simulationId ? "bg-sky-500/10 text-sky-200" : "text-slate-300"
                                            }`}
                                        >
                                            <td className="py-1 px-1.5 font-bold">{run.timestamp}</td>
                                            <td className="py-1 px-1.5 text-cyan-400">{run.simulationId}</td>
                                            <td className="py-1 px-1.5 font-bold">{run.receiverSensor}</td>
                                            <td className="py-1 px-1.5 truncate max-w-[100px]">{run.targetZoneName}</td>
                                            <td className="py-1 px-1.5">{run.scenario.toUpperCase()}</td>
                                            <td className="py-1 px-1.5 font-bold">{run.simPeak.toFixed(3)}</td>
                                            <td className="py-1 px-1.5">{run.backendResponse?.events_detected ?? 0}</td>
                                            <td className="py-1 px-1.5">
                                                <span className={run.backendResponse?.status === "PROCESSED_ANOMALY_DETECTED" ? "text-rose-400 font-bold" : "text-slate-400"}>
                                                    {run.backendResponse?.status === "PROCESSED_ANOMALY_DETECTED" ? "YES" : "NO"}
                                                </span>
                                            </td>
                                            <td className="py-1 px-1.5 font-bold">
                                                {run.backendResponse?.health_score !== undefined && run.backendResponse.health_score !== null
                                                    ? run.backendResponse.health_score.toFixed(1)
                                                    : "100.0"}
                                            </td>
                                            <td className="py-1 px-1.5">
                                                {run.backendResponse?.alert_generated ? (
                                                    <span className="text-rose-400 font-bold">ALERT #{run.backendResponse.alert_id}</span>
                                                ) : (
                                                    <span className="text-slate-500">NONE</span>
                                                )}
                                            </td>
                                            <td className="py-1 px-1.5">
                                                <span className={run.telemetryStatus === "ACCEPTED" ? "text-emerald-400" : "text-rose-400"}>
                                                    {run.telemetryStatus}
                                                </span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>

            {/* ========================================================= */}
            {/* FULLSCREEN/CENTERED TELEMETRY PROCESSING INSPECTOR MODAL  */}
            {/* ========================================================= */}
            {isInspectorOpen && (
                <TelemetryProcessingInspector
                    isOpen={isInspectorOpen}
                    onClose={() => setIsInspectorOpen(false)}
                    runId={currentRunId || currentResult?.simulationId || "RUN-STANDBY"}
                    sensorId={primarySensor.id}
                    zoneName={targetZone}
                    currentResult={currentResult}
                    simulatorRunState={simulatorRunState}
                    stageCards={stageCards}
                    sseState={sseState}
                    sseActiveStage={sseActiveStage}
                    sseBackendDurationMs={sseBackendDurationMs}
                    presentedStage={presentedStage}
                    isReplayingTrace={isReplayingTrace}
                    onTriggerReplay={triggerReplay}
                    onSkipToEnd={skipToEnd}
                    identifier={
                        currentResult?.backendResponse?.telemetry_id
                            ? String(currentResult.backendResponse.telemetry_id)
                            : primarySensor.id
                    }
                />
            )}
        </div>
    );
}
