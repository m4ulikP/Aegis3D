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

**Aegis3D** is a software-centric structural health monitoring (SHM) and early-warning platform with an optional physical piezoelectric transducer (PZT) sensing input layer. The platform observes structural acoustic and mechanical wave activity in buildings and infrastructure to detect anomalous behavior, evaluate multi-event persistence, correlate multi-sensor arrival times, analyze directional trend trajectories, compute an explainable prototype Structural Health Indicator (SHI), and expose real-time monitoring data via frontend-consumable REST APIs.

While PZT sensors and ESP32 microcontrollers form the planned physical sensing layer, Aegis3D is strictly **Software-First**. All core intelligence—DC offset removal, Butterworth lowpass filtering, threshold-based event detection, FFT feature extraction, zone statistical baselines, z-score anomaly detection, temporal persistence evaluation, 2-PZT time-difference-of-arrival correlation, directional trend analysis, SHI scoring, and REST API routing—is executed by pure, hardware-agnostic Python software modules. The backend functions seamlessly whether fed by live ESP32 streams, imported historical sensor logs, or synthetic signal sources.

> **Crucial Technical Disclaimer**: Aegis3D is a continuous monitoring and early-warning software platform. It does **NOT** use machine learning inference, predict structural collapse, guarantee disaster prevention, replace licensed structural engineers, or provide certified engineering safety assessments. Piezoelectric Transducers (PZTs) capture acoustic and mechanical stress waves within materials; they do not directly "see" cracks. Human engineering inspection remains mandatory for actual structural diagnosis.

---

## Role of Hardware in a Software-First Architecture

Aegis3D treats physical hardware strictly as an optional data ingestion adapter:
- **Input Mechanism**: Physical PZT sensors and ESP32 microcontrollers serve as data collection nodes feeding voltage samples into the backend API or MQTT broker.
- **Hardware-Agnostic Intelligence**: All signal processing, feature extraction, statistical baseline comparison, correlation, trend, health indicator, and REST API modules are decoupled from specific microcontrollers, sensor hardware, or database ORMs.
- **Data Source Versatility**: Aegis3D evaluates signal inputs identically regardless of whether they originate from physical sensors, imported datasets, or simulator engines.

---

## Key Design Principles

1. **Software-Centric & Hardware-Agnostic**: Signal processing, baseline, anomaly, correlation, trend, health evaluation, and REST API routing logic remain pure Python modules.
2. **Zero Machine Learning**: Aegis3D deliberately uses deterministic signal processing, standard deviation metrics, standardized z-scores, rolling window metrics, and rule-based thresholds instead of black-box AI/ML models.
3. **Explainable Evidence**: All anomaly flags, persistence evaluations, correlation groups, trends, health scores, and API endpoints produce itemized, human-readable evidence statements explaining why a result was produced.
4. **Relational Domain Integrity**: Standardized PostgreSQL database schema storing structural zones, monitoring sessions, events, baselines, health snapshots, and alerts with foreign key constraints.

---

## Current Implementation Status

### Implemented vs Scaffolded Overview

- **IMPLEMENTED**:
  - **Backend Telemetry & Processing Engine**: Complete intelligence engine, PostgreSQL persistence, telemetry ingestion (`POST /api/v1/telemetry`), signal processing, baselining, z-score anomaly detection, temporal persistence, 2-PZT cross-sensor correlation, trend analysis, deterministic SHI, and frontend-consumable REST APIs.
  - **BIM & IFC Processing**: Offline IFC spatial extraction (`building_metadata.json`, `glb_mapping.json`, `zone_bim_mapping.json`) mapping structural elements across storeys to 3D GLB node names.
  - **3D Digital Twin Viewer**: React Three Fiber / Three.js 3D building viewer (`frontend/components/building/BuildingViewer.tsx`) integrated with canonical Zone ↔ BIM mapping, live health status endpoints, dynamic mesh group highlighting, HUD inspector, and prototype disclaimer.
  - **GIS City Map Interface**: 2.5D MapLibre GL city map component (`CityMap.tsx`) rendering Delhi building footprint polygons (`delhi_buildings.json`).
- **SCAFFOLDED / UPCOMING NEXT**:
  - **Virtual Sensor Simulator**: Virtual signal simulator emitting representative telemetry streams to `POST /api/v1/telemetry` is upcoming work.
  - **Frontend Live Monitoring Cards**: Live streaming card integration and dynamic real-time telemetry pipeline visualization components.
  - **Real-Time Streaming**: WebSockets and Server-Sent Events (SSE) live data flows.

### Implementation Status Breakdown

| Component | Status | Description / Location |
| :--- | :--- | :--- |
| **Domain Models & Schemas** | **Implemented** | Core SQLAlchemy models (`Zone`, `MonitoringSession`, `Event`, `Baseline`, `HealthSnapshot`, `Alert`) & Pydantic DTOs (`backend/app/models/`, `backend/app/schemas/`) |
| **PostgreSQL Persistence** | **Implemented** | Environment-based DB configuration, SQLAlchemy 2.0 session layer, and Alembic migrations (`backend/app/db/`) |
| **FastAPI REST Foundation** | **Implemented** | API foundation with liveness `/health` and DB readiness `/health/db` endpoints (`backend/app/api/routes/health.py`) |
| **Telemetry Ingestion API** | **Implemented** | `POST /api/v1/telemetry` raw discrete signal ingestion, validator, & processing pipeline (`backend/app/api/routes/telemetry.py`) |
| **Event Ingestion API** | **Implemented** | `POST /api/v1/events` and `GET /api/v1/events/{id}` for pre-detected events (`backend/app/api/routes/events.py`) |
| **Signal Processing Engine** | **Implemented** | Mean-subtraction DC offset removal, moving average, Butterworth lowpass filtering, event window detection, and FFT feature extraction (`backend/app/processing/`) |
| **Statistical Baseline Engine** | **Implemented** | Zone-specific historical baseline calculation (mean and standard deviation for magnitude & energy, normal rate, min-data validation) (`backend/app/baseline/`) |
| **Rule-Based Anomaly Engine** | **Implemented** | Z-score deviation comparison (`|z| >= 3.0` sigma), zero-variance baseline handling, and evidence generation (`backend/app/anomaly/`) |
| **Temporal Persistence** | **Implemented** | Rolling window persistence evaluation, anomaly ratio, consecutive anomalies, and window boundary checks (`backend/app/correlation/temporal.py`) |
| **Two-PZT Event Correlation** | **Implemented** | Cross-sensor event correlation across 25ms tolerance, TDOA spread, and relative source indication (`backend/app/correlation/sensor_correlation.py`) |
| **Evidence Aggregation** | **Implemented** | Unified classification (`NORMAL_OBSERVATION` to `PERSISTENT_AND_CROSS_SENSOR_CORRELATED`) (`backend/app/correlation/evidence.py`) |
| **Deterministic Trend Analysis** | **Implemented** | Directional trend evaluation (`STABLE`, `INCREASING`, `DECREASING`, `INSUFFICIENT_DATA`) comparing sub-periods (`backend/app/trend/`) |
| **Structural Health Indicator (SHI)** | **Implemented** | Deterministic 0–100 prototype monitoring score, itemized deductions, and `HealthStatus` mapping (`backend/app/health/`) |
| **HealthSnapshot Persistence** | **Implemented** | Database persistence of health score, status, trend, reason, and evidence dict (`backend/app/services/health_service.py`) |
| **Monitoring & Health REST APIs** | **Implemented** | Exposes REST endpoints for Zone listing, Zone detail, Zone events, SHI health, trend, correlation, alerts, and dashboard summary (`backend/app/api/routes/`) |
| **Automated Test Suite** | **Implemented** | **164 passed / 1 warning** pytest unit & integration tests (`backend/tests/`) |
| **BIM/IFC Metadata Pipeline** | **Implemented** | Offline IFC extraction of structural elements, GLB node mapping, and canonical `zone_bim_mapping.json` (`data/processed/bim/`) |
| **3D Building Model Asset** | **Implemented** | 3D GLB structural asset (`models/glb/building_demo.glb`) |
| **Browser 3D BIM Viewer** | **Implemented** | Three.js / React Three Fiber building viewer integrated with zone health & BIM highlighting (`frontend/components/building/BuildingViewer.tsx`) |
| **GIS City Map Component** | **Implemented** | Next.js 14 MapLibre GL 2.5D city map consuming `delhi_buildings.json` (`frontend/components/dashboard/CityMap.tsx`) |
| **Virtual Sensor Simulator** | *Upcoming* | Prototype telemetry stream generator for virtual sensor simulation |
| **ESP32 Firmware & Hardware** | *Scaffolded* | PlatformIO structure & PCB schematics (`firmware/`, `hardware/`) |

---

## Implemented Processing & Data Flow Pipeline

```text
[ Telemetry Ingestion (POST /api/v1/telemetry) / Discrete Signal Input ]
                 │
                 ▼
[ 1. Preprocessing ] ──────────────► Mean-subtraction DC offset removal & peak amplitude normalization (`SampledSignal`)
                 │
                 ▼
[ 2. Filtering ] ──────────────────► Butterworth lowpass filter (`scipy.signal`) & moving average
                 │
                 ▼
[ 3. Event Detection ] ────────────► Amplitude thresholding, sample windowing, min-duration & gap merging (`process_signal_pipeline`)
                 │
                 ▼
[ 4. Feature Extraction ] ─────────► Peak amplitude, RMS amplitude, Discrete Signal Energy, FFT Dominant Frequency
                 │
                 ▼
[ 5. Event Persistence ] ──────────► DB persistence of detected activity window events (`EventRepository` / `EventService`)
                 │
                 ▼
[ 6. Statistical Baseline ] ───────► Zone-specific historical mean & standard deviation for magnitude & energy
                 │
                 ▼
[ 7. Anomaly Detection ] ──────────► Rule-based standardized deviation (|z| >= 3.0 sigma) & zero-variance handling (`AnomalyService`)
                 │
                 ▼
[ 8. Temporal Persistence ] ───────► Rolling observation window (300s), anomaly ratio, max consecutive anomalies (`CorrelationService`)
                 │
                 ▼
[ 9. 2-PZT Sensor Correlation ] ────► 25ms cross-sensor time-difference-of-arrival (TDOA) correlation & relative source hint
                 │
                 ▼
[ 10. Evidence Aggregation ] ────────► Evidence classification (NORMAL_OBSERVATION to PERSISTENT_AND_CROSS_SENSOR_CORRELATED)
                 │
                 ▼
[ 11. Deterministic Trend Analysis ] ► Window sub-period comparison (STABLE, INCREASING, DECREASING, INSUFFICIENT_DATA) (`TrendService`)
                 │
                 ▼
[ 12. Structural Health Indicator ] ► Deterministic 0–100 score, itemized deductions, and HealthStatus classification (`HealthService`)
                 │
                 ▼
[ 13. HealthSnapshot & Alert ] ────► DB persistence for health snapshot, trend, and automated alert evaluation
                 │
                 ▼
[ 14. FastAPI REST API Layer ] ─────► Exposes telemetry, events, zones, health, trend, correlation, alerts & summary endpoints
                 │
                 ▼
[ 15. 3D Digital Twin & GIS Map ] ──► R3F 3D viewer highlighting mapped BIM components & Next.js MapLibre GIS map
```

---

## Detailed Component Specifications

### 1. Signal Processing Foundation (`backend/app/processing/`)
- **`SampledSignal`**: Immutable 1D signal container enforcing positive sample rates (`sample_rate > 0`) and validating against `NaN`/`Inf`.
- **Preprocessing**: Mean-subtraction DC offset removal preserving signal metadata.
- **Filtering**: Moving average filter (`mode="same"`) and Butterworth lowpass filter (`scipy.signal.butter` / `filtfilt`) with Nyquist boundary checks.
- **Event Detection**: Amplitude thresholding identifying active sample windows, filtering transient noise (`min_duration_samples`), and merging sub-threshold gaps (`merge_gap_samples`).
- **Feature Extraction**:
  - **Peak Amplitude**: `max(|x[n]|)`
  - **RMS Amplitude**: Root Mean Square of sampled amplitudes
  - **Discrete Signal Energy**: `sum(x[n]^2)` (*Note: Digital signal metric, not physical joules*)
  - **Duration & Sample Count**: Window duration in milliseconds and sample count.
  - **Dominant Frequency**: Real FFT spectrum analysis (`np.fft.rfft`) with zero-padding and DC bin exclusion.

### 2. Zone Statistical Baseline Engine (`backend/app/baseline/`)
- Computes zone-specific historical baseline parameters over a date window `[valid_from, valid_until]`.
- Calculates arithmetic mean and population standard deviation (`ddof=0`) for event magnitude and signal energy.
- Calculates normal historical event rate (events per second).
- Requires minimum qualifying events (`DEFAULT_MIN_EVENTS = 10`) and excludes `DISMISSED` events.

### 3. Rule-Based Anomaly Detection (`backend/app/anomaly/`)
- Computes standardized z-scores for magnitude and energy:
  ```text
  z_magnitude = (magnitude - mean_magnitude) / std_magnitude
  z_energy    = (energy - mean_energy) / std_energy
  ```
- Evaluates absolute deviation against configurable threshold (`|z| >= 3.0` sigma).
- Evaluates magnitude and energy independently (`is_anomalous = mag_anomalous or eng_anomalous`).
- **Zero-Standard-Deviation Handling**: When baseline standard deviation is zero (`std = 0`):
  - Event value equals mean $\implies z = 0.0$, normal.
  - Event value differs from mean $\implies z = 0.0$, flagged anomalous with explainable zero-variance evidence.
  - Strictly avoids `NaN`, `infinity`, or division-by-zero errors.

### 4. Temporal Persistence Evaluation (`backend/app/correlation/temporal.py`)
- Evaluates anomaly sequence over a rolling observation window (default `300.0` seconds).
- Computes total events, anomalous events, anomaly ratio (`anomalous events / total events`), and max consecutive anomalous events.
- Persistence satisfied when BOTH conditions hold:
  ```text
  anomalous event count >= min_count (default: 3)
  AND
  anomaly ratio >= min_ratio (default: 0.50)
  ```

### 5. Two-PZT Sensor Event Correlation (`backend/app/correlation/sensor_correlation.py`)
- Correlates events across two distinct PZT sensors within a configurable temporal tolerance window (default `25` ms).
- Computes temporal spread in milliseconds (`delta_t = |t2 - t1|`) and relative arrival time difference.
- Generates relative source indication hints (e.g. `"Event arrived first at sensor PZT-01 (lead time: 4.20 ms relative to PZT-02)"`).
- *Note*: Provides relative source arrival order along a 2-sensor axis, **NOT** precise 2D or 3D spatial triangulation.

### 6. Evidence Aggregation (`backend/app/correlation/evidence.py`)
Aggregates anomaly, persistence, and correlation into standardized classifications:
- `NORMAL_OBSERVATION`: Event within normal baseline bounds.
- `INDIVIDUAL_ANOMALY`: Isolated anomaly without persistence or cross-sensor correlation.
- `PERSISTENT_ANOMALY`: Anomaly meeting rolling-window temporal persistence criteria.
- `CROSS_SENSOR_CORRELATED`: Anomaly detected across 2+ sensors within tolerance window.
- `PERSISTENT_AND_CROSS_SENSOR_CORRELATED`: Anomaly meeting both persistence and multi-sensor correlation.

### 7. Deterministic Trend Analysis (`backend/app/trend/`)
- Divides a configurable analysis window (default `3600.0` seconds) into two contiguous sub-periods:
  - **Earlier Sub-Period**: `[window_start, midpoint)`
  - **Later Sub-Period**: `[midpoint, window_end]`
- Calculates normalized anomaly rate (`anomalous events / total events`) for each sub-period and computes delta (`rate_delta = rate_later - rate_earlier`).
- Evaluates directional trend classification:
  - `INCREASING`: Anomaly rate delta `>= threshold` (default: 0.10) or magnitude/evidence rising.
  - `DECREASING`: Anomaly rate declining toward baseline.
  - `STABLE`: Anomaly rate and magnitude remain within tolerance.
  - `INSUFFICIENT_DATA`: Fewer than `min_events_per_period` (default: 2) in either sub-period. *Preserves data uncertainty without artificial penalties.*
- Identifies and documents divergent component trends (e.g. rate increasing while magnitude decreases).

### 8. Structural Health Indicator (SHI) (`backend/app/health/`)
- Converts accumulated evidence from Steps 7–9 into a deterministic prototype score bounded strictly to the range `0–100`:
  ```text
  raw_score = base_score - (anomaly_penalty + persistence_penalty + cross_sensor_penalty + trend_penalty)
  score = clamp(raw_score, 0, 100)
  ```
- Default prototype configuration:
  - `base_score = 100.0`
  - `anomaly_penalty = 15.0` (applied for individual anomaly activity)
  - `persistence_penalty = 20.0` (applied for Step 8 temporal persistence)
  - `cross_sensor_penalty = 25.0` (applied for Step 8 cross-sensor correlation)
  - `increasing_trend_penalty = 15.0` (applied for Step 9 `INCREASING` trend)
- Prototype Status Mapping:
  - `score >= 90.0` $\implies$ `HealthStatus.NORMAL`
  - `70.0 <= score < 90.0` $\implies$ `HealthStatus.MONITOR`
  - `45.0 <= score < 70.0` $\implies$ `HealthStatus.INSPECTION_ADVISED`
  - `score < 45.0` $\implies$ `HealthStatus.HIGH_PRIORITY_INSPECTION`
- *Note*: Score boundaries and penalty weights are prototype monitoring parameters, NOT certified structural safety thresholds.

### 9. Telemetry Ingestion Contract & Existing Processing Pipeline (`POST /api/v1/telemetry`)
The telemetry ingestion capability exposes an endpoint for accepting raw or representative sampled sensor signals and running them directly through the existing backend processing pipeline.

- **`POST /api/v1/telemetry`**: Ingests raw/representative discrete sensor telemetry, preprocesses signal data via `SampledSignal`, detects structural activity windows using `process_signal_pipeline`, extracts spectral & temporal features, persists detected events (`EventRepository`/`EventService`), evaluates baseline z-score anomalies (`AnomalyService`), computes temporal persistence & 2-PZT cross-sensor correlation (`CorrelationService`), updates zone trend indicators (`TrendService`), evaluates Structural Health Indicators (`HealthService`), updates zone health state, and evaluates system alerts.

#### Conceptual Distinction
- **`/api/v1/telemetry`**: Accepts **incoming sampled sensor telemetry** (1D amplitude array and sample rate). The backend intelligence engine independently determines if events or anomalies exist within the signal.
- **`/api/v1/events`**: Accepts or queries **already-detected structural events**.

#### Ingestion Contract Schema (`TelemetryIngestRequest`)
```json
{
  "sensor_id": "PZT-Z1-01",
  "zone_name": "Zone 1 - Main Deck Girder",
  "timestamp": "2026-09-28T12:00:00Z",
  "sample_rate_hz": 1000.0,
  "sequence": 101,
  "samples": [0.012, 0.045, -0.023, 0.850, 1.230, -0.950, 0.015, -0.005],
  "detection_threshold": 0.50,
  "session_id": 1
}
```

#### Response Contract Schema (`TelemetryIngestResponse`)
```json
{
  "status": "success",
  "telemetry_accepted": true,
  "sensor_id": "PZT-Z1-01",
  "zone_id": 1,
  "zone_name": "Zone 1 - Main Deck Girder",
  "timestamp": "2026-09-28T12:00:00Z",
  "samples_count": 8,
  "sample_rate_hz": 1000.0,
  "sequence": 101,
  "events_detected": 1,
  "events": [
    {
      "event_id": 42,
      "magnitude": 1.23,
      "energy": 2.85,
      "duration_ms": 5.0,
      "frequency_hz": 125.0,
      "severity": "MODERATE",
      "is_anomalous": true,
      "magnitude_z_score": 3.42,
      "energy_z_score": 3.10,
      "anomaly_reasons": ["Magnitude z-score +3.42 exceeds threshold (+3.00)"]
    }
  ],
  "extracted_features": {
    "peak_amplitude": 1.23,
    "rms_amplitude": 0.597,
    "energy": 2.85,
    "duration_ms": 8.0,
    "frequency_hz": 125.0,
    "sample_count": 8
  },
  "temporal_persistence_confirmed": false,
  "cross_sensor_correlation_confirmed": false,
  "health_score": 85.0,
  "health_status": "MONITOR",
  "health_trend": "STABLE",
  "alert_generated": false,
  "alert_id": null,
  "alert_severity": null,
  "alert_title": null,
  "message": "Telemetry processed successfully: 1 event(s) detected, health updated to MONITOR (85.0)."
}
```

#### Pipeline Integration & Component Reuse
Rather than creating a parallel execution path, telemetry ingestion reuses existing domain repositories, models, and service components:
- `SampledSignal` for signal validation and mean-subtraction DC offset removal
- `process_signal_pipeline` for windowing, Butterworth filtering, and FFT feature extraction
- `EventRepository` & `EventService` for event persistence (reusing existing PostgreSQL models)
- `AnomalyService` for statistical z-score evaluation against zone baselines
- `CorrelationService` for rolling temporal persistence and 2-PZT cross-sensor correlation
- `TrendService` & `HealthService` for deterministic SHI score evaluation and persistence
- **Zero Database Schema Migrations**: Ingestion requires no new database tables or schema changes; existing PostgreSQL models are fully reused.

---

### 10. Step 11 — Monitoring & Health REST API Layer (`backend/app/api/routes/`)
Step 11 exposes all existing backend intelligence through clean, frontend-consumable REST endpoints:

- **`POST /api/v1/telemetry`**: Ingests raw sensor telemetry signal arrays, executes processing pipeline, persists detected events, updates zone health, and returns structured processing results (`TelemetryIngestResponse`).
- **`GET /api/v1/zones`**: Returns all monitoring zones (`ZoneResponse`).
- **`GET /api/v1/zones/{zone_id}`**: Returns zone detail metadata (`ZoneDetailResponse`), including total event count, active alert count, and latest health status. Returns `404` if zone does not exist.
- **`GET /api/v1/zones/{zone_id}/events`**: Returns zone event observations (`List[EventResponse]`) with filtering (`limit`, `start_time`, `end_time`, `severity`, `status`). Returns `404` if zone does not exist.
- **`GET /api/v1/zones/{zone_id}/health`**: Returns latest Structural Health Indicator score, status, trend, reason, timestamp, evidence payload, and embedded safety disclaimer (`ZoneHealthResponse`). Returns `404` if zone does not exist.
- **`GET /api/v1/zones/{zone_id}/trend`**: Exposes Step 9 deterministic trend analysis (`ZoneTrendResponse`), returning overall trend direction (`STABLE`, `INCREASING`, `DECREASING`, `INSUFFICIENT_DATA`), rate delta, magnitude delta, and sub-period metrics. Returns `404` if zone does not exist.
- **`GET /api/v1/zones/{zone_id}/correlation`**: Exposes Step 8 temporal persistence and 2-PZT cross-sensor correlation groups (`ZoneCorrelationResponse`), with relative arrival hints and explicit non-localization note. Returns `404` if zone does not exist.
- **`GET /api/v1/alerts`**: Returns actionable system alerts (`List[AlertResponse]`) with optional filtering (`zone_id`, `status`, `severity`, `limit`).
- **`GET /api/v1/health/summary`**: Provides high-level dashboard health summary (`HealthSummaryResponse`), aggregating total zones, status counts, active alerts, recent events, and latest timestamp.

**Key Step 11 Architectural Properties**:
- **Zero Business Logic Duplication**: Endpoints delegate to `MonitoringService` and `TelemetryService`, which reuse `HealthService`, `TrendService`, `CorrelationService`, `AnomalyService`, and `EventService`.
- **Unmodified Intelligence Algorithms**: Step 6–10 algorithms, thresholds, SHI formulas, correlation tolerances, and trend rules were **not** modified.
- **Zero Database Schema Changes**: No database schema modifications or migrations were required. Existing `Zone`, `Event`, `HealthSnapshot`, and `Alert` PostgreSQL models cleanly support all REST operations.

---

## Mandatory SHI Limitation Disclaimer

Every `StructuralHealthResult` and `ZoneHealthResponse` output embeds the following mandatory safety disclaimer:

> **"SHI is a prototype evidence-based monitoring indicator derived from observed signal/event behavior. It is not a certified structural safety score and does not independently establish structural damage or failure."**

Aegis3D explicitly does **NOT**:
- Predict structural collapse or catastrophic failure
- Independently diagnose physical cracks or material fatigue
- Replace physical on-site structural engineering inspections
- Provide legal or certified structural safety guarantees

---

## Hardware & Frontend Integration Status

### Hardware Integration Status
- **Planned Input Architecture**: 2 × PZT sensors $\rightarrow$ Analog Signal Conditioning $\rightarrow$ ESP32 ADC $\rightarrow$ Wi-Fi/MQTT $\rightarrow$ Aegis3D backend API.
- **Current Status**: ESP32 PlatformIO firmware and PCB schematics are scaffolded in `firmware/` and `hardware/`. Physical PZT acquisition is not yet fully integrated into the backend pipeline.
- **Backend Independence**: The signal processing, baseline, anomaly, correlation, trend, SHI, and REST API modules operate seamlessly on simulated, imported, or sampled signal data without physical hardware dependencies.

### Frontend Dashboard Status
- **Current Status**: Next.js 14 dashboard application shell is implemented in `frontend/`, featuring a 2.5D MapLibre GL city map component (`CityMap.tsx`) rendering Delhi building footprint polygons (`delhi_buildings.json`).
- **Next Phases**: Connecting client-side React components to Step 11 backend REST APIs, building the browser-side 3D BIM component viewer (`BuildingViewer.tsx`), and adding real-time event updates.

---

## Backend Software Architecture & Directory Tree

```text
Aegis3D/
├── docker-compose.yml           # PostgreSQL 15 & Mosquitto MQTT Docker containers
├── .env.example                 # Environment configuration template
├── README.md                    # Project technical documentation
├── backend/
│   ├── requirements.txt         # FastAPI, SQLAlchemy, SciPy, NumPy, Matplotlib
│   ├── alembic.ini              # Alembic database migration config
│   ├── app/
│   │   ├── main.py              # FastAPI app initialization & router setup
│   │   ├── api/                 # REST router registration
│   │   │   └── routes/          # REST endpoints (health.py, telemetry.py, events.py, zones.py, alerts.py, monitoring.py)
│   │   ├── db/                  # Session provider, Base engine, Alembic migrations
│   │   ├── models/              # Zone, MonitoringSession, Event, Baseline, HealthSnapshot, Alert
│   │   ├── schemas/             # Pydantic schemas (telemetry.py, event.py, zone.py, alert.py, health.py)
│   │   ├── repositories/        # EventRepository, BaselineRepository
│   │   ├── services/            # TelemetryService, EventService, BaselineService, AnomalyService, CorrelationService, TrendService, HealthService, MonitoringService
│   │   ├── processing/          # Signal filtering, window detection & FFT feature extraction
│   │   ├── baseline/            # Pure zone statistical baseline calculation engine
│   │   ├── anomaly/             # Pure z-score anomaly detection engine
│   │   ├── correlation/         # Temporal persistence, 2-PZT correlation & evidence aggregation
│   │   ├── trend/               # Sub-period trend analysis calculation engine
│   │   └── health/              # Pure Structural Health Indicator (SHI) calculation engine
│   ├── scripts/
│   │   └── demo_signal_processing.py  # Executable signal processing visual demo
│   └── tests/                   # Complete backend pytest test suite (164 passed, 1 warning)
│       ├── test_signal_processing.py
│       ├── test_baseline.py
│       ├── test_anomaly.py
│       ├── test_correlation.py
│       ├── test_trend.py
│       ├── test_shi.py
│       ├── test_api_telemetry.py # Telemetry ingestion contract & processing pipeline tests
│       ├── test_api_events.py
│       ├── test_api_health.py
│       ├── test_api_monitoring.py
│       ├── test_db_config.py
│       └── test_models.py
├── firmware/esp32/              # ESP32 PlatformIO firmware scaffolding
├── frontend/                    # Next.js 14 frontend dashboard, 3D BIM Viewer & MapLibre GL GIS city map
├── hardware/                    # PCB layout, BOM, schematics scaffolding
├── docs/                        # Architecture diagrams and BIM_ARCHITECTURE.md
└── data/                        # Signal and BIM data storage directories
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
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

### 4. Setup Virtual Environment & Install Dependencies
```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\activate

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Start FastAPI Development Server
```bash
uvicorn app.main:app --reload
```

Verify endpoints:
- **API Liveness Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database Readiness Check**: [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)
- **Telemetry Ingestion**: `POST http://127.0.0.1:8000/api/v1/telemetry`
- **List Zones**: [http://127.0.0.1:8000/api/v1/zones](http://127.0.0.1:8000/api/v1/zones)
- **Health Summary**: [http://127.0.0.1:8000/api/v1/health/summary](http://127.0.0.1:8000/api/v1/health/summary)
- **List Alerts**: [http://127.0.0.1:8000/api/v1/alerts](http://127.0.0.1:8000/api/v1/alerts)

---

## Running Verification Commands

### 1. Run Complete Backend Test Suite
```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/
```
*Expected Result*: **`164 passed, 1 warning`** across all test modules.

### 2. Run Signal Processing Visual Demonstration
```bash
cd backend
.\.venv\Scripts\python.exe scripts/demo_signal_processing.py
```
*Expected Result*: Executes full 5-stage signal processing pipeline on synthetic burst signals and generates visualization plot in `data/processed/step5_signal_demo.png`.

---

## Validation Strategy

### Testing Methodology
Aegis3D validates algorithm behavior using synthetic, imported, and controlled signal datasets:
- **Baseline Datasets**: Background structural mechanical noise without burst events.
- **Environmental Noise Datasets**: Non-structural transient noise spikes (e.g. door closures, footsteps).
- **Controlled Stress Event Datasets**: High-amplitude acoustic burst signals simulating mechanical stress wave releases.

### Planned Physical Benchtop Metrics
As physical hardware coupling progresses, Aegis3D will evaluate:
- **Event Detection Latency**: Processing time from raw sample ingestion to backend anomaly & health result.
- **False Positive Separation**: Statistical separation (`delta_z`) between normal baseline noise and true anomaly events.
- **TDOA Arrival Accuracy**: Precision of relative arrival time lead/lag estimation between 2 PZT sensors.

---

## Software-First Milestone Roadmap

### Implemented Backend Capabilities (**Completed**)
- [x] **Step 1**: Core domain models & schema design
- [x] **Step 2**: PostgreSQL database persistence & Alembic migrations
- [x] **Step 3**: FastAPI REST foundation & health endpoints
- [x] **Step 4**: Event ingestion REST API (`POST /api/v1/events`)
- [x] **Step 5**: Signal processing engine (DC offset, Butterworth filtering, windowing, FFT extraction)
- [x] **Step 6**: Zone statistical baseline engine (mean, standard deviation, event rate)
- [x] **Step 7**: Rule-based z-score anomaly detection engine (`|z| >= 3.0` sigma, zero-variance handling)
- [x] **Step 8**: Temporal persistence evaluation, 2-PZT cross-sensor correlation & evidence aggregation
- [x] **Step 9**: Deterministic zone trend analysis engine (`STABLE`, `INCREASING`, `DECREASING`, `INSUFFICIENT_DATA`)
- [x] **Step 10**: Deterministic Structural Health Indicator (SHI 0–100 score, itemized deductions, `HealthSnapshot`)
- [x] **Step 11**: Monitoring & Structural Health REST API integration endpoints (zones, health, trend, correlation, alerts, summary)
- [x] **Backend Step 3A/3B**: Telemetry Ingestion Contract & Existing Processing Pipeline (`POST /api/v1/telemetry`)

### Future Milestones (**Next Development Stages**)
- [ ] **Virtual Sensor Simulator**: Stream representative telemetry signals to `POST /api/v1/telemetry` for end-to-end testing
- [ ] **Frontend Live Telemetry Visualization**: Connect client dashboard cards to live telemetry ingestion results and streaming health status
- [ ] **3D Digital Twin Dynamic Highlighting**: Interactive real-time component color transitions based on live health score updates in `BuildingViewer.tsx`
- [ ] **ESP32 Firmware & ADC Sampling**: Firmware completion for physical PZT ADC sampling and benchtop testing
- [ ] **MQTT Live Ingestion Adapter**: Broker integration for hardware stream forwarding to backend API
- [ ] **Multi-level Alert Escalation**: Escalation workflows for persistent multi-zone anomalies
