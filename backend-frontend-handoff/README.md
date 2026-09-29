# Aegis3D Backend-to-Frontend Integration Handoff Package

> **Notice**: This folder (`backend-frontend-handoff/`) is a **temporary handoff package** generated to help the frontend teammate immediately inspect, contract-check, and wire up the Next.js application shell to the Aegis3D FastAPI backend. It is **not** persistent production documentation.

---

## Welcome to the Backend Handoff Package!

The Aegis3D backend intelligence pipeline (Steps 1–11) is 100% complete, tested, and merged on `main`. All 9 frontend-facing REST endpoints are live and fully operational.

This folder contains everything you need to start connecting the Next.js 14 frontend components right now.

---

## Handoff Directory Sitemap

| File / Folder | Purpose |
| :--- | :--- |
| [**`API_CONTRACT.md`**](./API_CONTRACT.md) | **Primary Reference**: Detailed endpoint contracts for all 9 REST endpoints (methods, paths, params, response schemas, status codes). |
| [**`openapi.json`**](./openapi.json) | **Live OpenAPI Spec**: Complete FastAPI 3.1.0 OpenAPI JSON export generated directly from the backend application. |
| [**`sample-responses/`**](./sample-responses/) | **Sample JSON Data**: Schema-accurate sample response files for every endpoint (`zones.json`, `zone-health.json`, `health-summary.json`, etc.). |
| [**`ENUMS.md`**](./ENUMS.md) | **TypeScript Types**: Exact string enum definitions (`HealthStatus`, `HealthTrend`, `EventSeverity`, `AlertStatus`, etc.). |
| [**`ERRORS.md`**](./ERRORS.md) | **Error Handling**: Detailed HTTP error status codes (`404`, `422`, `503`) and response structures. |
| [**`LOCAL_SETUP.md`**](./LOCAL_SETUP.md) | **Local Running Guide**: How to start PostgreSQL (`docker compose up -d postgres`) and launch FastAPI (`uvicorn app.main:app`). |
| [**`FRONTEND_CHECKLIST.md`**](./FRONTEND_CHECKLIST.md) | **Integration Roadmap**: Step-by-step checklist separating what is ready now vs what is planned for future steps. |
| [**`ZONE_BIM_MAPPING.md`**](./ZONE_BIM_MAPPING.md) | **Identifier Audit**: Complete map of `Zone.id`, `BLDG-001`, IFC `GlobalId`, structural components, and sensor `source_id`. |
| [**`BACKEND_STATUS.md`**](./BACKEND_STATUS.md) | **Backend Snapshot**: Complete technical status matrix of backend modules and services. |

---

## What You Can Connect Right Now

You can immediately wire up the following Next.js dashboard UI elements to live backend REST routes:

1. **Dashboard Overview Summary Cards**: Fetch `GET /api/v1/health/summary` for total zones count, active alert badge count, total event count, and latest timestamp.
2. **Zone Navigation & Selector**: Fetch `GET /api/v1/zones` to populate floor/zone sidebar or dropdown selectors.
3. **Zone Header Metadata**: Fetch `GET /api/v1/zones/{zone_id}` for zone details and active alert status.
4. **Structural Health Indicator (SHI) Card**: Fetch `GET /api/v1/zones/{zone_id}/health` to render 0–100 score gauge, `HealthStatus` badge, explainable evidence breakdown, and embedded safety disclaimer.
5. **Directional Trend Panel**: Fetch `GET /api/v1/zones/{zone_id}/trend` to render earlier vs later period metric comparison tables (`STABLE`, `INCREASING`, `DECREASING`).
6. **2-PZT Sensor Correlation Panel**: Fetch `GET /api/v1/zones/{zone_id}/correlation` to show 2-PZT event groups, lead times, and non-localization notice.
7. **Event Log Feed**: Fetch `GET /api/v1/zones/{zone_id}/events` with severity/status filters.
8. **Actionable Alert List**: Fetch `GET /api/v1/alerts` for active system alert feeds.

---

## What Is NOT Implemented Yet (Do Not Wire Up Yet)

- **Browser 3D BIM Viewer Component**: Three.js / React Three Fiber renderer component (`BuildingViewer.tsx`) loading `building_demo.glb` is scaffolded (`frontend/components/building/.gitkeep`), pending implementation in Step 13.
- **WebSockets / SSE Streaming**: Real-time push streams are not active. Use HTTP polling (5–10s refetch interval in TanStack Query) for live UI updates.
- **Native CORS Headers**: Backend currently runs without native CORS middleware. Use Next.js rewrites in `frontend/next.config.js` or server-side fetch calls to bypass origin checks during local development.
- **Authentication**: Authentication is not enabled; API routes are unauthenticated.

---

## Decisions to Align On (Backend & Frontend Discussion)

1. **CORS Configuration**: Whether to add `CORSMiddleware` directly to `backend/app/main.py` for client-side fetching from `http://localhost:3000` or rely on Next.js rewrites.
2. **3D Mesh Highlighting Strategy**: Alignment on using IFC `GlobalId` tags from `glb_mapping.json` to highlight structural components in the 3D viewer when a zone or event is selected.
3. **Polling Interval**: Standardizing client refetch intervals (e.g., 5 seconds for events/alerts, 30 seconds for trend/health evaluation).
