# Aegis3D Frontend API Contract Document

This document defines the REST API contract exposed by the Aegis3D FastAPI backend for consumption by the Next.js frontend application shell.

---

## Global Technical Specifications

- **Base URL**: `http://localhost:8000/api/v1`
- **Data Format**: `application/json`
- **Timestamp Format**: ISO-8601 UTC strings (e.g., `2026-09-27T15:00:00.000Z` or `2026-09-27T15:00:00+00:00`)
- **Authentication**: None required in current backend implementation
- **CORS**: Not enabled in backend yet (Frontend dev server proxy or browser workaround recommended during development)
- **OpenAPI Document**: `backend-frontend-handoff/openapi.json` or `http://localhost:8000/openapi.json`

---

## Endpoint Contracts

### 1. `GET /api/v1/zones`
Return all structural monitoring zones.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/zones`
- **Path Parameters**: None
- **Query Parameters**: None
- **Request Body**: None
- **Response Schema**: `ZoneResponse[]`
  - `id`: `integer` (Primary Key ID)
  - `name`: `string` (Zone name)
  - `floor`: `string | null` (Floor designation, e.g. "Floor 1")
  - `description`: `string | null` (Optional description)
  - `created_at`: `string` (ISO-8601 UTC timestamp)
- **Status Codes**: `200 OK`
- **Sample Response**: `sample-responses/zones.json`

---

### 2. `GET /api/v1/zones/{zone_id}`
Return a specific zone and its monitoring metadata.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/zones/{zone_id}`
- **Path Parameters**:
  - `zone_id`: `integer` (required, ge=1)
- **Query Parameters**: None
- **Request Body**: None
- **Response Schema**: `ZoneDetailResponse`
  - `id`: `integer`
  - `name`: `string`
  - `floor`: `string | null`
  - `description`: `string | null`
  - `created_at`: `string` (ISO-8601 UTC)
  - `event_count`: `integer` (Total events recorded in zone)
  - `active_alert_count`: `integer` (Count of ACTIVE alerts in zone)
  - `latest_health_status`: `string | null` (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`)
- **Status Codes**:
  - `200 OK`: Success
  - `404 Not Found`: If `zone_id` does not exist (`detail: "Zone with id {zone_id} not found"`)
- **Sample Response**: `sample-responses/zone-detail.json`

---

### 3. `GET /api/v1/zones/{zone_id}/events`
Return event observations associated with a zone.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/zones/{zone_id}/events`
- **Path Parameters**:
  - `zone_id`: `integer` (required, ge=1)
- **Query Parameters**:
  - `limit`: `integer` (optional, default: 50, min: 1, max: 500)
  - `start_time`: `string` (optional, ISO-8601 UTC timestamp filter)
  - `end_time`: `string` (optional, ISO-8601 UTC timestamp filter)
  - `severity`: `string` (optional, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `status`: `string` (optional, `DETECTED`, `REVIEWED`, `DISMISSED`)
- **Request Body**: None
- **Response Schema**: `EventResponse[]`
  - `id`: `integer`
  - `session_id`: `integer`
  - `zone_id`: `integer`
  - `source_type`: `string` (`SIMULATOR`, `SENSOR`, `IMPORTED`)
  - `source_id`: `string` (e.g. "PZT-01")
  - `correlation_id`: `string | null`
  - `timestamp`: `string` (ISO-8601 UTC)
  - `magnitude`: `number | null`
  - `energy`: `number | null`
  - `duration_ms`: `number | null`
  - `frequency_hz`: `number | null`
  - `severity`: `string` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `status`: `string` (`DETECTED`, `REVIEWED`, `DISMISSED`)
  - `metadata`: `object | null`
- **Status Codes**:
  - `200 OK`: Success
  - `404 Not Found`: If `zone_id` does not exist
- **Sample Response**: `sample-responses/zone-events.json`

---

### 4. `GET /api/v1/zones/{zone_id}/health`
Return the current Structural Health Indicator (SHI) for a zone.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/zones/{zone_id}/health`
- **Path Parameters**:
  - `zone_id`: `integer` (required, ge=1)
- **Query Parameters**:
  - `reference_time`: `string` (optional, ISO-8601 UTC timestamp reference)
  - `window_duration_seconds`: `number` (optional, default: 3600.0, min: 60.0, max: 86400.0)
- **Request Body**: None
- **Response Schema**: `ZoneHealthResponse`
  - `zone_id`: `integer`
  - `score`: `number` (0.0 to 100.0)
  - `status`: `string` (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`)
  - `trend`: `string` (`STABLE`, `INCREASING`, `DECREASING`)
  - `reason`: `string` (Explainable text summary)
  - `timestamp`: `string` (ISO-8601 UTC)
  - `evidence`: `object | null` (Itemized score deductions and counts)
  - `disclaimer`: `string` (Mandatory safety disclaimer text)
- **Status Codes**:
  - `200 OK`: Success
  - `404 Not Found`: If `zone_id` does not exist
- **Sample Response**: `sample-responses/zone-health.json`

---

### 5. `GET /api/v1/zones/{zone_id}/trend`
Expose deterministic sub-period trend analysis for a zone.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/zones/{zone_id}/trend`
- **Path Parameters**:
  - `zone_id`: `integer` (required, ge=1)
- **Query Parameters**:
  - `reference_time`: `string` (optional, ISO-8601 UTC timestamp reference)
  - `analysis_window_seconds`: `number` (optional, default: 3600.0, min: 60.0, max: 86400.0)
- **Request Body**: None
- **Response Schema**: `ZoneTrendResponse`
  - `zone_id`: `integer`
  - `overall_trend_direction`: `string` (`STABLE`, `INCREASING`, `DECREASING`, `INSUFFICIENT_DATA`)
  - `event_rate_change_ratio`: `number`
  - `magnitude_delta`: `number`
  - `is_statistically_significant`: `boolean`
  - `reason`: `string`
  - `earlier_period`: `PeriodMetricsSchema` (`total_events`, `anomalous_events`, `anomaly_rate`, `mean_magnitude`, `persistent_anomaly_count`, `cross_sensor_event_count`)
  - `later_period`: `PeriodMetricsSchema` (`total_events`, `anomalous_events`, `anomaly_rate`, `mean_magnitude`, `persistent_anomaly_count`, `cross_sensor_event_count`)
- **Status Codes**:
  - `200 OK`: Success
  - `404 Not Found`: If `zone_id` does not exist
- **Sample Response**: `sample-responses/zone-trend.json`

---

### 6. `GET /api/v1/zones/{zone_id}/correlation`
Expose temporal persistence & 2-PZT cross-sensor correlation for a zone.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/zones/{zone_id}/correlation`
- **Path Parameters**:
  - `zone_id`: `integer` (required, ge=1)
- **Query Parameters**:
  - `reference_time`: `string` (optional, ISO-8601 UTC timestamp reference)
  - `window_duration_seconds`: `number` (optional, default: 300.0, min: 10.0, max: 3600.0)
  - `tolerance_seconds`: `number` (optional, default: 0.025, min: 0.001, max: 1.0)
- **Request Body**: None
- **Response Schema**: `ZoneCorrelationResponse`
  - `zone_id`: `integer`
  - `temporal_persistence`: `TemporalPersistenceSchema` (`is_persistent`, `total_events`, `anomalous_events`, `anomaly_ratio`, `window_duration_seconds`)
  - `correlated_groups_count`: `integer`
  - `cross_sensor_groups_count`: `integer`
  - `correlated_groups`: `CorrelatedGroupSchema[]` (`group_id`, `event_ids`, `temporal_spread_ms`, `is_cross_sensor`, `relative_source_hint`)
  - `note`: `string` (Explicit non-localization note)
- **Status Codes**:
  - `200 OK`: Success
  - `404 Not Found`: If `zone_id` does not exist
- **Sample Response**: `sample-responses/zone-correlation.json`

---

### 7. `GET /api/v1/alerts`
Return actionable system alerts.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/alerts`
- **Path Parameters**: None
- **Query Parameters**:
  - `zone_id`: `integer` (optional zone ID filter)
  - `status`: `string` (optional, `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`)
  - `severity`: `string` (optional, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `limit`: `integer` (optional, default: 50, min: 1, max: 500)
- **Request Body**: None
- **Response Schema**: `AlertResponse[]`
  - `id`: `integer`
  - `health_snapshot_id`: `integer`
  - `zone_id`: `integer`
  - `timestamp`: `string` (ISO-8601 UTC)
  - `severity`: `string` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `title`: `string`
  - `message`: `string`
  - `status`: `string` (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`)
  - `acknowledged_at`: `string | null`
  - `resolved_at`: `string | null`
- **Status Codes**: `200 OK`
- **Sample Response**: `sample-responses/alerts.json`

---

### 8. `GET /api/v1/health/summary`
Return dashboard-level monitoring health summary.

- **HTTP Method**: `GET`
- **Path**: `/api/v1/health/summary`
- **Path Parameters**: None
- **Query Parameters**: None
- **Request Body**: None
- **Response Schema**: `HealthSummaryResponse`
  - `total_zones`: `integer`
  - `health_status_counts`: `Record<string, integer>` (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`)
  - `active_alerts_count`: `integer`
  - `recent_events_count`: `integer`
  - `latest_timestamp`: `string | null` (ISO-8601 UTC)
- **Status Codes**: `200 OK`
- **Sample Response**: `sample-responses/health-summary.json`

---

### 9. `POST /api/v1/events`
Submit a new structural event observation.

- **HTTP Method**: `POST`
- **Path**: `/api/v1/events`
- **Path Parameters**: None
- **Query Parameters**: None
- **Request Body**: `EventCreate`
  ```json
  {
    "session_id": 1,
    "zone_id": 1,
    "source_type": "SENSOR",
    "source_id": "PZT-01",
    "correlation_id": "CORR-20260927-001",
    "timestamp": "2026-09-27T15:00:00Z",
    "magnitude": 4.5,
    "energy": 40.0,
    "duration_ms": 25.0,
    "frequency_hz": 120000.0,
    "severity": "HIGH",
    "status": "DETECTED",
    "metadata": { "sensor_gain": 20 }
  }
  ```
- **Response Schema**: `EventResponse` (Created event record with generated `id`)
- **Status Codes**:
  - `201 Created`: Success
  - `404 Not Found`: If `session_id` or `zone_id` does not exist
  - `422 Unprocessable Entity`: Validation failure (e.g. negative magnitude or invalid enum string)
- **Sample Response**: `sample-responses/event-create-response.json`
