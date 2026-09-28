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

**Aegis3D** is a software-centric structural health monitoring (SHM) and early-warning platform with an optional physical piezoelectric transducer (PZT) sensing input layer. The platform observes structural acoustic and mechanical wave activity in buildings and infrastructure to detect anomalous behavior, evaluate multi-event persistence, correlate multi-sensor arrival times, analyze directional trend trajectories, compute an explainable prototype Structural Health Indicator (SHI), and expose real-time monitoring data and 9-stage processing traces via REST APIs.

While PZT sensors and ESP32 microcontrollers form the planned physical sensing layer, Aegis3D is strictly **Software-First**. All core intelligence—DC offset removal, Butterworth lowpass filtering, threshold-based event detection, FFT feature extraction, zone statistical baselines, z-score anomaly detection, temporal persistence evaluation, 2-PZT time-difference-of-arrival correlation, directional trend analysis, SHI scoring, processing trace assembly, and REST API routing—is executed by pure, hardware-agnostic Python software modules. The backend functions seamlessly whether fed by live telemetry streams, imported historical sensor logs, or virtual signal simulators.

> **Crucial Technical Disclaimer**: Aegis3D is a continuous structural health monitoring and early-warning software platform. It does **NOT** use machine learning inference, predict structural collapse, guarantee disaster prevention, replace licensed structural engineers, or provide certified engineering safety assessments. Piezoelectric Transducers (PZTs) capture acoustic and mechanical stress waves within materials; they do not directly "see" cracks or establish 2D/3D crack coordinates. Human engineering inspection remains mandatory for actual structural diagnosis.

---

## Role of Hardware in a Software-First Architecture

Aegis3D treats physical hardware strictly as an optional data ingestion adapter:
- **Input Mechanism**: Physical PZT sensors and ESP32 microcontrollers serve as collection nodes feeding voltage samples into backend API endpoints or MQTT brokers.
- **Hardware-Agnostic Intelligence**: All signal processing, feature extraction, statistical baseline comparison, correlation, trend, health indicator, processing trace generation, and REST API modules are decoupled from specific microcontrollers, sensor hardware, or database ORMs.
- **Data Source Versatility**: Aegis3D evaluates signal inputs identically regardless of whether they originate from physical sensors, imported datasets, or simulator engines.

---

## Key Design Principles

1. **Software-Centric & Hardware-Agnostic**: Signal processing, baseline, anomaly, correlation, trend, health evaluation, processing trace assembly, and REST API routing logic remain pure Python modules.
2. **Zero Machine Learning**: Aegis3D deliberately uses deterministic signal processing, standard deviation metrics, standardized z-scores, rolling window metrics, and rule-based thresholds instead of black-box AI/ML models.
3. **Explainable Evidence & Processing Traces**: All anomaly flags, persistence evaluations, correlation groups, trends, health scores, and API endpoints produce itemized, human-readable evidence statements explaining why a result was produced.
4. **Authoritative Backend**: The backend is the single source of truth for processing trace metrics, z-scores, persistence decisions, correlation groups, and health scores. The frontend acts strictly as a visual presentation layer.
5. **Relational Domain Integrity**: Standardized PostgreSQL database schema storing structural zones, monitoring sessions, events, baselines, health snapshots, and alerts with foreign key constraints.

---

## Current Implementation Status

### Implemented vs Scaffolded Overview

- **IMPLEMENTED**:
  - **Backend Telemetry & Processing Trace Engine**: Complete 9-stage intelligence engine, PostgreSQL persistence, telemetry ingestion (`POST /api/v1/telemetry`), processing trace endpoint (`GET /api/v1/telemetry/{identifier}/processing-trace`), signal processing, baselining, z-score anomaly detection, temporal persistence, 2-PZT cross-sensor correlation, trend analysis, deterministic SHI, and REST APIs.
  - **Frontend Telemetry Processing Inspector**: Focused 9-stage evidence viewer component (`TelemetryProcessingInspector.tsx`) featuring dynamic sliding-window fading pagination, clickable indicator dots, anchored hover tooltips, directional page slide transitions, keyboard accessibility (`aria-current="step"`, high-contrast focus rings), reduced motion support (`prefers-reduced-motion: reduce`), SVG engineering icons, and compact first-viewport hierarchy on Page 9.
  - **Virtual Sensor Simulator**: Physics-inspired multi-sensor signal simulator (`simulator/`) with PZT tone burst excitation generators (`generate_pzt_tone_burst`), structural path propagation models, and virtual PZT receivers emitting streams to `POST /api/v1/telemetry`.
  - **BIM & IFC Processing**: Offline IFC spatial extraction (`building_metadata.json`, `glb_mapping.json`, `zone_bim_mapping.json`) mapping structural elements across storeys to 3D GLB node names.
  - **3D Digital Twin Viewer**: Three.js / React Three Fiber building viewer (`frontend/components/building/DigitalTwinViewer.tsx`) integrated with canonical Zone ↔ BIM mapping, live health status endpoints, dynamic mesh group highlighting, HUD inspector launch triggers, and prototype disclaimers.
  - **GIS City Map Interface**: 2.5D MapLibre GL city map component (`CityMap.tsx`) rendering Delhi building footprint polygons (`delhi_buildings.json`).
  - **Automated Test Suite**: **173 passed / 1 warning** backend pytest unit & integration tests (`backend/tests/`).
- **UPCOMING / FUTURE MILESTONES**:
  - **Live Processing Stream**: Real-time WebSockets / SSE streaming layer connecting live background processing updates directly into the inspector UI.
  - **ESP32 Benchtop Hardware**: Full benchtop validation with physical ESP32 PZT sampling hardware.

---

## Implemented Processing & Data Flow Pipeline

```text
[ Simulator / Sensor Telemetry ]
               │
               ▼
 [ POST /api/v1/telemetry ]
               │
               ▼
 [ GET /api/v1/telemetry/{identifier}/processing-trace ]
               │
               ▼
 ┌─────────────────────────────────────────────────────────┐
 │               9-STAGE PROCESSING TRACE                   │
 ├─────────────────────────────────────────────────────────┤
 │  1. INGESTION           Raw signal & bounds metadata    │
 │  2. CONDITIONING        DC removal & lowpass filter     │
 │  3. EVENT DETECTION     Threshold & window detection    │
 │  4. FEATURE EXTRACTION  Peak, RMS, Energy, FFT Freq     │
 │  5. BASELINE REFERENCE  Zone mean & std deviation norms │
 │  6. ANOMALY EVALUATION  Standardized z-score deviation  │
 │  7. PERSISTENCE         Rolling temporal anomaly ratio  │
 │  8. CORRELATION         2-PZT TDOA relative source      │
 │  9. HEALTH & ALERT      SHI score (0–100) & alert box   │
 └─────────────────────────────────────────────────────────┘
               │
               ▼
 [ Telemetry Processing Inspector (Frontend Visualization Layer) ]
```

---

## Detailed Processing Trace Stages

The processing trace API (`GET /api/v1/telemetry/{identifier}/processing-trace`) assembles full trace evidence across nine sequential stages:

1. **Ingestion Stage**: Captures raw discrete sensor amplitude samples, sample rate (Hz), timestamp, total sample count, peak amplitude, and bounding window state.
2. **Conditioning Stage**: Applies mean-subtraction DC offset removal and Butterworth lowpass filtering (`scipy.signal`), recording DC offset and window parameters.
3. **Event Detection Stage**: Evaluates signal amplitude against detection threshold, identifies active activity windows, filters noise via minimum sample duration, and merges sub-threshold gaps.
4. **Feature Extraction Stage**: Extracts quantitative metrics for detected events:
   - **Peak Amplitude**: $\max(|x[n]|)$
   - **RMS Amplitude**: Root Mean Square of sampled amplitudes
   - **Discrete Signal Energy**: $\sum x[n]^2$ (*Digital signal metric*)
   - **Duration & Sample Count**: Active window duration in milliseconds and point count.
   - **Dominant Frequency**: Real FFT spectrum analysis (`np.fft.rfft`) with zero-padding and DC bin exclusion.
5. **Baseline Reference Stage**: Compares extracted event features against historical zone baseline statistical norms (arithmetic mean and population standard deviation for magnitude and energy, normal event rate).
6. **Anomaly Evaluation Stage**: Computes standardized z-scores for magnitude and energy:
   $$z_{\text{magnitude}} = \frac{\text{magnitude} - \mu_{\text{magnitude}}}{\sigma_{\text{magnitude}}}, \quad z_{\text{energy}} = \frac{\text{energy} - \mu_{\text{energy}}}{\sigma_{\text{energy}}}$$
   Flags events exceeding standardized threshold ($|z| \ge 3.0$) with zero-variance baseline protection.
7. **Persistence Stage**: Evaluates rolling anomaly ratio over an observation window (default 300s), tracking total events, anomalous events, anomaly ratio, and maximum consecutive anomalies.
8. **Cross-Sensor Correlation Stage**: Correlates events across two distinct PZT sensors within temporal tolerance (default 25ms), computing Time-Difference-of-Arrival (TDOA) spread ($\Delta t = |t_2 - t_1|$) and relative source indication lead/lag hints.
9. **Health & Alert Stage**: Computes the prototype Structural Health Indicator (SHI 0–100 score), itemized score deduction penalties, health status classification (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`), directional trend, system alert dispatch, and canonical disclaimer.

---

## Telemetry Processing Inspector UI (`frontend/components/dashboard/`)

The frontend contains a dedicated Telemetry Processing Inspector component (`TelemetryProcessingInspector.tsx`) designed specifically for narrow workspace analysis (~420px panel):

- **Focus & Hierarchy**: Designed as an engineering control-room instrument rather than a generic SaaS dashboard. Employs dark slate flat surfaces, crisp 1px borders, restrained typography, and Title Case section headings.
- **Dynamic Fading Stage Pagination (`DynamicStagePagination`)**: Horizontally centered 7-dot sliding window pagination bar (`[ ← ] ○ ○ ● ○ ○ ○ ○ [ → ]`). Indicator opacity fades progressively based on stage distance ($d_0 = 1.0$, $d_1 = 0.75$, $d_2 = 0.50$, $d_3 = 0.28$, $d_4+ = 0.14$).
- **Anchored Micro-Tooltips**: Hovering any stage dot reveals a crisp monospace stage label anchored directly above the dot (`role="tooltip"`), following the dot without mouse-tracking or layout shifts.
- **Directional Page Slide Transitions**: Moving forward (`target > current`) slides content in from `+16px` right; moving backward (`target < current`) slides content in from `-16px` left (`260ms cubic-bezier`).
- **Keyboard Accessibility & Reduced Motion**: Full keyboard control (`aria-current="step"`, high-contrast focus rings via `.stage-dot-btn:focus-visible`). Complete motion disabling under `@media (prefers-reduced-motion: reduce)`.
- **Page 9 First-Viewport Layout**: Consolidated SHI score (`40.0 / 100`), status badge (`HIGH PRIORITY INSPECTION`), trend, score deductions grid (`−15 pts`, `−20 pts`, `−25 pts`, `total_deductions −60 pts`), and System Alert Dispatch box into the top viewport area.

---

## Cross-Sensor Correlation & Relative Source Indication

Aegis3D supports multi-sensor event correlation across PZT transducers:
- **TDOA Relationship**: Calculates arrival time difference ($\Delta t = |t_2 - t_1|$) for events falling within the 25ms tolerance window.
- **Relative Source Indication**: Generates relative arrival lead/lag hints (e.g. `"Event arrived first at sensor PZT-Z1-01 (lead time: 4.20 ms relative to PZT-Z1-02)"`).

> **Explicit Non-Localization Note**: The 2-PZT correlation module provides **relative arrival order along a 2-sensor path**. It does **NOT** compute exact 2D/3D spatial coordinates, physical crack coordinates, or precise damage localization.

---

## Structural Health Indicator (SHI) Specification

The Structural Health Indicator (SHI) is a deterministic prototype score bounded strictly to `0–100`:
$$\text{raw\_score} = 100.0 - (\text{anomaly\_penalty} + \text{persistence\_penalty} + \text{cross\_sensor\_penalty} + \text{trend\_penalty})$$
$$\text{SHI} = \max(0, \min(100, \text{raw\_score}))$$

### Penalty Breakdown
- Individual Anomaly Activity: $-15.0$ pts
- Temporal Persistence: $-20.0$ pts
- Cross-Sensor Correlation: $-25.0$ pts
- Increasing Trend Penalty: $-15.0$ pts

### Prototype Health Status Mapping
- $\text{SHI} \ge 90.0 \implies \text{HealthStatus.NORMAL}$
- $70.0 \le \text{SHI} < 90.0 \implies \text{HealthStatus.MONITOR}$
- $45.0 \le \text{SHI} < 70.0 \implies \text{HealthStatus.INSPECTION_ADVISED}$
- $\text{SHI} < 45.0 \implies \text{HealthStatus.HIGH_PRIORITY_INSPECTION}$

### Mandatory Safety Disclaimer
Every health result payload and inspector view displays the canonical disclaimer:
> *"SHI is a prototype evidence-based monitoring indicator derived from observed signal/event behavior. It is not a certified structural safety score and does not independently establish structural damage or failure."*

---

## BIM / Digital Twin & GIS Integration

- **IFC / GLB Model**: Offline spatial extraction parses IFC structural geometries into `building_metadata.json` and maps storeys/elements to GLB mesh node identifiers (`models/glb/building_demo.glb`).
- **3D Building Viewer (`DigitalTwinViewer.tsx`)**: Built with Three.js and React Three Fiber. Applies dynamic status color overlays (`NORMAL`, `MONITOR`, `INSPECTION_ADVISED`, `HIGH_PRIORITY_INSPECTION`) to structural elements based on backend zone health endpoints.
- **Logical Zones vs Spatial Groups**: Maps logical monitoring zones (`Zone 1 - Main Deck Girder`, `Zone 2 - Pier Column 4`) to BIM element groups. *Does not claim physical individual sensor micro-coordinates.*
- **GIS City Map (`CityMap.tsx`)**: Next.js 14 MapLibre GL 2.5D city map component rendering building footprint polygons in Delhi (`delhi_buildings.json`).

---

## Virtual Sensor Simulator (`simulator/`)

The repository includes an active virtual signal simulator emitting multi-sensor telemetry to `POST /api/v1/telemetry`:
- **PZT Tone Burst Excitation (`generate_pzt_tone_burst`)**: Generates windowed sinusoidal tone-burst signals representing active PZT acoustic excitation.
- **Physics-Inspired Propagation (`simulator/physics/`)**: Models attenuation and time delay across structural propagation paths between virtual sensors.
- **Signal Modes**: Supports `normal`/`healthy`, `transient`/`event`, and `anomaly` signal payload generation.

---

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Docker & Docker Compose (for PostgreSQL database)
- Git

### 2. Environment Configuration
```bash
git clone https://github.com/m4ulikP/Aegis3D.git
cd Aegis3D
cp .env.example .env
```

### 3. Start PostgreSQL Database Container
```bash
docker compose up -d postgres
```

### 4. Setup Backend Virtual Environment
```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\activate

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 5. Setup Frontend Application
```bash
cd frontend
npm install
npm run dev
```

Endpoints:
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Health**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Telemetry Ingestion**: `POST http://127.0.0.1:8000/api/v1/telemetry`
- **Processing Trace**: `GET http://127.0.0.1:8000/api/v1/telemetry/latest/processing-trace`
- **Frontend Dashboard**: [http://localhost:3000/dashboard](http://localhost:3000/dashboard)

---

## Test Verification

### Backend Pytest Suite
```bash
cd backend
.\.venv\Scripts\python.exe -m pytest
```
*Verification Result*: **`173 passed, 1 warning`** across 16 test modules (`test_processing_trace.py`, `test_api_telemetry.py`, `test_signal_processing.py`, `test_shi.py`, `test_anomaly.py`, `test_correlation.py`, `test_trend.py`, `test_baseline.py`, `test_api_monitoring.py`, `test_api_events.py`, `test_api_health.py`, `test_models.py`, `test_db_config.py`, `test_api_cors.py`, `test_seed_demo.py`, `test_zone_bim_mapping.py`).

### Frontend Type Check
```bash
cd frontend
npx tsc --noEmit
```
*Verification Result*: **`0 errors`**.

---

## Software-First Milestone Roadmap

### Implemented Capabilities (**Completed**)
- [x] **Backend Intelligence Engine**: Signal processing (Butterworth/FFT), statistical baseline, z-score anomaly detection, temporal persistence, 2-PZT cross-sensor correlation, directional trend, and SHI scoring.
- [x] **Telemetry Ingestion API**: `POST /api/v1/telemetry` raw discrete signal processing pipeline.
- [x] **Processing Trace API**: `GET /api/v1/telemetry/{identifier}/processing-trace` returning full 9-stage evidence trace payloads.
- [x] **Frontend Telemetry Inspector**: 9-stage evidence viewer component (`TelemetryProcessingInspector.tsx`) with dynamic sliding-window fading stage pagination, tooltips, keyboard accessibility, reduced motion support, directional page slide transitions, and Page 9 first-viewport layout.
- [x] **Virtual Sensor Simulator**: PZT tone burst excitation and structural propagation telemetry generator (`simulator/`).
- [x] **3D Digital Twin & GIS Map**: R3F 3D building viewer (`DigitalTwinViewer.tsx`) with zone health highlighting and MapLibre GL GIS map (`CityMap.tsx`).
- [x] **REST API Layer & Pytest Suite**: Complete monitoring REST endpoints and **173 passed / 1 warning** pytest suite.

### Future Milestones (**Upcoming Work**)
- [ ] **Live Processing Stream**: Real-time WebSockets / SSE streaming layer connecting live background processing updates directly into the inspector UI.
- [ ] **ESP32 Benchtop Hardware**: Full benchtop validation with physical ESP32 PZT sampling hardware.
- [ ] **Multi-level Alert Escalation**: Escalation workflows for persistent multi-zone anomalies.
