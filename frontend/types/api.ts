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
    events_detected: number;
    events: Array<{
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
    }>;
    extracted_features?: {
        peak_amplitude: number;
        rms_amplitude: number;
        energy: number;
        duration_ms: number;
        frequency_hz?: number | null;
        sample_count: number;
    } | null;
    temporal_persistence_confirmed?: boolean | null;
    cross_sensor_correlation_confirmed?: boolean | null;
    health_score?: number | null;
    health_status?: HealthStatus | null;
    health_trend?: string | null;
    alert_generated: boolean;
    alert_id?: number | null;
    alert_severity?: AlertSeverity | null;
    alert_title?: string | null;
    detection_threshold?: number | null;
    message: string;
}

