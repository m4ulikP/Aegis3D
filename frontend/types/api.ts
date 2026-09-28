export type HealthStatus = "NORMAL" | "MONITOR" | "INSPECTION_ADVISED" | "HIGH_PRIORITY_INSPECTION";
export type HealthTrend = "STABLE" | "INCREASING" | "DECREASING";
export type AlertSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";
export type EventSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type EventStatus = "DETECTED" | "REVIEWED" | "DISMISSED";
export type EventSourceType = "SIMULATOR" | "SENSOR" | "IMPORTED";

export interface HealthSummaryResponse {
    total_zones: number;
    health_status_counts: Record<string, number>;
    active_alerts_count: number;
    recent_events_count: number;
    latest_timestamp?: string | null;
}

export interface ZoneResponse {
    id: number;
    name: string;
    floor?: string | null;
    description?: string | null;
    created_at: string;
}

export interface ZoneDetailResponse {
    id: number;
    name: string;
    floor?: string | null;
    description?: string | null;
    created_at: string;
    event_count: number;
    active_alert_count: number;
    latest_health_status?: HealthStatus | null;
}

export interface ZoneHealthResponse {
    zone_id: number;
    score: number;
    status: HealthStatus;
    trend: HealthTrend;
    reason: string;
    timestamp: string;
    evidence?: Record<string, any> | null;
    disclaimer: string;
}

export interface AlertResponse {
    id: number;
    health_snapshot_id: number;
    zone_id: number;
    timestamp: string;
    severity: AlertSeverity;
    title: string;
    message: string;
    status: AlertStatus;
    acknowledged_at?: string | null;
    resolved_at?: string | null;
}

export interface EventResponse {
    id: number;
    session_id: number;
    zone_id: number;
    source_type: EventSourceType;
    source_id: string;
    correlation_id?: string | null;
    timestamp: string;
    magnitude?: number | null;
    energy?: number | null;
    duration_ms?: number | null;
    frequency_hz?: number | null;
    severity: EventSeverity;
    status: EventStatus;
    metadata?: Record<string, any> | null;
}

export interface ZoneTrendResponse {
    zone_id: number;
    overall_trend_direction: string;
    period_comparison_note: string;
}

export interface ZoneCorrelationResponse {
    zone_id: number;
    is_persistent: boolean;
    anomalous_events_count: number;
    total_events_count: number;
    correlated_groups: any[];
}

export interface TelemetryEventResult {
    event_id: number;
    magnitude: number;
    energy: number;
    duration_ms: number;
    frequency_hz?: number | null;
    severity: EventSeverity;
    is_anomalous: boolean;
    magnitude_z_score?: number | null;
    energy_z_score?: number | null;
    anomaly_reasons?: string[];
}

export interface ExtractedFeaturesSchema {
    peak_amplitude: number;
    rms_amplitude: number;
    energy: number;
    duration_ms: number;
    frequency_hz?: number | null;
    sample_count: number;
}

export interface TelemetryLatestResponse {
    status: string;
    telemetry_accepted: boolean;
    sensor_id: string;
    zone_id: number;
    zone_name: string;
    timestamp: string;
    samples_count: number;
    sample_rate_hz: number;
    sequence?: number | null;
    samples?: number[];
    detection_threshold?: number | null;
    events_detected: number;
    events: TelemetryEventResult[];
    extracted_features?: ExtractedFeaturesSchema | null;
    temporal_persistence_confirmed?: boolean | null;
    cross_sensor_correlation_confirmed?: boolean | null;
    health_score?: number | null;
    health_status?: HealthStatus | null;
    health_trend?: string | null;
    alert_generated: boolean;
    alert_id?: number | null;
    alert_severity?: AlertSeverity | null;
    alert_title?: string | null;
    message: string;
}

export interface TelemetryIngestRequest {
    sensor_id: string;
    zone_name: string;
    timestamp?: string;
    sample_rate_hz: number;
    sequence?: number;
    samples: number[];
    detection_threshold?: number;
    session_id?: number;
}

export interface TraceMetadata {
    trace_id: string;
    event_id?: number | null;
    sensor_id: string;
    zone_id: number;
    zone_name: string;
    timestamp: string;
    sequence?: number | null;
    sample_rate_hz: number;
    samples_count: number;
    session_id?: number | null;
}

export interface RawTelemetryTrace {
    sensor_id: string;
    zone_name: string;
    timestamp: string;
    sample_rate_hz: number;
    samples_count: number;
    sequence?: number | null;
    samples_bounded: number[];
    peak_amplitude: number;
    rms_amplitude: number;
    is_bounded: boolean;
}

export interface ConditioningTrace {
    dc_removal_applied: boolean;
    dc_offset_removed?: number | null;
    filter_applied: boolean;
    filter_type?: string | null;
    filter_window_size?: number | null;
    conditioned_samples_bounded?: number[] | null;
}

export interface DetectedWindowTrace {
    start_index: number;
    end_index: number;
    start_time_ms: number;
    end_time_ms: number;
    duration_ms: number;
    peak_amplitude: number;
    rms_amplitude: number;
    sample_count: number;
}

export interface EventDetectionTrace {
    detection_threshold: number;
    events_detected_count: number;
    events_detected: boolean;
    min_duration_samples: number;
    merge_gap_samples: number;
    detected_windows: DetectedWindowTrace[];
}

export interface FeatureExtractionTrace {
    event_id?: number | null;
    peak_amplitude?: number | null;
    rms_amplitude?: number | null;
    energy?: number | null;
    duration_ms?: number | null;
    frequency_hz?: number | null;
    sample_count?: number | null;
    features_dict: Record<string, any>;
}

export interface BaselineTrace {
    baseline_id?: number | null;
    zone_id: number;
    mean_magnitude?: number | null;
    std_magnitude?: number | null;
    mean_energy?: number | null;
    std_energy?: number | null;
    normal_event_rate?: number | null;
    valid_from?: string | null;
    valid_until?: string | null;
    baseline_available: boolean;
}

export interface AnomalyEvaluationTrace {
    evaluated: boolean;
    is_anomalous: boolean;
    magnitude_z_score?: number | null;
    energy_z_score?: number | null;
    magnitude_anomalous?: boolean | null;
    energy_anomalous?: boolean | null;
    z_threshold: number;
    severity?: EventSeverity | null;
    reasons: string[];
}

export interface PersistenceTrace {
    evaluated: boolean;
    is_persistent: boolean;
    total_events_in_window: number;
    anomalous_events_in_window: number;
    anomaly_ratio: number;
    max_consecutive_anomalies: number;
    window_duration_seconds: number;
    min_anomaly_count_required: number;
    min_anomaly_ratio_required: number;
    reasons: string[];
}

export interface CorrelationTrace {
    evaluated: boolean;
    is_cross_sensor_correlated: boolean;
    correlated_group_id?: string | null;
    participating_sensors: string[];
    event_ids: number[];
    temporal_spread_ms?: number | null;
    tolerance_seconds: number;
    relative_source_hint?: string | null;
    reasons: string[];
}

export interface TrendTrace {
    evaluated: boolean;
    overall_trend?: string | null;
    rate_delta?: number | null;
    magnitude_delta?: number | null;
    earlier_period_events?: number | null;
    later_period_events?: number | null;
    earlier_period_anomaly_rate?: number | null;
    later_period_anomaly_rate?: number | null;
    reasons: string[];
}

export interface HealthTrace {
    evaluated: boolean;
    health_score?: number | null;
    health_status?: HealthStatus | null;
    trend?: string | null;
    deductions?: Record<string, number> | null;
    reason?: string | null;
    evidence_summary: string[];
    disclaimer: string;
}

export interface AlertTrace {
    alert_generated: boolean;
    alert_id?: number | null;
    alert_severity?: AlertSeverity | null;
    alert_status?: AlertStatus | null;
    alert_title?: string | null;
    alert_message?: string | null;
    timestamp?: string | null;
}

export interface ProcessingTraceResponse {
    metadata: TraceMetadata;
    ingestion: RawTelemetryTrace;
    conditioning: ConditioningTrace;
    event_detection: EventDetectionTrace;
    features?: FeatureExtractionTrace | null;
    baseline: BaselineTrace;
    anomaly: AnomalyEvaluationTrace;
    persistence: PersistenceTrace;
    correlation: CorrelationTrace;
    trend: TrendTrace;
    health: HealthTrace;
    alert: AlertTrace;
}
