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
