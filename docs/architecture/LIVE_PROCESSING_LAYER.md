# Aegis3D Live Processing Layer Architecture

## 1. Overview & Purpose
The **Aegis3D Live Processing Layer** connects the backend signal processing pipeline with the frontend **Telemetry Processing Inspector** via Server-Sent Events (SSE). It provides a real-time, backend-driven inspection experience where stage progression directly reflects actual execution rather than artificial client-side timers.

```
Simulator (Laptop 2)
        ↓ POST /api/v1/telemetry
Backend Pipeline (Laptop 1: 0.0.0.0:8000)
   ├── Real Stage Execution (1..9)
   ├── Live Event Bus (In-Memory Broadcast)
   │        ↓ GET /api/v1/telemetry/live (SSE)
   │     Frontend Live Inspector (Browser / Laptop 1 & 2)
   │        ↓ on PROCESSING_COMPLETED
   └── Authoritative Trace Store
            ↓ GET /api/v1/telemetry/{id}/processing-trace
         Authoritative 9-Stage Inspector Render
```

---

## 2. Server-Sent Events (SSE) Endpoint

- **Method**: `GET`
- **Path**: `/api/v1/telemetry/live`
- **Headers**:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
- **Query Parameters**:
  - `max_events` (optional, integer): Limits the number of events streamed before ending (primarily used for deterministic integration testing).

### Network & Cross-Origin Configuration
- **CORS**: Configured in FastAPI to allow origins defined in `CORS_ORIGINS` (comma-separated), defaulting to `http://localhost:3000`, `http://127.0.0.1:3000`, and all LAN host IP bindings.
- **Frontend Reverse Proxy**: Next.js route rewrites in `frontend/next.config.js` proxy `/api/:path*` to `process.env.BACKEND_URL || "http://127.0.0.1:8000"`, allowing seamless LAN operations without hardcoding IP addresses.

---

## 3. Event Contract & Schema

Live events are strictly typed and lightweight. They communicate pipeline lifecycle state and stage metrics without streaming redundant heavy waveform arrays over SSE.

### Event Types (`LiveEventType`)
1. `PROCESSING_STARTED`: Emitted when telemetry is accepted and the 9-stage pipeline begins.
2. `STAGE_STARTED`: Emitted when the pipeline enters a specific processing stage.
3. `STAGE_COMPLETED`: Emitted upon successful execution of a stage, carrying stage execution summary and sequence numbers.
4. `PROCESSING_COMPLETED`: Emitted when the 9th stage completes, providing the authoritative `event_id` and `trace_id` for handoff.
5. `PROCESSING_ERROR`: Emitted if an unhandled exception occurs during pipeline execution, identifying the failed stage.
6. `HEARTBEAT`: Periodic keep-alive event emitted every 15 seconds to prevent intermediate proxy timeout.

### 9 Conceptual Stages (`ProcessingStage`)
The pipeline preserves this exact conceptual execution order:
1. `INGESTION`
2. `CONDITIONING`
3. `EVENT_DETECTION`
4. `FEATURE_EXTRACTION`
5. `BASELINE_REFERENCE`
6. `ANOMALY_EVALUATION`
7. `PERSISTENCE`
8. `CROSS_SENSOR_CORRELATION`
9. `HEALTH_AND_ALERT`

### Event Schema (`LiveProcessingEvent`)
```json
{
  "type": "stage_completed",
  "trace_id": "trace-evt-170",
  "event_id": 170,
  "sensor_id": "PZT-Z05",
  "zone_id": 1,
  "stage": "ANOMALY_EVALUATION",
  "status": "completed",
  "summary": "1 event(s) evaluated: ANOMALOUS (peak Z=4.22σ)",
  "error": null,
  "timestamp": "2026-09-29T08:00:00.123456Z",
  "sequence": 4
}
```

---

## 4. In-Process Event Bus Architecture

The backend utilizes `LiveEventBus` (`backend/app/services/live_bus.py`) to decouple synchronous database/pipeline execution from async SSE stream consumers:

- **Asynchronous Loop Dispatch**: Telemetry ingestion executes inside a FastAPI worker thread. Events are safely dispatched to the async event loop using `asyncio.run_coroutine_threadsafe`.
- **Bounded Subscriber Queues**: Each connected SSE client receives an `asyncio.Queue(maxsize=200)`. If a slow client queue fills up, the oldest event is dropped (`drop-oldest` policy) preventing unbounded memory growth.
- **Client Disconnect Cleanup**: When a client terminates or network breaks, the SSE generator detects queue wait timeouts or client disconnects, unregisters the subscriber queue, and frees all associated memory.
- **Zero Blocking**: Telemetry POST ingestion (`/api/v1/telemetry`) is never blocked by slow or unresponsive SSE subscribers.

---

## 5. Frontend Consumption & UI Architecture

The frontend integrates the live stream via the `useLiveTelemetry` hook (`frontend/hooks/useLiveTelemetry.ts`) and the `TelemetryProcessingInspector` component (`frontend/components/dashboard/TelemetryProcessingInspector.tsx`):

### UI States
- `DISCONNECTED`: SSE disconnected.
- `CONNECTING`: Attempting connection to `/api/v1/telemetry/live`.
- `CONNECTED` / `IDLE`: Connected and actively listening; awaiting telemetry packets.
- `PROCESSING`: Pipeline is currently executing stages 1 through 9.
- `COMPLETED`: Run complete and authoritative trace synced.
- `ERROR`: Pipeline execution or stream error.
- `RECONNECTING`: Network interrupted; backoff retry active.

### Live Stage Progression
- Upon `STAGE_STARTED`, the active stage indicator renders an amber active state (`● PROCESSING`).
- Upon `STAGE_COMPLETED`, the stage transitions to green completed (`✓`).
- If `PROCESSING_ERROR` arrives, the stage turns red (`✕ ERROR`).
- With `AUTO-TRACK ON`, the inspector automatically navigates the paginated evidence view to the currently executing stage.

### Authoritative Trace Handoff
To maintain a single source of truth, SSE is strictly a lightweight live transport. When `PROCESSING_COMPLETED` is received:
1. The frontend extracts `event_id` or `trace_id`.
2. It fetches `GET /api/v1/telemetry/{identifier}/processing-trace`.
3. The transient live states are seamlessly replaced with the authoritative trace data (full bounded waveform samples, detailed statistical breakdowns, baseline parameters).

### Rule: "NO TELEMETRY ≠ HEALTHY"
When connected to SSE but no telemetry packets have arrived, the inspector displays:
```
NO TELEMETRY ≠ HEALTHY · SYSTEM IDLE
```
It never displays "HEALTHY" in the absence of real telemetry signals.

---

## 6. Current In-Process Limitation
The current event bus is an **in-process prototype broker**:
- It operates entirely in memory within a single FastAPI server instance.
- It does **not** persist events across server restarts.
- For horizontally scaled deployments across multiple backend container instances, an external broker (such as Redis Pub/Sub, NATS, or Kafka) would replace the in-memory subscriber registry. For the single-instance Aegis3D platform, this design provides zero-overhead, sub-millisecond event dispatch without additional infrastructure dependencies.
