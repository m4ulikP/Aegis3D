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
    getHealthSummary: () =>
        apiFetch("/health/summary"),

    getZones: () =>
        apiFetch("/zones"),

    getZone: (zoneId: number) =>
        apiFetch(`/zones/${zoneId}`),

    getZoneHealth: (zoneId: number) =>
        apiFetch(`/zones/${zoneId}/health`),

    getZoneTrend: (zoneId: number) =>
        apiFetch(`/zones/${zoneId}/trend`),

    getZoneCorrelation: (zoneId: number) =>
        apiFetch(`/zones/${zoneId}/correlation`),

    getZoneEvents: (zoneId: number) =>
        apiFetch(`/zones/${zoneId}/events`),

    getAlerts: () =>
        apiFetch("/alerts"),
};