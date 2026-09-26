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

**Aegis3D** is a software-centric structural health monitoring (SHM) and early-warning platform with an optional physical piezoelectric transducer (PZT) sensing layer. The platform observes structural acoustic and elastic wave activity in buildings and infrastructure to detect anomalous behavior and flag specific locations requiring physical inspection.

While PZT sensors and ESP32 microcontrollers form the physical sensing input layer, the core innovation and execution of Aegis3D are software-driven. The backend performs deterministic signal processing, noise filtering, event window detection, feature extraction, statistical baseline calculation, and rule-based anomaly detection. The architecture remains hardware-agnostic throughout: the software platform functions seamlessly whether fed by live ESP32 microcontrollers, recorded sensor datasets, or simulated signal sources.

> **Crucial Technical Disclaimer**: Aegis3D is a continuous monitoring and early-warning software platform. It does **NOT** use machine learning inference, predict structural collapse, guarantee disaster prevention, replace licensed structural engineers, or provide certified engineering safety assessments. Piezoelectric Transducers (PZTs) capture acoustic, mechanical, and elastic stress waves within materials; they do not directly "see" cracks. Human engineering inspection remains mandatory for actual structural diagnosis.

---

## Role of Hardware in a Software-First Architecture

Aegis3D treats hardware strictly as an optional data ingestion source rather than the core system:
- **Input Mechanism**: Physical PZT sensors and ESP32 microcontrollers serve as data collection nodes feeding voltage samples into the software pipeline.
- **Hardware-Agnostic Processing Engine**: All core algorithms—DC offset removal, Butterworth filtering, FFT spectral analysis, baseline generation, and z-score anomaly detection—are pure, hardware-independent software modules.
- **Data Source Versatility**: Aegis3D evaluates signal inputs from physical sensor streams, imported historical sensor logs, or synthetic simulator engines with zero changes to the underlying processing logic.

---

## Key Design Principles

1. **Software-Centric & Hardware-Agnostic**: Core signal processing, baseline calculation, and anomaly detection engines remain pure, deterministic Python modules completely decoupled from specific microcontrollers, sensor hardware, or database ORMs.
2. **Zero Machine Learning**: Aegis3D deliberately uses deterministic signal processing, mathematical feature extraction, standard deviation metrics, and rule-based statistical thresholds instead of black-box AI/ML models.
3. **Explainable Evidence**: All anomaly flags produce human-readable, auditable evidence strings (e.g. z-score deviations) explaining exactly why an event was flagged relative to a zone's statistical baseline.
4. **Relational Domain Integrity**: Standardized PostgreSQL persistence layer storing structural zones, sessions, events, baselines, health snapshots, and alerts with strict foreign key constraints.

---

## Current Implementation Status

| Component | Status | Description / Path |
| :--- | :--- | :--- |
| **Domain Models & Schemas** | **Implemented** | 6 core SQLAlchemy models (`Zone`, `MonitoringSession`, `Event`, `Baseline`, `HealthSnapshot`, `Alert`) & Pydantic DTOs (`backend/app/models/`, `backend/app/schemas/`) |
| **PostgreSQL Persistence** | **Implemented** | Environment-based database config, SQLAlchemy 2.0 session layer, and Alembic migrations (`backend/app/db/`) |
| **FastAPI REST Foundation** | **Implemented** | Liveness `/health` and DB readiness `/health/db` endpoints (`backend/app/api/routes/health.py`) |
| **Event Ingestion API** | **Implemented** | `POST /api/v1/events` and `GET /api/v1/events/{id}` with validation & service layer (`backend/app/api/routes/events.py`) |
| **Signal Processing Engine** | **Implemented** | Sampled signal types, mean-subtraction DC offset removal, moving average, Butterworth lowpass filtering, event window detection, and FFT feature extraction (`backend/app/processing/`) |
| **Statistical Baseline Engine** | **Implemented** | Zone-specific historical baseline calculation ($\mu, \sigma$ for magnitude & energy, normal event rate, min-data validation) (`backend/app/baseline/`) |
| **Rule-Based Anomaly Engine** | **Implemented** | Z-score deviation comparison ($|z| \ge 3.0\sigma$), zero-variance baseline handling, and explainable evidence generation (`backend/app/anomaly/`) |
| **Signal Visualizer Script** | **Implemented** | Headless Matplotlib demonstration generating synthetic signals & diagnostic plots (`backend/scripts/demo_signal_processing.py`) |
| **Automated Test Suite** | **Implemented** | 68 passed pytest unit & integration tests (`backend/tests/`) |
| **Next.js Dashboard** | *Scaffolded* | Visual interface structure (`frontend/`) |
| **ESP32 Firmware** | *Scaffolded* | PlatformIO structure for ADC sampling & MQTT (`firmware/esp32/`) |
| **Hardware PCB & Schematics** | *Scaffolded* | Schematic & PCB layout documentation (`hardware/`) |
| **Temporal Persistence** | *Planned* | Multi-event temporal tracking over observation windows (Phase 3) |
| **Two-PZT Event Correlation** | *Planned* | Cross-sensor event matching & relative source indication (Phase 3) |
| **Structural Health Indicator** | *Planned* | Zone health scoring and alert escalation rules (Phase 3) |
| **Physical PZT Sensor Setup** | *Planned* | Benchtop validation with physical sensor hardware (Phase 4) |

---

## System Architecture & Processing Pipeline

### End-to-End Processing Architecture

```text
[ Signal Input Source ]
  (Physical PZT Sensors / Historical Logs / Synthetic Simulator)
                 │
                 ▼
[ Signal Input Adapter / Ingestion API ]
                 │
                 ▼
[ Signal Processing Engine ]
  ├── 1. Raw Sampled Signal Representation (SampledSignal)
  ├── 2. DC Offset Removal (Mean Subtraction)
  ├── 3. Butterworth Lowpass Filtering (scipy.signal)
  ├── 4. Event Window Detection (Thresholding & Windowing)
  └── 5. Feature Extraction (Peak, RMS, Energy, FFT Frequency)
                 │
                 ▼ (Extracted Numerical Features)
[ Zone-Specific Statistical Baseline Engine ]
  └── Calculates Historical Mean (μ) & Standard Deviation (σ)
                 │
                 ▼
[ Rule-Based Anomaly Detection Engine ]
  ├── Evaluates Standardized Deviation (|z| >= 3.0σ Threshold)
  ├── Zero-Variance Baseline Handling
  └── Explaining Evidence Generation
                 │
                 ▼ (Planned / Phase 3)
[ Temporal Persistence & Multi-PZT Correlation ]
                 │
                 ▼ (Planned / Phase 3)
[ Trend Analysis & Structural Health Indicator ]
                 │
                 ▼ (Planned / Phase 4)
[ Alert Escalation & Web Dashboard Interface ]
```

---

## Software Architecture & Package Layout

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
│   │   ├── services/            # EventService, BaselineService, AnomalyService
│   │   ├── processing/          # Signal filtering, window detection & FFT feature extraction
│   │   ├── baseline/            # Pure statistical baseline calculation engine
│   │   └── anomaly/             # Rule-based z-score anomaly analysis engine
│   ├── scripts/
│   │   └── demo_signal_processing.py  # Executable signal processing visual demo
│   └── tests/                   # Pytest test suite (68 passing tests)
├── firmware/esp32/              # ESP32 PlatformIO firmware scaffolding
├── frontend/                    # Next.js frontend dashboard scaffolding
├── hardware/                    # PCB layout, BOM, schematics scaffolding
├── docs/                        # Architecture diagrams, protocols, and documentation
└── data/                        # Signal data storage directories
```

---

## Core Technical Features

### 1. Signal Processing Foundation (`backend/app/processing/`)
- **`SampledSignal`**: Immutable 1D signal container enforcing positive sample rates ($f_s > 0$) and validating against `NaN`/`Inf` values.
- **Preprocessing**: Mean-subtraction DC offset removal preserving signal metadata. Optional peak amplitude normalization.
- **Filtering**: Moving average filter (`mode="same"`) and Butterworth lowpass filter (`scipy.signal.butter` / `filtfilt`) with Nyquist boundary checks.
- **Event Detection**: Amplitude thresholding identifying contiguous active sample windows, filtering transient noise (`min_duration_samples`), and merging sub-threshold gaps (`merge_gap_samples`).
- **Feature Extraction**:
  - **Peak Amplitude**: $\max(|x[n]|)$
  - **RMS Amplitude**: $\sqrt{\frac{1}{N} \sum x[n]^2}$
  - **Discrete Signal Energy**: $\sum x[n]^2$ (digital feature metric)
  - **Dominant Frequency**: Real FFT spectrum analysis (`np.fft.rfft`) with zero-padding and DC bin exclusion.

### 2. Statistical Baseline Engine (`backend/app/baseline/`)
- Derives normal historical statistical behavior for a specific `Zone` over an observation window `[valid_from, valid_until]`.
- Calculates arithmetic mean and population standard deviation (`ddof=0`) for event magnitude and signal energy.
- Calculates normal event rate (events per second over observation window).
- Requires minimum qualifying events (`DEFAULT_MIN_EVENTS = 10`) and excludes `DISMISSED` events.

### 3. Rule-Based Anomaly Detection (`backend/app/anomaly/`)
- Computes standardized $z$-score deviations:
  $$z_{\text{mag}} = \frac{\text{magnitude} - \mu_{\text{mag}}}{\sigma_{\text{mag}}}, \quad z_{\text{eng}} = \frac{\text{energy} - \mu_{\text{eng}}}{\sigma_{\text{eng}}}$$
- Evaluates absolute deviation against configurable threshold ($|z| \ge 3.0\sigma$).
- Evaluates magnitude and energy independently (`is_anomalous = mag_anomalous or eng_anomalous`).
- **Zero-Variance Handling**: When historical baseline standard deviation is zero ($\sigma = 0$):
  - Event value equals mean $\implies z = 0.0$, normal.
  - Event value differs from mean $\implies z = 0.0$, flagged anomalous with zero-variance evidence string.
  - Strictly avoids `NaN`, `infinity`, or division-by-zero errors.

---

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Docker & Docker Compose (for PostgreSQL database)
- Git

### 2. Clone & Environment Configuration
```bash
git clone https://github.com/m4ulikP/Aegis3D.git
cd Aegis3D

# Create local environment configuration
cp .env.example .env
```

### 3. Start PostgreSQL Database
```bash
# Start PostgreSQL on port 5432
docker compose up -d postgres
```

### 4. Setup Python Virtual Environment & Install Dependencies
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\activate

# Activate virtual environment (Linux/macOS)
# source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 5. Run Database Migrations
```bash
# Apply Alembic database migrations
alembic upgrade head
```

### 6. Start FastAPI Application Server
```bash
# Start uvicorn development server on http://127.0.0.1:8000
uvicorn app.main:app --reload
```

Verify endpoints:
- **API Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database Health Check**: [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)

---

## Running Verification Commands

### 1. Run Complete Backend Test Suite
```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/
```
*Expected Output*: `68 passed in ~1.9s` (100% pass rate).

### 2. Run Signal Processing Visual Demonstration
```bash
cd backend
.\.venv\Scripts\python.exe scripts/demo_signal_processing.py
```
*Expected Output*: Executes full 5-stage signal processing pipeline on synthetic burst events, prints feature metrics to console, and saves visualization plot to `data/processed/step5_signal_demo.png`.

---

## Validation Strategy & Metrics

### Testing Methodology
Aegis3D uses synthetic and controlled signal datasets to validate software algorithm performance before physical deployment:
- **Healthy Baseline Datasets**: Low-amplitude background mechanical noise without burst events.
- **External Environmental Noise Datasets**: Transient non-structural impacts (e.g., footsteps, door slams).
- **Controlled Structural/Mechanical Event Datasets**: High-amplitude burst signals simulating mechanical stress wave releases.

### Future Validation Evaluation Metrics
As multi-sensor correlation and physical hardware are integrated, Aegis3D will evaluate:
- **Event Detection Rate**: Ratio of detected acoustic burst events versus injected synthetic events.
- **False Positive Rate**: Percentage of non-structural environmental noise spikes incorrectly flagged as anomalous.
- **Detection Latency**: End-to-end processing time from signal input to backend anomaly result generation.
- **Anomaly Score Separation**: Statistical separation ($\Delta z$) between normal baseline fluctuations and anomalous stress events.
- **Relative Localization Error**: Difference between estimated relative event region and actual PZT sensor arrival time difference (TDOA).

---

## Current Technical Limitations

1. **Indirect Measurement**: Piezoelectric transducers measure elastic and mechanical stress waves propagating through materials. They do not directly photograph or measure physical crack dimensions.
2. **Sensor Mounting & Coupling**: Physical sensor coupling, mounting adhesive, and contact pressure affect frequency response and signal amplitude during physical testing.
3. **Zone Variability**: Material composition, geometry, and mechanical loads vary significantly between building zones.
4. **Environmental Interference**: Heavy machinery, foot traffic, or door closures can generate acoustic signals requiring baseline calibration to prevent false positives.
5. **Historical Baseline Dependency**: Statistical baseline calculation requires a minimum of 10 representative historical events per zone.
6. **Two-Sensor Spatial Limits**: A two-sensor setup enables relative time-of-arrival correlation along a single linear axis, but cannot perform full 3D spatial triangulation.
7. **Non-Certified Assessment**: Rule-based statistical anomaly detection is a structural health monitoring aid, not a certified structural engineering safety rating.
8. **Human Inspection Mandatory**: Flagged anomaly events highlight locations requiring physical inspection by qualified structural engineers.

---

## Software-First Development Roadmap

### Phase 1 — Software Foundation (**Completed**)
- [x] Domain models & PostgreSQL persistence schema
- [x] Alembic database migrations
- [x] FastAPI server foundation & Health endpoints
- [x] Event ingestion REST API (`POST /api/v1/events`)

### Phase 2 — Signal Intelligence (**Completed**)
- [x] Hardware-agnostic signal processing pipeline (filtering, window detection, FFT feature extraction)
- [x] Zone-specific statistical baseline engine ($\mu, \sigma$, event rate)
- [x] Deterministic rule-based $z$-score anomaly detection engine ($|z| \ge 3.0\sigma$)
- [x] Executable signal processing visualization tool

### Phase 3 — Advanced Structural Intelligence (**Next Milestone**)
- [ ] Multi-event temporal persistence tracking
- [ ] Two-PZT time-difference-of-arrival (TDOA) event correlation
- [ ] Relative source indication & approximate affected region mapping
- [ ] Event frequency & energy trend analysis over time
- [ ] Zone Structural Health Indicator (0–100 prototype monitoring score)
- [ ] Multi-level alert escalation engine

### Phase 4 — Interface & Optional Physical Integration (**Future Milestone**)
- [ ] Next.js real-time monitoring dashboard interface
- [ ] MQTT broker live message ingestion adapter
- [ ] ESP32 PlatformIO ADC sampling firmware completion
- [ ] Physical 2-PZT sensor prototype & controlled physical validation
