# Aegis3D

## Smart PZT-Based Structural Health Monitoring & Early-Warning System

### Team BRIKS
- **Maulik Pandey**
- **Shikhar Sadhu**
- **Pratyush Bhaskar Ram**
- **Madhav Kumar**

**MAITRON 2026** | **Software Track**  
**SDG**: SDG 11 — Sustainable Cities and Communities

---

## Overview

**Aegis3D** is a software-centric structural health monitoring (SHM) and early-warning platform designed to analyze high-frequency structural acoustic and elastic stress wave activity in civil infrastructure. The system ingests discrete sensor voltage samples from Piezoelectric Transducers (PZT), conditions signals, detects transient stress waves, extracts spectral features, assesses zone baseline deviations using standardized z-scores, monitors temporal persistence, evaluates two-sensor arrival time differences, tracks directional trends, and computes an explainable prototype Structural Health Indicator (SHI).

Aegis3D is strictly **Software-First** and deterministic. All intelligence—signal conditioning, feature extraction, baseline evaluation, z-score anomaly scoring, persistence tracking, cross-sensor correlation, health scoring, live event streaming, and trace assembly—is executed by pure, hardware-agnostic Python and TypeScript modules. The platform operates seamlessly whether receiving real-time telemetry from physical microcontrollers, recorded sensor logs, or the included physics-based virtual sensor simulator.

> **Crucial Engineering & Safety Disclaimer**: Aegis3D is an experimental structural health monitoring and early-warning research prototype. It does **NOT** employ black-box machine learning models, predict structural collapse, guarantee disaster prevention, or substitute for certified structural engineering inspections. Piezoelectric Transducers (PZTs) detect acoustic and mechanical stress waves propagating through materials; they do not directly image cracks or provide 2D/3D crack coordinates. Physical inspection by qualified licensed structural engineers remains mandatory for structural diagnosis.

---

## Role of Hardware in a Software-First Architecture

Aegis3D treats physical hardware strictly as an ingestion adapter:
- **Modular Data Ingestion**: Physical PZT sensors and ESP32 microcontrollers serve as data collection nodes streaming voltage samples to backend HTTP REST endpoints.
- **Hardware-Agnostic Intelligence**: Signal processing, baseline comparison, anomaly detection, correlation, health scoring, and trace reconstruction are fully decoupled from sensor hardware, firmware, or database ORMs.
- **Data Source Versatility**: Aegis3D processes sensor telemetry identically regardless of whether packets originate from benchtop physical sensors, imported datasets, or the built-in multi-sensor simulator.

---

## Key Design Principles

1. **Software-Centric & Hardware-Agnostic**: All core pipeline stages run as deterministic Python modules without hardware or GPU dependencies.
2. **Zero Machine Learning**: Aegis3D relies entirely on explainable mathematical, statistical, and signal-processing principles: Butterworth filtering, FFT spectral analysis, standardized z-scores ($|z| \ge 3.0$), rolling anomaly persistence ratios, and bounded rule-based scoring.
3. **Explainable Processing Traces**: Every anomaly flag, persistence decision, correlation group, and health deduction produces itemized, human-readable evidence statements detailing why the result was generated.
4. **Authoritative Backend Single Source of Truth**: The backend pipeline computes all authoritative traces, z-scores, and health metrics. The frontend acts purely as an instrumentation and presentation interface.
5. **Continuous Instrument Experience**: Live processing and completed authoritative trace inspection are unified into one seamless experience without user-facing mode toggles.
6. **Relational Domain Integrity**: Standardized PostgreSQL schema maintaining foreign-key-constrained structural zones, monitoring sessions, raw events, baselines, health snapshots, and system alerts.

---

## Current Implementation Status

### Implemented Subsystems
- **Live Telemetry Ingestion & Live Event Bus**: Real-time HTTP ingestion (`POST /api/v1/telemetry`) integrated with an asynchronous in-memory pub-sub event bus (`LiveEventBus`) emitting Server-Sent Events (`GET /api/v1/telemetry/live`).
- **Rapid Backend Pipeline**: Full 9-stage signal-processing and health pipeline executing end-to-end in milliseconds with zero artificial backend delays or sleeps.
- **Frontend Live Presentation Queue**: Client-side event queue delivering received live SSE events at a deliberate, human-readable cadence (~350–500 ms dwell per stage, ~3.7s total sequence) while displaying actual backend computation duration separately.
- **Continuous Processing Inspector**: Unified inspection panel (`TelemetryProcessingInspector.tsx`) providing live stage tracking, dynamic sliding-window fading pagination, anchored tooltips, keyboard accessibility, reduced-motion support, and an **automatic reset to Page 1 (Ingestion)** upon authoritative trace completion.
- **Authoritative Processing Trace Engine**: Dedicated REST endpoint (`GET /api/v1/telemetry/{identifier}/processing-trace`) providing the full 9-stage evidence payload with raw/conditioned waveforms, FFT frequency spectra, z-scores, and itemized SHI deductions.
- **Virtual Sensor Simulator**: Multi-sensor physics-based signal generator (`simulator/`) simulating PZT tone-burst excitation, structural propagation attenuation, and time delays across structural zones.
- **3D Digital Twin Viewer**: React Three Fiber building viewer (`DigitalTwinViewer.tsx`) mapping structural storeys to GLB meshes with real-time zone health color coding and HUD inspection triggers.
- **GIS City Map**: MapLibre GL 2.5D interface (`CityMap.tsx`) visualizing building footprint polygons in Delhi.
- **Verified Two-Laptop Architecture**: Validated multi-machine deployment where Laptop 2 generates and transmits telemetry across a local network to Laptop 1 running the backend, live SSE stream, and dashboard.
- **Automated Test Suite**: **180 passed / 1 warning** backend pytest suite and **0 error** TypeScript verification.

### Future Milestones
- **Physical ESP32 Benchtop Hardware**: Hardware validation with physical PZT sensors connected via ESP32 ADC over WiFi/Ethernet.
- **Multi-Level Alert Escalation**: Automated dispatch workflows for persistent cross-zone structural anomalies.

---

## Architecture & Live Processing Flow

Aegis3D supports both single-machine local development and multi-machine network deployments:

```text
 ┌──────────────────────────────────────────────────────────────┐
 │                  LAPTOP 2: SENSOR SIMULATOR                  │
 │  - Virtual PZT Signal Generator (Tone Burst Excitation)      │
 │  - Structural Path Attenuation & Delay Modeling              │
 │  - HTTP Client POSTs Telemetry Batch                         │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                 HTTP POST /api/v1/telemetry
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                  LAPTOP 1: FASTAPI BACKEND                   │
 │  1. Ingestion           - Discrete amplitude array parsing   │
 │  2. Conditioning        - DC offset removal & Butterworth    │
 │  3. Event Detection     - Threshold & sample windowing       │
 │  4. Feature Extraction  - Peak, RMS, Energy, FFT Spectrum    │
 │  5. Baseline Reference  - Zone statistical mean & std dev    │
 │  6. Anomaly Evaluation  - Standardized z-score calculation   │
 │  7. Persistence         - Rolling temporal anomaly ratio     │
 │  8. Correlation         - 2-PZT TDOA relative lead/lag       │
 │  9. Health & Alert      - SHI score (0–100) & alert dispatch │
 │                                                              │
 │  Backend Execution: Sub-15 ms (Zero artificial delays)       │
 │  Emits Stage Events to LiveEventBus                          │
 └──────────────┬───────────────────────────────┬───────────────┘
                │                               │
    SSE /api/v1/telemetry/live      GET /api/v1/telemetry/{id}/processing-trace
                │                               │
                ▼                               ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                 LAPTOP 1: FRONTEND DASHBOARD                 │
 │                                                              │
 │  ┌────────────────────────────────────────────────────────┐  │
 │  │ FRONTEND PRESENTATION QUEUE (useLiveTelemetry)         │  │
 │  │ - Queues real SSE stage events                         │  │
 │  │ - Visual dwell pacing: ~350–500 ms per stage           │  │
 │  │ - Bounded queue: Supersedes older pending bursts       │  │
 │  │ - Real backend timing badge: e.g. "STAGE 04 (12ms)"    │  │
 │  └───────────────────────────┬────────────────────────────┘  │
 │                              │                               │
 │                              ▼                               │
 │  ┌────────────────────────────────────────────────────────┐  │
 │  │ UNIFIED PROCESSING INSPECTOR (Continuous UX)           │  │
 │  │ - No user-facing LIVE | ARCHIVE toggle                 │  │
 │  │ - Sequential stage-by-stage presentation (1 → 9)       │  │
 │  │ - On PROCESSING_COMPLETED: loads authoritative trace   │  │
 │  │ - Automatic View Reset: snaps to PAGE 1 (INGESTION)    │  │
 │  │ - Presenter manually navigates completed Pages 1 → 9   │  │
 │  └────────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────┘
```

---

## Live Processing Layer & Server-Sent Events

### SSE Endpoint: `GET /api/v1/telemetry/live`
The backend provides a real-time event stream using standard HTTP Server-Sent Events (SSE). When a telemetry packet arrives at `POST /api/v1/telemetry`, the backend executes the 9 processing stages and publishes events to `LiveEventBus`.

#### Event Types Emitted
- `HEARTBEAT`: Periodic connection keep-alive (every 15s).
- `PROCESSING_STARTED`: Signals that a new telemetry packet was accepted for processing.
- `STAGE_STARTED`: Emitted as each stage (1 through 9) begins execution.
- `STAGE_COMPLETED`: Emitted as each stage completes, containing summary statistics, execution status, and timestamp.
- `PROCESSING_COMPLETED`: Signals end of pipeline execution; includes the authoritative `trace_id` and `event_id` for client-side trace handoff.
- `PROCESSING_ERROR`: Broadcasts pipeline errors or validation failures.

#### Real Backend Speed vs Frontend Presentation Pacing
- **Backend Execution**: The backend executes signal conditioning, FFT, z-score evaluation, and database persistence in real time (typically 5–15 ms total). **No artificial delays, sleeps, or throttling exist in the backend.**
- **Frontend Presentation Queue**: Because human observers cannot comprehend 9 stages flashing past in 10 milliseconds, the frontend (`useLiveTelemetry.ts`) queues the real SSE events and advances through them with deliberate visual dwell times (~350–500 ms per stage).
- **Duration Metrics**: The actual backend processing duration is extracted from event timestamps and displayed in the status badge (e.g. `● LIVE · STAGE 03 (12ms)` or `<1ms`), preserving clear separation between backend compute time and UI presentation pacing.

---

## Processing Inspector: Unified Continuous Experience

The **Processing Inspector** (`TelemetryProcessingInspector.tsx`) eliminates the split between "Live" and "Archive" modes, delivering one uninterrupted instrumentation experience:

### Continuous Workflow
1. **Telemetry Arrives**: Backend ingests the packet and emits real SSE stage events.
2. **Sequential Presentation**: Inspector displays the live pipeline traversing Stages 1 through 9 with human-readable dwell pacing.
3. **Completion & Trace Handoff**: Upon receiving `PROCESSING_COMPLETED`, the inspector automatically queries `GET /api/v1/telemetry/{identifier}/processing-trace` for the completed run's authoritative trace.
4. **Automatic Stage 1 Reset**: As soon as the completed authoritative trace is ready, the inspector **automatically sets its view to Page 1 — Ingestion** (`setCurrentStage(1)`).
5. **Presenter Exploration**: The presenter or evaluator can immediately step through Pages 1 through 9 using the dynamic pagination controls to examine detailed evidence, without needing to manually click backward eight times.

> **Zero Replay Guarantee**: The automatic Stage 1 reset is strictly a view-state navigation change. It does not restart backend processing, replay SSE animations, re-post telemetry, or generate duplicate network requests.

---

## Detailed Processing Pipeline Stages

The backend processing engine and authoritative trace assemble complete evidence across nine sequential stages:

| Stage | Stage Name | Description & Methodology |
|:---:|:---|:---|
| **01** | **Ingestion** | Ingests discrete sensor voltage samples, records sampling rate ($f_s$, default 1000 Hz), sequence number, total sample count, peak amplitude, and sensor bounding window. |
| **02** | **Conditioning** | Removes DC offset via arithmetic mean subtraction ($\tilde{x}[n] = x[n] - \mu$) and applies a 4th-order Butterworth lowpass filter (`scipy.signal`) to suppress high-frequency noise. |
| **03** | **Event Detection** | Evaluates conditioned amplitude against detection thresholds ($V_{\text{thresh}}$), identifies contiguous active activity windows, rejects transient noise below minimum sample count, and merges sub-threshold gaps. |
| **04** | **Feature Extraction** | Computes quantitative event characteristics: Peak Amplitude $\max(\|x[n]\|)$, Root Mean Square (RMS), Discrete Signal Energy $\sum x[n]^2$, Active Duration (ms), and Dominant Frequency via real FFT (`np.fft.rfft`) excluding the DC bin. |
| **05** | **Baseline Reference** | Compares extracted features against zone statistical norms derived from historical normal baseline records (arithmetic mean $\mu$ and population standard deviation $\sigma$ for magnitude and energy, plus baseline event rate). |
| **06** | **Anomaly Evaluation** | Computes standardized z-scores for magnitude and energy: <br>$$z = \frac{x - \mu}{\sigma}$$<br> Flags events exceeding threshold ($\|z\| \ge 3.0$) with zero-variance baseline protection. |
| **07** | **Persistence** | Analyzes rolling anomaly ratios across an observation window (default 300s): tracks total events, anomalous events, anomaly ratio, and maximum consecutive anomalies to filter isolated false positives. |
| **08** | **Cross-Sensor Correlation** | Correlates events across two distinct PZT sensors within temporal tolerance (default 25 ms), computing Time-Difference-of-Arrival (TDOA) spread ($\Delta t = \|t_2 - t_1\|$) and relative lead/lag arrival order along the sensor pair. |
| **09** | **Health & Alert** | Calculates the prototype Structural Health Indicator (SHI 0–100 score), itemized score deduction penalties, health classification (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`), directional trend, and active alert dispatch. |

---

## Cross-Sensor Correlation & Relative Source Indication

Aegis3D supports multi-sensor acoustic wave arrival correlation:
- **TDOA Relationship**: Calculates arrival time delta ($\Delta t = |t_2 - t_1|$) for events detected across paired sensors within a 25 ms coincidence window.
- **Relative Source Indication**: Determines relative wavefront arrival lead/lag (e.g., `"Event arrived first at sensor PZT-Z1-01 (lead time: 4.20 ms relative to PZT-Z1-02)"`).

> **Explicit Non-Localization Note**: Two-PZT correlation indicates **relative arrival precedence along a 1D path between two sensors**. It does **NOT** compute 2D/3D physical coordinates, trilateration, or crack geometric coordinates.

---

## Structural Health Indicator (SHI) Specification

The Structural Health Indicator (SHI) is a bounded, deterministic prototype score strictly ranging from `0` to `100`:

$$\text{raw\_score} = 100.0 - (\text{anomaly\_penalty} + \text{persistence\_penalty} + \text{correlation\_penalty} + \text{trend\_penalty})$$
$$\text{SHI} = \max(0.0, \min(100.0, \text{raw\_score}))$$

### Itemized Penalty Deductions
- **Individual Anomaly Activity**: $-15.0$ pts (triggered when $|z| \ge 3.0$)
- **Temporal Persistence**: $-20.0$ pts (triggered when rolling anomaly ratio exceeds threshold)
- **Cross-Sensor Correlation**: $-25.0$ pts (triggered when correlated wave arrival is confirmed across paired sensors)
- **Increasing Trend Penalty**: $-15.0$ pts (triggered when linear regression slope indicates accelerating degradation)

### Health Status Classification
- $\text{SHI} \ge 90.0 \implies$ `HealthStatus.NORMAL`
- $70.0 \le \text{SHI} < 90.0 \implies$ `HealthStatus.MONITOR`
- $45.0 \le \text{SHI} < 70.0 \implies$ `HealthStatus.INSPECTION_ADVISED`
- $\text{SHI} < 45.0 \implies$ `HealthStatus.HIGH_PRIORITY_INSPECTION`

---

## API Documentation

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Backend service liveness and application status |
| `GET` | `/health/db` | PostgreSQL database connection health check |
| `POST` | `/api/v1/telemetry` | Ingests raw PZT discrete voltage samples, runs 9-stage pipeline, publishes live events |
| `GET` | `/api/v1/telemetry/live` | Server-Sent Events (SSE) stream for real-time stage progression events |
| `GET` | `/api/v1/telemetry/{id}/processing-trace` | Returns complete authoritative 9-stage evidence trace for an event or trace ID |
| `GET` | `/api/v1/telemetry/latest` | Retrieves latest ingested telemetry record and baseline comparison |
| `GET` | `/api/v1/zones` | Lists all monitored structural zones with current health status |
| `GET` | `/api/v1/zones/{id}/health` | Detailed health summary, SHI score, and trend for a specific zone |
| `GET` | `/api/v1/alerts` | Lists active and historical system structural alerts |

---

## Two-Laptop Demo Setup

The live-processing architecture has been verified end-to-end across a two-laptop local area network configuration:

```text
Laptop 2 (Simulator Host)                      Laptop 1 (Platform Host)
[Virtual PZT Simulator]  ──(HTTP POST)──►  [FastAPI Backend :8000]
                                            [PostgreSQL Database]
                                            [LiveEventBus / SSE]
                                            [Next.js Dashboard :3000]
```

### Laptop 1: Platform Host (Backend + Database + Frontend)
1. **Start PostgreSQL**:
   ```bash
   docker compose up -d postgres
   ```
2. **Launch Backend (Bind to all interfaces)**:
   ```bash
   cd backend
   .\.venv\Scripts\activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   *(Note: Binding to `0.0.0.0` allows Laptop 2 to reach the backend via Laptop 1's LAN IP address).*
3. **Launch Frontend Dashboard**:
   ```bash
   cd frontend
   npm run dev
   ```
   Open `http://localhost:3000/dashboard` in a browser.

### Laptop 2: Simulator Host (Telemetry Injection Only)
Laptop 2 does **not** need the database or frontend. It only requires Python to run the simulator:
1. Identify Laptop 1's LAN IP address (e.g. `192.168.1.39`).
2. Run the virtual PZT sensor simulator targeting Laptop 1:
   ```bash
   cd simulator
   python main.py --mode anomaly --sensor PZT-Z1-01 --backend-url http://<LAPTOP-1-IP>:8000 --batches 1
   ```
3. Observe on Laptop 1:
   - Backend processes the batch in ~10 ms and emits real SSE events.
   - Frontend Processing Inspector automatically opens or updates.
   - Stages 1 through 9 present sequentially with human-readable dwell pacing.
   - When processing completes, authoritative trace loads and view resets automatically to **Page 1 — Ingestion**.

---

## Local Single-Machine Setup

For single-machine local development:

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Docker & Docker Compose
- Git

### 2. Database
```bash
docker compose up -d postgres
```

### 3. Backend Setup
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Dashboard is accessible at [http://localhost:3000/dashboard](http://localhost:3000/dashboard) (root `/` automatically redirects to `/dashboard`).

### 5. Run a Simulator Packet
```bash
cd simulator
python main.py --mode anomaly --sensor PZT-Z1-01 --backend-url http://localhost:8000 --batches 1
```

---

## Verification & Test Status

### Backend Pytest Suite
```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/
```
- **Result**: **`180 passed, 1 warning`** in 2.98s across 17 test modules:
  - `test_live_processing.py` (SSE streaming & event bus)
  - `test_processing_trace.py` (9-stage trace assembly & REST endpoint)
  - `test_api_telemetry.py` (ingestion route & schema validation)
  - `test_signal_processing.py` (Butterworth filter & FFT metrics)
  - `test_anomaly.py` (z-score calculation & variance protection)
  - `test_correlation.py` (2-PZT TDOA & relative arrival logic)
  - `test_shi.py` (SHI bounded score & penalty deductions)
  - `test_trend.py`, `test_baseline.py`, `test_api_monitoring.py`, `test_api_events.py`, `test_api_health.py`, `test_models.py`, `test_db_config.py`, `test_api_cors.py`, `test_seed_demo.py`, `test_zone_bim_mapping.py`.

### Frontend Type Validation
```bash
cd frontend
npx tsc --noEmit
```
- **Result**: **`0 errors`** (clean TypeScript compilation).

### Frontend Production Build
```bash
cd frontend
npm run build
```
- **Result**: **`Compiled successfully`** (optimized production bundle with prerendered static routes for `/` and `/dashboard`).

---

## Software-First Milestone Roadmap

### Implemented Capabilities (**Completed**)
- [x] **Backend Intelligence Engine**: Butterworth conditioning, FFT feature extraction, baseline z-score evaluation, temporal persistence, 2-PZT correlation, trend analysis, and deterministic SHI scoring.
- [x] **Telemetry Ingestion API**: `POST /api/v1/telemetry` raw discrete signal processing pipeline.
- [x] **Live Processing Layer**: Asynchronous `LiveEventBus` and SSE endpoint (`GET /api/v1/telemetry/live`) streaming real-time stage execution events.
- [x] **Frontend Presentation Queue**: Client-side event queue delivering received live SSE events at a readable cadence (~350–500 ms per stage) with real backend duration tracking.
- [x] **Unified Processing Inspector**: Single continuous experience removing manual LIVE/ARCHIVE mode switching, complete with dynamic sliding pagination, micro-tooltips, and automatic Page 1 reset upon authoritative trace completion.
- [x] **Processing Trace API**: `GET /api/v1/telemetry/{identifier}/processing-trace` delivering complete 9-stage evidence payloads.
- [x] **Virtual Sensor Simulator**: Physics-based PZT tone burst excitation and structural propagation telemetry generator (`simulator/`).
- [x] **3D Digital Twin & GIS Map**: R3F 3D building viewer (`DigitalTwinViewer.tsx`) with zone health overlays and MapLibre GL city map (`CityMap.tsx`).
- [x] **Two-Laptop Distributed Verification**: End-to-end validation across separate simulator and platform hosts.
- [x] **Automated Test Suite**: 180 passed backend pytest tests, 0 TypeScript errors, successful Next.js production build.

### Future Milestones (**Upcoming Work**)
- [ ] **Physical ESP32 Benchtop Hardware**: Benchtop validation with physical PZT sensors connected via ESP32 ADC.
- [ ] **Multi-Level Alert Escalation**: Automated dispatch workflows for persistent multi-zone structural anomalies.

---

## Engineering Limitations & Prototype Boundaries

1. **Acoustic Wave Detection vs Physical Crack Imaging**: PZT sensors detect transient acoustic, elastic, and mechanical stress waves propagating through materials. They do not directly photograph, image, or measure crack width or depth.
2. **Relative 1D Arrival Order vs 2D/3D Localization**: Aegis3D’s two-sensor correlation determines relative arrival order along a single sensor-to-sensor acoustic path. It does **not** provide 2D planar or 3D spatial crack coordinate localization.
3. **Prototype Indicator vs Certified Structural Rating**: The Structural Health Indicator (SHI) is an experimental scoring index based on observed signal features. It is not an officially certified structural code compliance metric or safety certificate.
4. **Early-Warning Notification vs Disaster Prediction**: "Early warning" denotes the detection of anomalous acoustic stress events exceeding statistical baselines that warrant human engineering inspection. It does **not** constitute a deterministic prediction of structural failure or collapse.
5. **Synthetic & Simulated Inputs**: Benchtop demonstrations may utilize virtual PZT telemetry generated by the simulator to evaluate pipeline behavior across controlled anomaly modes.
6. **Logical Zone Mapping vs Sensor Micro-Coordinates**: 3D Digital Twin BIM mappings associate monitored structural elements by zone groups; they do not represent exact millimeter-level physical sensor mounting coordinates.
