# Aegis3D

## Smart PZT-Based Structural Health Monitoring & Early-Warning System

### Team BRIKS
- **Maulik Pandey**
- **Shikhar Sadhu**
- **Pratyush Bhaskar Ram**
- **Madhav Kumar**

**MAITRON 2026** | **Hardware Track**  
**Primary SDG**: SDG 11 — Sustainable Cities and Communities  
**Secondary SDG**: SDG 9 — Industry, Innovation and Infrastructure

---

## Overview

**Aegis3D** is a hardware-track Structural Health Monitoring (SHM) and early-warning prototype designed to observe structural acoustic and elastic wave activity in buildings and infrastructure. By capturing piezoelectric sensor signals and processing them through a deterministic, hardware-agnostic signal processing and statistical analysis pipeline, Aegis3D establishes zone-specific baseline behavior and identifies anomalous structural events to flag locations requiring physical inspection.

> **Crucial Disclaimer**: Aegis3D is a continuous monitoring and early-warning aid. It does **NOT** use machine learning inference, predict structural collapse, guarantee disaster prevention, replace licensed structural engineers, or provide certified safety assessments. Piezoelectric Transducers (PZTs) detect acoustic, mechanical, and elastic wave events within materials; they do not directly "see" cracks. Human engineering inspection remains mandatory for actual structural assessment.

---

## Key Design Principles

1. **Hardware Independence**: Core signal processing, baseline calculation, and anomaly detection engines remain pure, deterministic Python modules completely decoupled from specific microcontrollers, sensor models, or database ORMs.
2. **Zero Machine Learning**: Aegis3D deliberately uses deterministic signal processing, mathematical feature extraction, standard deviation metrics, and rule-based statistical thresholds instead of black-box AI/ML models.
3. **Explainable Evidence**: All anomaly flags produce human-readable, auditable evidence strings (e.g. z-score deviations) explaining exactly why an event was flagged relative to a zone's baseline.
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
| **Temporal & Trend Analysis** | *Planned* | Multi-event trend analysis over observation windows (Phase 2) |
| **Two-PZT Event Correlation** | *Planned* | Cross-sensor event matching & relative source indication (Phase 2) |
| **Structural Health Indicator** | *Planned* | Zone health scoring and alert escalation rules (Phase 3) |

---

## System & Processing Pipeline Architecture

### Current Processing Pipeline

```text
[ Physical PZT Sensors (2x Array) ]
                │
                ▼ (Mechanical / Elastic Acoustic Waves)
[ Analog Signal Conditioning (Amp / Filter) ]
                │
                ▼ (Conditioned Voltage Signal)
[ ESP32 ADC Sampling ]
                │
                ▼ (Digital Signal Packets)
[ Wi-Fi / MQTT Transport ]
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│ Backend Signal Processing Pipeline (backend/app/)       │
│                                                         │
│ 1. Raw Sampled Signal Representation (SampledSignal)    │
│ 2. DC Offset Removal (Mean Subtraction)                │
│ 3. Butterworth Lowpass Filtering (scipy.signal)         │
│ 4. Event Detection (Threshold & Window Windowing)       │
│ 5. Feature Extraction (Peak, RMS, Energy, FFT Freq)     │
└──────────────────────────┬──────────────────────────────┘
                           │ (Extracted Features)
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Baseline & Anomaly Intelligence Layer                   │
│                                                         │
│ 1. Zone-Specific Historical Baseline (Mean & Std Dev)   │
│ 2. Z-Score Deviation Comparison (|z| >= 3.0σ Threshold)  │
│ 3. Rule-Based Anomaly Decision & Explainable Evidence   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Persistence & API Layer                                 │
│                                                         │
│ 1. PostgreSQL Relational Database (SQLAlchemy 2.0)       │
│ 2. FastAPI REST Interface (POST/GET /api/v1/events)     │
└─────────────────────────────────────────────────────────┘
```

### Planned Future Pipeline Expansion

```text
[ Anomaly Evidence ] ──► [ Temporal Trend Engine ] ──► [ Multi-PZT Correlation ]
                                                              │
                                                              ▼
[ Web Dashboard ] ◄── [ Alert Escalation ] ◄── [ Structural Health Indicator ]
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
Aegis3D uses synthetic and controlled signal datasets to validate algorithm performance before physical deployment:
- **Healthy Baseline Datasets**: Low-amplitude background mechanical noise without burst events.
- **External Environmental Noise Datasets**: Transient non-structural impacts (e.g., footsteps, door slams).
- **Controlled Structural/Mechanical Event Datasets**: High-amplitude burst signals simulating mechanical stress wave releases.

### Future Validation Evaluation Metrics
As physical hardware and multi-sensor correlation are integrated, Aegis3D will evaluate:
- **Event Detection Rate**: Ratio of detected acoustic burst events versus injected synthetic events.
- **False Positive Rate**: Percentage of non-structural environmental noise spikes incorrectly flagged as anomalous.
- **Detection Latency**: End-to-end processing time from ESP32 ADC sampling to backend anomaly result generation.
- **Anomaly Score Separation**: Statistical separation ($\Delta z$) between normal baseline fluctuations and anomalous stress events.
- **Relative Localization Error**: Difference between estimated relative event region and actual PZT sensor arrival time difference (TDOA).

---

## Current Technical Limitations

1. **Indirect Measurement**: Piezoelectric transducers measure elastic and mechanical stress waves propagating through materials. They do not directly photograph or measure physical crack dimensions.
2. **Sensor Mounting & Coupling**: Sensor coupling, mounting adhesive, and physical contact pressure significantly affect frequency response and signal amplitude.
3. **Zone Variability**: Material composition, geometry, and mechanical loads vary significantly between building zones.
4. **Environmental Interference**: Heavy machinery, foot traffic, or door closures can generate acoustic signals that require baseline calibration to prevent false positives.
5. **Historical Baseline Dependency**: Statistical baseline calculation requires a minimum of 10 representative historical events per zone.
6. **Two-Sensor Spatial Limits**: A two-sensor setup enables relative time-of-arrival correlation along a single linear axis, but cannot perform full 3D spatial triangulation.
7. **Non-Certified Assessment**: Rule-based statistical anomaly detection is a structural health monitoring aid, not a certified structural engineering safety rating.
8. **Human Inspection Mandatory**: Flagged anomaly events highlight locations requiring physical inspection by qualified structural engineers.

---

## Development Roadmap

### Phase 1: Core Backend & Statistical Foundation (**Completed**)
- [x] PostgreSQL persistence schema & Alembic migrations
- [x] FastAPI server foundation & Health endpoints
- [x] Event ingestion REST API
- [x] Hardware-agnostic signal processing pipeline (filtering, window detection, FFT feature extraction)
- [x] Zone-specific statistical baseline engine
- [x] Deterministic rule-based $z$-score anomaly detection engine

### Phase 2: Temporal & Multi-Sensor Intelligence (**Next Milestone**)
- [ ] Multi-event temporal persistence tracking
- [ ] Two-PZT time-difference-of-arrival (TDOA) event correlation
- [ ] Relative source indication / approximate affected region mapping
- [ ] Event frequency & energy trend analysis over time

### Phase 3: Health Indicator & Escalation
- [ ] Zone Structural Health Indicator (0–100 prototype monitoring score)
- [ ] Multi-level alert escalation engine
- [ ] Next.js real-time monitoring dashboard interface
- [ ] Historical trends and baseline visualization charts

### Phase 4: Hardware & Live Deployment
- [ ] ESP32 PlatformIO ADC sampling firmware completion
- [ ] MQTT broker live message ingestion adapter
- [ ] Physical 2-PZT sensor conditioning circuit prototype
- [ ] Benchtop validation on physical concrete/steel structural element
