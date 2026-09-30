"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
    LiveConnectionState,
    LiveEventType,
    LiveProcessingEvent,
    LiveStageInfo,
    LiveStageStatus,
    ProcessingStage,
} from "@/types/api";

export const STAGE_NAMES: ProcessingStage[] = [
    "INGESTION",
    "CONDITIONING",
    "EVENT_DETECTION",
    "FEATURE_EXTRACTION",
    "BASELINE_REFERENCE",
    "ANOMALY_EVALUATION",
    "PERSISTENCE",
    "CROSS_SENSOR_CORRELATION",
    "HEALTH_AND_ALERT",
];

export function createDefaultStages(): Record<number, LiveStageInfo> {
    const map: Record<number, LiveStageInfo> = {};
    STAGE_NAMES.forEach((stage, idx) => {
        const id = idx + 1;
        map[id] = {
            id,
            stage,
            status: "pending",
            summary: null,
            timestamp: null,
        };
    });
    return map;
}

// Stage dwell timings for human-readable presentation (~350–500ms per stage, ~3.7s total)
// Split into start phase (processing dot) and completed phase (green check with evidence summary)
const STAGE_DWELL_MS: Record<number, { startMs: number; completeMs: number }> = {
    1: { startMs: 120, completeMs: 280 }, // INGESTION: 400ms
    2: { startMs: 120, completeMs: 280 }, // CONDITIONING: 400ms
    3: { startMs: 130, completeMs: 320 }, // EVENT_DETECTION: 450ms
    4: { startMs: 120, completeMs: 280 }, // FEATURE_EXTRACTION: 400ms
    5: { startMs: 100, completeMs: 250 }, // BASELINE_REFERENCE: 350ms
    6: { startMs: 130, completeMs: 320 }, // ANOMALY_EVALUATION: 450ms
    7: { startMs: 120, completeMs: 280 }, // PERSISTENCE: 400ms
    8: { startMs: 120, completeMs: 280 }, // CROSS_SENSOR_CORRELATION: 400ms
    9: { startMs: 180, completeMs: 420 }, // HEALTH_AND_ALERT: 600ms
};

interface QueuedStageData {
    startedEvent?: LiveProcessingEvent;
    completedEvent?: LiveProcessingEvent;
    errorEvent?: LiveProcessingEvent;
}

interface QueuedRun {
    runId: string;
    sensorId?: string | null;
    zoneId?: number | null;
    zoneName?: string | null;
    sequence?: number | null;
    startedTimestamp?: string | null;
    completedTimestamp?: string | null;
    backendDurationMs: number | null;
    stages: Record<number, QueuedStageData>;
    completionEvent?: LiveProcessingEvent | null;
    errorEvent?: LiveProcessingEvent | null;
    isBackendCompleted: boolean;
    hasBackendError: boolean;
    errorMessage?: string | null;
}

interface UseLiveTelemetryOptions {
    enabled?: boolean;
    endpoint?: string;
    onCompleted?: (traceId: string, eventId?: number | null) => void;
}

export function useLiveTelemetry({
    enabled = true,
    endpoint,
    onCompleted,
}: UseLiveTelemetryOptions = {}) {
    const [connectionState, setConnectionState] = useState<LiveConnectionState>("CONNECTING");
    const [activeStage, setActiveStage] = useState<number | null>(null);
    const [stageStatuses, setStageStatuses] = useState<Record<number, LiveStageInfo>>(createDefaultStages());
    const [lastCompletedTraceId, setLastCompletedTraceId] = useState<string | null>(null);
    const [activeRunId, setActiveRunId] = useState<string | null>(null);
    const [latestEvent, setLatestEvent] = useState<LiveProcessingEvent | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null);
    const [backendDurationMs, setBackendDurationMs] = useState<number | null>(null);
    const [isPlaybackActive, setIsPlaybackActive] = useState<boolean>(false);
    const [queueDepth, setQueueDepth] = useState<number>(0);

    const eventSourceRef = useRef<EventSource | null>(null);
    const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
    const retryCountRef = useRef<number>(0);
    const isUnmountedRef = useRef<boolean>(false);

    // Presentation queue refs
    const activeRunRef = useRef<QueuedRun | null>(null);
    const pendingRunRef = useRef<QueuedRun | null>(null);
    const isPlaybackActiveRef = useRef<boolean>(false);
    const playbackTimerRef = useRef<NodeJS.Timeout | null>(null);
    const currentStageIndexRef = useRef<number>(1);
    const prefersReducedMotionRef = useRef<boolean>(false);

    // Check reduced-motion preference
    useEffect(() => {
        if (typeof window === "undefined") return;
        const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
        prefersReducedMotionRef.current = mediaQuery.matches;
        const handler = (e: MediaQueryListEvent) => {
            prefersReducedMotionRef.current = e.matches;
        };
        mediaQuery.addEventListener?.("change", handler);
        return () => mediaQuery.removeEventListener?.("change", handler);
    }, []);

    // Resolve URL without hardcoding
    const sseUrl = endpoint || (
        typeof window !== "undefined"
            ? (process.env.NEXT_PUBLIC_API_BASE_URL
                ? `${process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/+$/, "")}/telemetry/live`
                : "/api/v1/telemetry/live")
            : "/api/v1/telemetry/live"
    );

    const clearPlaybackTimers = useCallback(() => {
        if (playbackTimerRef.current) {
            clearTimeout(playbackTimerRef.current);
            playbackTimerRef.current = null;
        }
    }, []);

    const cleanup = useCallback(() => {
        clearPlaybackTimers();
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        isPlaybackActiveRef.current = false;
        activeRunRef.current = null;
        pendingRunRef.current = null;
        setIsPlaybackActive(false);
        setQueueDepth(0);
    }, [clearPlaybackTimers]);

    // Forward declaration of playStage function ref
    const playStageRef = useRef<((stageIdx: number) => void) | null>(null);

    const finishRun = useCallback((run: QueuedRun) => {
        setConnectionState("COMPLETED");
        setActiveStage(null);
        setBackendDurationMs(run.backendDurationMs);
        if (run.completionEvent) {
            setLatestEvent(run.completionEvent);
        }

        const finalTraceId = run.completionEvent?.trace_id || run.runId;
        const finalEventId = run.completionEvent?.event_id;
        setLastCompletedTraceId(finalTraceId);

        // Authoritative completed trace handoff!
        if (onCompleted) {
            onCompleted(finalTraceId, finalEventId);
        }

        // Dwell briefly in completed state (500ms) before checking for a pending run
        playbackTimerRef.current = setTimeout(() => {
            if (isUnmountedRef.current) return;

            if (pendingRunRef.current) {
                const nextRun = pendingRunRef.current;
                pendingRunRef.current = null;
                setQueueDepth(0);
                activeRunRef.current = nextRun;
                setActiveRunId(nextRun.runId);
                setConnectionState("PROCESSING");
                setStageStatuses(createDefaultStages());
                currentStageIndexRef.current = 1;
                playStageRef.current?.(1);
            } else {
                isPlaybackActiveRef.current = false;
                setIsPlaybackActive(false);
                activeRunRef.current = null;
                setActiveStage(null);
                setConnectionState("CONNECTED");
            }
        }, 500);
    }, [onCompleted]);

    const handleRunError = useCallback((run: QueuedRun, stageIdx?: number) => {
        setConnectionState("ERROR");
        const errMsg = run.errorMessage || run.errorEvent?.error_message || "Pipeline processing error";
        setErrorMessage(errMsg);

        const errStage = stageIdx || (run.errorEvent?.stage_index ?? (run.errorEvent?.stage ? STAGE_NAMES.indexOf(run.errorEvent.stage) + 1 : 1));
        if (errStage) {
            setStageStatuses((prev) => ({
                ...prev,
                [errStage]: {
                    ...prev[errStage],
                    status: "error",
                    summary: errMsg,
                },
            }));
        }

        isPlaybackActiveRef.current = false;
        setIsPlaybackActive(false);
        activeRunRef.current = null;
    }, []);

    // Playback state machine: advances sequentially through received stages
    const playStage = useCallback((stageIdx: number) => {
        if (isUnmountedRef.current) return;

        const currentRun = activeRunRef.current;
        if (!currentRun) {
            isPlaybackActiveRef.current = false;
            setIsPlaybackActive(false);
            setActiveStage(null);
            return;
        }

        // When all 9 stages have dwelled and completed:
        if (stageIdx > 9) {
            if (currentRun.isBackendCompleted || currentRun.stages[9]?.completedEvent) {
                finishRun(currentRun);
            } else if (currentRun.hasBackendError) {
                handleRunError(currentRun);
            } else {
                // Safety timeout: finalize run if stage 9 completed
                playbackTimerRef.current = setTimeout(() => {
                    finishRun(currentRun);
                }, 400);
            }
            return;
        }

        currentStageIndexRef.current = stageIdx;
        const stageData = currentRun.stages[stageIdx];

        // Check if an error occurred at or before this stage
        if (stageData?.errorEvent || (currentRun.hasBackendError && !stageData?.completedEvent)) {
            handleRunError(currentRun, stageIdx);
            return;
        }

        // Check if the real stage event has arrived from SSE
        // Do NOT advance or fabricate stages if the backend has not yet reached this stage!
        if (!stageData?.startedEvent && !stageData?.completedEvent) {
            playbackTimerRef.current = setTimeout(() => {
                playStage(stageIdx);
            }, 50);
            return;
        }

        const dwell = STAGE_DWELL_MS[stageIdx] || { startMs: 120, completeMs: 280 };
        const motionMultiplier = prefersReducedMotionRef.current ? 0.35 : 1.0;
        const startMs = Math.round(dwell.startMs * motionMultiplier);
        const completeMs = Math.round(dwell.completeMs * motionMultiplier);

        // Phase 1: Stage Processing (amber active dot)
        setActiveStage(stageIdx);
        setStageStatuses((prev) => ({
            ...prev,
            [stageIdx]: {
                ...prev[stageIdx],
                status: "processing",
                timestamp: stageData.startedEvent?.timestamp || stageData.completedEvent?.timestamp || new Date().toISOString(),
            },
        }));

        if (stageData.startedEvent) {
            setLatestEvent(stageData.startedEvent);
        }

        // Schedule Phase 2: Stage Completed (green checkmark + evidence summary)
        playbackTimerRef.current = setTimeout(() => {
            if (isUnmountedRef.current) return;

            let attempts = 0;
            const checkCompletion = () => {
                if (isUnmountedRef.current) return;
                attempts += 1;
                const updatedRun = activeRunRef.current;
                const updatedStage = updatedRun?.stages[stageIdx];

                if (updatedStage?.completedEvent) {
                    setStageStatuses((prev) => ({
                        ...prev,
                        [stageIdx]: {
                            ...prev[stageIdx],
                            status: "completed",
                            summary: updatedStage.completedEvent?.summary || prev[stageIdx]?.summary,
                            timestamp: updatedStage.completedEvent?.timestamp || new Date().toISOString(),
                        },
                    }));

                    setLatestEvent(updatedStage.completedEvent);

                    // Dwell on the completed stage so human can read the evidence summary
                    playbackTimerRef.current = setTimeout(() => {
                        if (isUnmountedRef.current) return;
                        playStage(stageIdx + 1);
                    }, completeMs);
                } else if (updatedRun?.hasBackendError) {
                    handleRunError(updatedRun, stageIdx);
                } else if (updatedRun?.isBackendCompleted || attempts >= 20) {
                    // Fallback: If backend is completed or after 1000ms, mark completed and advance
                    setStageStatuses((prev) => ({
                        ...prev,
                        [stageIdx]: {
                            ...prev[stageIdx],
                            status: "completed",
                            summary: prev[stageIdx]?.summary || (updatedRun?.isBackendCompleted ? "Completed" : "Stage timeout"),
                            timestamp: new Date().toISOString(),
                        },
                    }));
                    playbackTimerRef.current = setTimeout(() => {
                        if (isUnmountedRef.current) return;
                        playStage(stageIdx + 1);
                    }, completeMs);
                } else {
                    // Wait briefly for completion event if still in transit
                    playbackTimerRef.current = setTimeout(checkCompletion, 50);
                }
            };

            checkCompletion();
        }, startMs);
    }, [finishRun, handleRunError]);

    // Keep playStageRef updated
    useEffect(() => {
        playStageRef.current = playStage;
    }, [playStage]);

    // Helper to find or associate target run
    const findTargetRun = useCallback((traceId?: string | null, sequence?: number | null, sensorId?: string | null): QueuedRun | null => {
        if (activeRunRef.current) {
            if (!traceId || activeRunRef.current.runId === traceId) {
                return activeRunRef.current;
            }
            if (sequence !== undefined && sequence !== null && activeRunRef.current.sequence === sequence) {
                return activeRunRef.current;
            }
            if (sensorId && activeRunRef.current.sensorId === sensorId) {
                return activeRunRef.current;
            }
        }
        if (pendingRunRef.current) {
            if (!traceId || pendingRunRef.current.runId === traceId) {
                return pendingRunRef.current;
            }
            if (sequence !== undefined && sequence !== null && pendingRunRef.current.sequence === sequence) {
                return pendingRunRef.current;
            }
        }
        return activeRunRef.current || pendingRunRef.current;
    }, []);

    // Skip playback button handler
    const skipPlayback = useCallback(() => {
        clearPlaybackTimers();
        const currentRun = activeRunRef.current;
        if (!currentRun) return;

        // Immediately mark all received stages as completed
        setStageStatuses((prev) => {
            const next = { ...prev };
            for (let i = 1; i <= 9; i++) {
                const st = currentRun.stages[i];
                if (st?.completedEvent) {
                    next[i] = {
                        id: i,
                        stage: STAGE_NAMES[i - 1],
                        status: "completed",
                        summary: st.completedEvent.summary || next[i]?.summary,
                        timestamp: st.completedEvent.timestamp,
                    };
                }
            }
            return next;
        });

        if (currentRun.isBackendCompleted) {
            finishRun(currentRun);
        }
    }, [clearPlaybackTimers, finishRun]);

    const connect = useCallback(() => {
        if (!enabled || isUnmountedRef.current) return;
        cleanup();

        setConnectionState((prev) => (prev === "DISCONNECTED" ? "CONNECTING" : prev === "CONNECTED" ? "CONNECTED" : "CONNECTING"));
        setErrorMessage(null);

        try {
            const es = new EventSource(sseUrl);
            eventSourceRef.current = es;

            es.onopen = () => {
                if (isUnmountedRef.current) return;
                retryCountRef.current = 0;
                setConnectionState((prev) => (prev === "PROCESSING" ? "PROCESSING" : "CONNECTED"));
            };

            es.onmessage = (rawMessage) => {
                if (isUnmountedRef.current) return;
                try {
                    const event: LiveProcessingEvent = JSON.parse(rawMessage.data);

                    switch (event.type) {
                        case "heartbeat": {
                            setLastHeartbeat(event.timestamp);
                            setConnectionState((prev) => (prev === "CONNECTING" || prev === "RECONNECTING" ? "CONNECTED" : prev));
                            break;
                        }

                        case "processing_started": {
                            const runId = event.trace_id || (event.sequence ? `seq-${event.sequence}` : `run-${Date.now()}`);
                            const newRun: QueuedRun = {
                                runId,
                                sensorId: event.sensor_id,
                                zoneId: event.zone_id,
                                zoneName: event.zone_name,
                                sequence: event.sequence,
                                startedTimestamp: event.timestamp,
                                completedTimestamp: null,
                                backendDurationMs: null,
                                stages: {},
                                isBackendCompleted: false,
                                hasBackendError: false,
                            };

                            if (!isPlaybackActiveRef.current) {
                                // Start presentation playback for this run immediately
                                activeRunRef.current = newRun;
                                isPlaybackActiveRef.current = true;
                                setIsPlaybackActive(true);
                                setActiveRunId(newRun.runId);
                                setConnectionState("PROCESSING");
                                setStageStatuses(createDefaultStages());
                                currentStageIndexRef.current = 1;
                                playStageRef.current?.(1);
                            } else {
                                // An earlier run is actively dwelling in playback:
                                // Queue this newest run as pending (supersedes any older unplayed pending run)
                                pendingRunRef.current = newRun;
                                setQueueDepth(1);
                            }
                            break;
                        }

                        case "stage_started": {
                            const stageIdx = event.stage_index ?? (event.stage ? STAGE_NAMES.indexOf(event.stage) + 1 : null);
                            if (stageIdx) {
                                const targetRun = findTargetRun(event.trace_id, event.sequence, event.sensor_id);
                                if (targetRun) {
                                    if (!targetRun.stages[stageIdx]) {
                                        targetRun.stages[stageIdx] = {};
                                    }
                                    targetRun.stages[stageIdx].startedEvent = event;
                                }
                            }
                            break;
                        }

                        case "stage_completed": {
                            const stageIdx = event.stage_index ?? (event.stage ? STAGE_NAMES.indexOf(event.stage) + 1 : null);
                            if (stageIdx) {
                                const targetRun = findTargetRun(event.trace_id, event.sequence, event.sensor_id);
                                if (targetRun) {
                                    if (!targetRun.stages[stageIdx]) {
                                        targetRun.stages[stageIdx] = {};
                                    }
                                    targetRun.stages[stageIdx].completedEvent = event;
                                }
                            }
                            break;
                        }

                        case "processing_completed": {
                            const targetRun = findTargetRun(event.trace_id, event.sequence, event.sensor_id);
                            if (targetRun) {
                                targetRun.isBackendCompleted = true;
                                targetRun.completedTimestamp = event.timestamp;
                                targetRun.completionEvent = event;

                                // Compute real backend execution time from real timestamps
                                if (event.duration_ms !== null && event.duration_ms !== undefined) {
                                    targetRun.backendDurationMs = Math.round(event.duration_ms);
                                } else if (targetRun.startedTimestamp) {
                                    const startMs = new Date(targetRun.startedTimestamp).getTime();
                                    const endMs = new Date(event.timestamp).getTime();
                                    const diff = endMs - startMs;
                                    targetRun.backendDurationMs = diff >= 0 ? diff : null;
                                }
                            }
                            break;
                        }

                        case "processing_error": {
                            const targetRun = findTargetRun(event.trace_id, event.sequence, event.sensor_id);
                            if (targetRun) {
                                targetRun.hasBackendError = true;
                                targetRun.errorEvent = event;
                                targetRun.errorMessage = event.error_message || event.summary || "Pipeline processing error";
                                const stageIdx = event.stage_index ?? (event.stage ? STAGE_NAMES.indexOf(event.stage) + 1 : null);
                                if (stageIdx) {
                                    if (!targetRun.stages[stageIdx]) targetRun.stages[stageIdx] = {};
                                    targetRun.stages[stageIdx].errorEvent = event;
                                }
                            }
                            break;
                        }

                        default:
                            break;
                    }
                } catch (parseErr) {
                    console.warn("[LiveTelemetry] Failed to parse live SSE event:", parseErr);
                }
            };

            es.onerror = () => {
                if (isUnmountedRef.current) return;
                cleanup();

                // Compute exponential backoff delay (1s, 2s, 4s, 8s, max 10s)
                const retryCount = retryCountRef.current;
                const delayMs = Math.min(1000 * Math.pow(2, retryCount), 10000);
                retryCountRef.current += 1;

                setConnectionState("RECONNECTING");
                reconnectTimerRef.current = setTimeout(() => {
                    if (!isUnmountedRef.current) {
                        connect();
                    }
                }, delayMs);
            };
        } catch (err: any) {
            setConnectionState("ERROR");
            setErrorMessage(err.message || "Failed to initialize SSE connection");
        }
    }, [enabled, sseUrl, cleanup, findTargetRun]);

    useEffect(() => {
        isUnmountedRef.current = false;
        if (enabled) {
            connect();
        } else {
            cleanup();
            setConnectionState("DISCONNECTED");
        }

        return () => {
            isUnmountedRef.current = true;
            cleanup();
        };
    }, [enabled, connect, cleanup]);

    const manualReconnect = useCallback(() => {
        retryCountRef.current = 0;
        connect();
    }, [connect]);

    const disconnect = useCallback(() => {
        cleanup();
        setConnectionState("DISCONNECTED");
    }, [cleanup]);

    return {
        connectionState,
        activeStage,
        stageStatuses,
        lastCompletedTraceId,
        activeRunId,
        latestEvent,
        errorMessage,
        lastHeartbeat,
        backendDurationMs,
        isPlaybackActive,
        queueDepth,
        skipPlayback,
        reconnect: manualReconnect,
        disconnect,
    };
}
