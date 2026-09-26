# Aegis3D

## Smart PZT-Based Structural Health Monitoring & Early-Warning System

### Team BRIKS
- **Maulik Pandey**
- **Shikhar Sadhu**
- **Pratyush Bhaskar Ram**
- **Madhav Kumar**

**MAITRON 2026** | **Software Track**  
**Primary SDG**: SDG 11 — Sustainable Cities and Communities  
**Secondary SDG**: SDG 9 — Industry, Innovation and Infrastructure

---

## Overview

**Aegis3D** is a software-centric structural health monitoring (SHM) and early-warning platform with an optional physical piezoelectric transducer (PZT) sensing input layer. The platform observes structural acoustic and mechanical wave activity in buildings and infrastructure to detect anomalous behavior, evaluate multi-event persistence, correlate multi-sensor arrival times, analyze directional trend trajectories, and compute an explainable prototype Structural Health Indicator (SHI).

While PZT sensors and ESP32 microcontrollers form the planned physical sensing layer, Aegis3D is strictly **Software-First**. All core intelligence—DC offset removal, Butterworth lowpass filtering, threshold-based event detection, FFT feature extraction, zone statistical baselines, z-score anomaly detection, temporal persistence evaluation, 2-PZT time-difference-of-arrival correlation, directional trend analysis, and SHI scoring—is executed by pure, hardware-agnostic Python software modules. The backend functions seamlessly whether fed by live ESP32 streams, imported historical sensor logs, or synthetic signal sources.

> **Crucial Technical Disclaimer**: Aegis3D is a continuous monitoring and early-warning software platform. It does **NOT** use machine learning inference, predict structural collapse, guarantee disaster prevention, replace licensed structural engineers, or provide certified engineering safety assessments. Piezoelectric Transducers (PZTs) capture acoustic and mechanical stress waves within materials; they do not directly "see" cracks. Human engineering inspection remains mandatory for actual structural diagnosis.

---

## Role of Hardware in a Software-First Architecture

Aegis3D treats physical hardware strictly as an optional data ingestion adapter:
- **Input Mechanism**: Physical PZT sensors and ESP32 microcontrollers serve as data collection nodes feeding voltage samples into the backend API or MQTT broker.
- **Hardware-Agnostic Intelligence**: All signal processing, feature extraction, statistical baseline comparison, correlation, trend, and health indicator modules are decoupled from specific microcontrollers, sensor hardware, or database ORMs.
- **Data Source Versatility**: Aegis3D evaluates signal inputs identically regardless of whether they originate from physical sensors, imported datasets, or simulator engines.

---

## Key Design Principles

1. **Software-Centric & Hardware-Agnostic**: Signal processing, baseline, anomaly, correlation, trend, and health evaluation logic remain pure Python modules.
2. **Zero Machine Learning**: Aegis3D deliberately uses deterministic signal processing, standard deviation metrics, standardized z-scores, rolling window metrics, and rule-based thresholds instead of black-box AI/ML models.
3. **Explainable Evidence**: All anomaly flags, persistence evaluations, correlation groups, trends, and health scores produce itemized, human-readable evidence statements explaining why a result was produced.
4. **Relational Domain Integrity**: Standardized PostgreSQL database schema storing structural zones, monitoring sessions, events, baselines, health snapshots, and alerts with foreign key constraints.

---

## Current Implementation Status

| Component | Status | Description / Location |
| :--- | :--- | :--- |
| **Domain Models & Schemas** | **Implemented** | Core SQLAlchemy models (`Zone`, `MonitoringSession`, `Event`, `Baseline`, `HealthSnapshot`, `Alert`) & Pydantic DTOs (`backend/app/models/`, `backend/app/schemas/`) |
| **PostgreSQL Persistence** | **Implemented** | Environment-based DB configuration, SQLAlchemy 2.0 session layer, and Alembic migrations (`backend/app/db/`) |
| **FastAPI REST Foundation** | **Implemented** | API foundation with liveness `/health` and DB readiness `/health/db` endpoints (`backend/app/api/routes/health.py`) |
| **Event Ingestion API** | **Implemented** | `POST /api/v1/events` and `GET /api/v1/events/{id}` with validation & service orchestration (`backend/app/api/routes/events.py`) |
| **Signal Processing Engine** | **Implemented** | Mean-subtraction DC offset removal, moving average, Butterworth lowpass filtering, event window detection, and FFT feature extraction (`backend/app/processing/`) |
| **Statistical Baseline Engine** | **Implemented** | Zone-specific historical baseline calculation (mean and standard deviation for magnitude & energy, normal rate, min-data validation) (`backend/app/baseline/`) |
| **Rule-Based Anomaly Engine** | **Implemented** | Z-score deviation comparison (`|z| >= 3.0` sigma), zero-variance baseline handling, and evidence generation (`backend/app/anomaly/`) |
| **Temporal Persistence** | **Implemented** | Rolling window persistence evaluation, anomaly ratio, consecutive anomalies, and window boundary checks (`backend/app/correlation/temporal.py`) |
| **Two-PZT Event Correlation** | **Implemented** | Cross-sensor event correlation across 25ms tolerance, TDOA spread, and relative source indication (`backend/app/correlation/sensor_correlation.py`) |
| **Evidence Aggregation** | **Implemented** | Unified classification (`NORMAL_OBSERVATION` to `PERSISTENT_AND_CROSS_SENSOR_CORRELATED`) (`backend/app/correlation/evidence.py`) |
| **Deterministic Trend Analysis** | **Implemented** | Directional trend evaluation (`STABLE`, `INCREASING`, `DECREASING`, `INSUFFICIENT_DATA`) comparing sub-periods (`backend/app/trend/`) |
| **Structural Health Indicator (SHI)** | **Implemented** | Deterministic 0–100 prototype monitoring score, itemized deductions, and `HealthStatus` mapping (`backend/app/health/`) |
| **HealthSnapshot Persistence** | **Implemented** | Database persistence of health score, status, trend, reason, and evidence dict (`backend/app/services/health_service.py`) |
| **Automated Test Suite** | **Implemented** | **128 passed** pytest unit & integration tests (`backend/tests/`) |
| **Next.js Dashboard Interface** | *Scaffolded* | Visual dashboard interface structure (`frontend/`) |
| **ESP32 Firmware** | *Scaffolded* | PlatformIO structure for ADC sampling & MQTT (`firmware/esp32/`) |
| **Hardware PCB & Schematics** | *Scaffolded* | Schematic & PCB layout documentation (`hardware/`) |
| **Physical PZT Benchtop Setup** | *Planned* | Controlled physical benchtop validation with physical sensor hardware |

---

## Implemented Processing & Intelligence Pipeline

```text
[ Raw Signal / Ingestion Input ]
                 │
                 ▼
[ 1. Preprocessing ] ──────────────► Mean-subtraction DC offset removal & peak amplitude normalization
                 │
                 ▼
[ 2. Filtering ] ──────────────────► Butterworth lowpass filter (scipy.signal) & moving average
                 │
                 ▼
[ 3. Event Detection ] ────────────► Amplitude thresholding, sample windowing, min-duration & gap merging
                 │
                 ▼
[ 4. Feature Extraction ] ─────────► Peak amplitude, RMS amplitude, Discrete Signal Energy, FFT Dominant Frequency
                 │
                 ▼
[ 5. Statistical Baseline ] ───────► Zone-specific historical mean & standard deviation for magnitude & energy
                 │
                 ▼
[ 6. Anomaly Detection ] ──────────► Rule-based standardized deviation (|z| >= 3.0 sigma) & zero-variance handling
                 │
                 ▼
[ 7. Temporal Persistence ] ───────► Rolling observation window (300s), anomaly ratio, max consecutive anomalies
                 │
                 ▼
[ 8. 2-PZT Sensor Correlation ] ────► 25ms cross-sensor time-difference-of-arrival (TDOA) correlation & relative source hint
                 │
                 ▼
[ 9. Evidence Aggregation ] ────────► Evidence classification (NORMAL_OBSERVATION to PERSISTENT_AND_CROSS_SENSOR_CORRELATED)
                 │
                 ▼
[ 10. Deterministic Trend Analysis ] ► Window sub-period comparison (STABLE, INCREASING, DECREASING, INSUFFICIENT_DATA)
                 │
                 ▼
[ 11. Structural Health Indicator ] ► Deterministic 0–100 score, itemized deductions, and HealthStatus classification
                 │
                 ▼
[ 12. HealthSnapshot Persistence ] ─► Database snapshot persistence for monitoring session & zone history
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

---

## Mandatory SHI Limitation Disclaimer

Every `StructuralHealthResult` output embeds the following mandatory safety disclaimer:

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
- **Backend Independence**: The signal processing, baseline, anomaly, correlation, trend, and SHI modules operate seamlessly on simulated, imported, or sampled signal data without physical hardware dependencies.

### Frontend Dashboard Status
- **Current Status**: Next.js dashboard framework is scaffolded in `frontend/`.
- **Planned Dashboard Features**: Real-time event monitoring, zone health status overview, historical trend visualization, inspection logs, and 3D digital-twin BIM zone view.

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
│   │   ├── api/routes/          # REST endpoints (/health, /api/v1/events)
│   │   ├── db/                  # Session provider, Base engine, Alembic migrations
│   │   ├── models/              # Zone, MonitoringSession, Event, Baseline, HealthSnapshot, Alert
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── repositories/        # EventRepository, BaselineRepository
│   │   ├── services/            # EventService, BaselineService, AnomalyService, CorrelationService, TrendService, HealthService
│   │   ├── processing/          # Signal filtering, window detection & FFT feature extraction
│   │   ├── baseline/            # Pure zone statistical baseline calculation engine
│   │   ├── anomaly/             # Pure z-score anomaly detection engine
│   │   ├── correlation/         # Temporal persistence, 2-PZT correlation & evidence aggregation
│   │   ├── trend/               # Sub-period trend analysis calculation engine
│   │   └── health/              # Pure Structural Health Indicator (SHI) calculation engine
│   ├── scripts/
│   │   └── demo_signal_processing.py  # Executable signal processing visual demo
│   └── tests/                   # Complete backend pytest test suite (128 passing tests)
│       ├── test_signal_processing.py
│       ├── test_baseline.py
│       ├── test_anomaly.py
│       ├── test_correlation.py
│       ├── test_trend.py
│       ├── test_shi.py
│       ├── test_api_events.py
│       ├── test_api_health.py
│       ├── test_db_config.py
│       └── test_models.py
├── firmware/esp32/              # ESP32 PlatformIO firmware scaffolding
├── frontend/                    # Next.js frontend dashboard scaffolding
├── hardware/                    # PCB layout, BOM, schematics scaffolding
├── docs/                        # Architecture diagrams and documentation
└── data/                        # Signal data storage directories
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

---

## Running Verification Commands

### 1. Run Complete Backend Test Suite
```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/
```
*Expected Result*: **`128 passed in ~2.0s`** (100% pass rate across 10 test modules).

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

### Steps 1–10 (**Completed**)
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

### Future Milestones (**Next Phases**)
- [ ] **Step 11**: Monitoring & Structural Health REST API integration endpoints
- [ ] **Step 12**: Next.js real-time monitoring dashboard interface
- [ ] **Step 13**: Interactive simulation & demo data streaming workflow
- [ ] **Step 14**: 3D BIM structural digital twin visualization
- [ ] **Step 15**: ESP32 PlatformIO firmware ADC sampling completion & benchtop testing
- [ ] **Step 16**: MQTT live ingestion adapter integration
- [ ] **Step 17**: Multi-level alert creation & escalation workflow
