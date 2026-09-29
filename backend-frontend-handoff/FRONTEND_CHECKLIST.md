# Frontend Integration Checklist & Roadmap

This document provides the frontend developer with a practical checklist for integrating the Next.js 14 application shell with the Aegis3D FastAPI backend.

---

## 1. IMPLEMENTED NOW (Ready for Client Integration)

### API Client Setup
- [ ] Configure `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` pointing to `http://localhost:8000/api/v1` (or Next.js rewrite `/api/v1`).
- [ ] Create a typed API fetch wrapper or TanStack/React Query client in `frontend/lib/api.ts`.

### TypeScript Types & Enum Definitions
- [ ] Import or generate TypeScript interfaces based on `backend-frontend-handoff/openapi.json` or `sample-responses/*.json`.
- [ ] Copy string literal types from `backend-frontend-handoff/ENUMS.md` (`HealthStatus`, `HealthTrend`, `EventSeverity`, `EventStatus`, `AlertStatus`, `AlertSeverity`).

### Endpoint Integrations
- [ ] **Dashboard Health Summary Card**: Connect `GET /api/v1/health/summary` to populate total zones count, active alert badge, total event count, and latest update timestamp.
- [ ] **Zone List & Selector**: Connect `GET /api/v1/zones` to render floor/zone list navigation.
- [ ] **Zone Detail View**: Connect `GET /api/v1/zones/{zone_id}` for individual zone header information.
- [ ] **Structural Health Indicator (SHI) Card**: Connect `GET /api/v1/zones/{zone_id}/health` to render 0–100 score gauge, `HealthStatus` status pill (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`), trend indicator, explainable text summary, itemized deductions breakdown, and mandatory disclaimer text.
- [ ] **Directional Trend Panel**: Connect `GET /api/v1/zones/{zone_id}/trend` to render earlier vs later period metric comparison tables (anomaly rates, mean magnitudes, persistent counts).
- [ ] **Correlation & Persistence Panel**: Connect `GET /api/v1/zones/{zone_id}/correlation` to render 2-PZT correlated event groups, arrival lead times, and non-localization notice.
- [ ] **Event Table / Feed**: Connect `GET /api/v1/zones/{zone_id}/events` to populate structural event table with severity badges and timestamp formatting.
- [ ] **Alerts List**: Connect `GET /api/v1/alerts` to render actionable alert list filtering by `zone_id` and `status=ACTIVE`.

### UI UX Handling
- [ ] **Timestamp Formatting**: Parse ISO-8601 UTC timestamp strings using standard JS date formatters (`date-fns` or `Intl.DateTimeFormat`).
- [ ] **Empty State Handling**: Safely handle empty arrays (`zones: []`, `events: []`, `alerts: []`) and `null` timestamps.
- [ ] **Loading States**: Display skeleton loaders while fetching zone health, trend, or event lists.
- [ ] **Error Handling**: Display fallback UI for `404 Not Found` (missing zone/event) or server connectivity errors using contracts in `backend-frontend-handoff/ERRORS.md`.

---

## 2. FUTURE / NOT IMPLEMENTED YET (Do Not Attempt to Wire Up Yet)

- [ ] **Client-Side CORS Middleware**: Backend currently relies on server-to-server fetch or Next.js rewrites; native CORS headers in FastAPI are planned.
- [ ] **Real-Time Streaming**: WebSockets (`ws://`) and Server-Sent Events (`/events/stream`) are not implemented. Use HTTP polling (e.g. 5-10s refetch interval in TanStack Query) for live updates.
- [ ] **3D BIM Interactive Mesh Renderer**: Three.js / React Three Fiber renderer loading `building_demo.glb` and applying `glb_mapping.json` highlights is scaffolded (`frontend/components/building/.gitkeep`), pending implementation.
- [ ] **City Map $\rightarrow$ Building Click Transition**: Interaction connecting MapLibre building polygon click to load the 3D building viewer is pending.
- [ ] **MQTT Live Ingestion Status**: Microcontroller ESP32 live streaming ingestion state is scaffolded in firmware/hardware, not exposed in API.
- [ ] **Authentication & User Management**: Login, JWT tokens, and user session management are not implemented in backend.
