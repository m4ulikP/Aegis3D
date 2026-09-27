import {
    AlertResponse,
    EventResponse,
    HealthSummaryResponse,
    ZoneCorrelationResponse,
    ZoneDetailResponse,
    ZoneHealthResponse,
    ZoneResponse,
    ZoneTrendResponse,
} from "@/types/api";

const API_BASE = "/api/v1";

async function apiFetch<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options?.headers || {}),
        },
    });

    if (!response.ok) {
        let message = `API request failed: ${response.status}`;

        try {
            const error = await response.json();
            if (error?.detail) {
                message = error.detail;
            }
        } catch {
            // Keep the default error message.
        }

        throw new Error(message);
    }

    return response.json();
}

export const api = {
    getHealthSummary: (): Promise<HealthSummaryResponse> =>
        apiFetch<HealthSummaryResponse>("/health/summary"),

    getZones: (): Promise<ZoneResponse[]> =>
        apiFetch<ZoneResponse[]>("/zones"),

    getZone: (zoneId: number): Promise<ZoneDetailResponse> =>
        apiFetch<ZoneDetailResponse>(`/zones/${zoneId}`),

    getZoneHealth: (zoneId: number): Promise<ZoneHealthResponse> =>
        apiFetch<ZoneHealthResponse>(`/zones/${zoneId}/health`),

    getZoneTrend: (zoneId: number): Promise<ZoneTrendResponse> =>
        apiFetch<ZoneTrendResponse>(`/zones/${zoneId}/trend`),

    getZoneCorrelation: (zoneId: number): Promise<ZoneCorrelationResponse> =>
        apiFetch<ZoneCorrelationResponse>(`/zones/${zoneId}/correlation`),

    getZoneEvents: (zoneId: number): Promise<EventResponse[]> =>
        apiFetch<EventResponse[]>(`/zones/${zoneId}/events`),

    getAlerts: (): Promise<AlertResponse[]> =>
        apiFetch<AlertResponse[]>("/alerts"),
};