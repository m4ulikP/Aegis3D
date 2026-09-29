# Aegis3D Sample API Responses

This directory contains representative JSON sample responses for all frontend-consumable endpoints.

## Response Files Overview

| File | Associated Endpoint | Status | Description |
| :--- | :--- | :--- | :--- |
| `zones.json` | `GET /api/v1/zones` | Schema-Derived | List of monitoring zones (`ZoneResponse[]`) |
| `zone-detail.json` | `GET /api/v1/zones/{zone_id}` | Schema-Derived | Zone detail with event and alert counts (`ZoneDetailResponse`) |
| `zone-events.json` | `GET /api/v1/zones/{zone_id}/events` | Schema-Derived | List of structural observation events (`EventResponse[]`) |
| `zone-health.json` | `GET /api/v1/zones/{zone_id}/health` | Schema-Derived | Structural Health Indicator (SHI) score, status, evidence payload, and disclaimer (`ZoneHealthResponse`) |
| `zone-trend.json` | `GET /api/v1/zones/{zone_id}/trend` | Schema-Derived | Directional trend analysis sub-period breakdown (`ZoneTrendResponse`) |
| `zone-correlation.json` | `GET /api/v1/zones/{zone_id}/correlation` | Schema-Derived | Temporal persistence & 2-PZT cross-sensor correlation groups (`ZoneCorrelationResponse`) |
| `alerts.json` | `GET /api/v1/alerts` | Schema-Derived | List of actionable system alerts (`AlertResponse[]`) |
| `health-summary.json` | `GET /api/v1/health/summary` | Schema-Derived | Dashboard-level aggregate health summary (`HealthSummaryResponse`) |
| `event-create-response.json` | `POST /api/v1/events` | Schema-Derived | Created event response (`EventResponse`) |

## Generation Note

These sample JSON files were generated using the **actual Pydantic v2 schemas** in `backend/app/schemas/` to ensure exact field key, data type, timestamp format (ISO-8601 UTC), and enum value alignment.

When the backend API server is running locally with a seeded PostgreSQL database (`docker compose up -d postgres`), live API responses will match these exact JSON structures.
