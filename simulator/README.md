# Aegis3D Virtual Sensor Simulator

Standalone software simulator for representative Piezoelectric Transducer (PZT) sensor nodes, designed to emit discrete time-series telemetry to the Aegis3D backend API over HTTP/LAN.

> [!IMPORTANT]
> **Prototype Telemetry Disclaimer**:  
> The simulator generates representative telemetry for the Aegis3D software prototype. It does not reproduce physically exact PZT/structural acoustic waveforms and does not represent physical sensor hardware.  
>  
> **Causal Architecture Principle**:  
> The simulator **sends telemetry only**. It never pre-classifies anomalies, forces alert flags, or dictates health scores. All event detection, feature extraction, z-score anomaly analysis, temporal persistence, 2-PZT cross-sensor correlation, and Structural Health Indicator (SHI) calculations are executed purely by the Aegis3D backend engine.

---

## 1. System Architecture

The simulator is built to run standalone on a separate laptop (e.g. Laptop 2) across a local area network (LAN), or locally alongside the backend (Laptop 1):

```text
┌─────────────────────────────────────────────────────────────┐
│ LAPTOP 2: Virtual Sensor Simulator (Standalone Node)       │
│                                                             │
│   VirtualPZTSensor (PZT-Z01 / PZT-Z02 / PZT-Z05)            │
│            │                                                │
│            ▼                                                │
│   Discrete Signal Generator (Normal / Transient / Anomaly)  │
│            │                                                │
│            ▼                                                │
│   TelemetryClient (HTTP POST JSON)                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTP POST over LAN
                             │ (/api/v1/telemetry)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ LAPTOP 1: Aegis3D Platform Foundation                       │
│                                                             │
│   FastAPI Server (0.0.0.0:8000)                             │
│            ↓                                                │
│   POST /api/v1/telemetry Ingestion Endpoint                 │
│            ↓                                                │
│   Signal Processing & Filtering (SampledSignal)             │
│            ↓                                                │
│   Event Window Detection & FFT Feature Extraction           │
│            ↓                                                │
│   PostgreSQL Event Persistence (EventRepository)            │
│            ↓                                                │
│   Statistical Baseline & Z-Score Anomaly Engine             │
│            ↓                                                │
│   Temporal Persistence & 2-PZT Cross-Sensor Correlation     │
│            ↓                                                │
│   Structural Health Indicator (SHI 0-100) Recalculation     │
│            ↓                                                │
│   Automated Alert Evaluation & State Update                 │
│            ↓                                                │
│   Next.js 14 Frontend & 3D Digital Twin Viewer              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```text
simulator/
├── README.md                      # Simulator documentation and operations guide
├── requirements.txt               # Standalone dependencies (numpy, pytest)
├── .env.example                   # Configuration template for LAN & localhost
├── config.py                      # Runtime settings loader & zone mappings
├── client.py                      # Lightweight HTTP client with error handling
├── signal_generator.py            # Representative waveform generator functions
├── main.py                        # Standalone CLI entrypoint
├── conftest.py                    # Pytest environment bootstrap
├── sensors/
│   ├── __init__.py                # Package exports
│   └── virtual_pzt.py             # VirtualPZTSensor state & payload builder
└── tests/
    ├── __init__.py                # Tests package
    ├── test_client.py             # Unit tests for HTTP transport and error handling
    ├── test_signal_generator.py   # Unit tests for normal/transient/anomaly waveforms
    ├── test_virtual_pzt.py        # Unit tests for sensor sequence & contract compliance
    └── test_integration_backend.py # End-to-end integration tests with backend pipeline
```

---

## 3. Telemetry Contract Adherence

The simulator adheres strictly to the backend `TelemetryIngestRequest` contract defined in `backend/app/schemas/telemetry.py`:

| Field | Type | Required | Description |
|---|---|---|---|
| `sensor_id` | `string` | Yes | Stable sensor identifier (e.g. `"PZT-Z01"` [Zone 2], `"PZT-Z05"` [Zone 1]). |
| `zone_name` | `string` | Yes | Target structural zone (e.g. `"Zone 1 - Main Deck Girder"`). |
| `timestamp` | `datetime` | Yes | ISO 8601 UTC timestamp of acquisition. |
| `sample_rate_hz` | `float` | Yes | Sampling frequency in Hertz (`> 0`). |
| `sequence` | `integer` | Yes | Monotonic packet sequence counter (`>= 0`). |
| `samples` | `List[float]` | Yes | 1D discrete real-valued sample array (no NaN/Inf). |
| `detection_threshold`| `float` | No | Optional amplitude threshold override. |
| `session_id` | `integer` | No | Optional monitoring session ID override. |

### Forbidden Payload Keys
The simulator **never** sends backend decision attributes:
`anomaly`, `is_anomalous`, `severity`, `health_score`, `alert`, `event_detected`, `correlation`.

---

## 4. Sensor & Zone Identities

Aegis3D maintains strict consistency between sensor IDs and target zones. The simulator uses the canonical BIM sensor registry (`sensors.json`):

| Sensor ID | Storey | Monitored Structural Zone | Structural Element Group |
|---|---|---|---|
| `PZT-Z01`–`PZT-Z04` | `01 - Entry Level` | `Zone 2 - Substructure Pier B` | Representative Structural Column Group (`IfcColumn`) |
| `PZT-Z05`–`PZT-Z08` | `02 - Floor` | `Zone 1 - Main Deck Girder` | Representative Structural Beam Group (`IfcBeam`) |
| `PZT-Z09`–`PZT-Z12` | `03 - Floor` | *Intentionally unassigned* | Upper Floor Structural Column Group (`IfcColumn`) |

*Note: All 12 canonical sensors are verified in the BIM/physics/sensor-registry layer. Eight sensors are currently assigned to active backend monitoring zones; PZT-Z09–Z12 are valid canonical Storey 03 sensors intentionally unassigned from the current monitoring-zone model and are rejected with HTTP 400 if submitted to Zone 1 or Zone 2.*

---

## 5. Signal Generation Modes & Anomaly Injection

Anomaly injection means **altering the discrete sample values**, not sending an anomaly flag.

### A. Normal (`--mode normal`)
- Low-amplitude background ambient noise ($\mu = 0.0, \sigma = 0.04$) and subtle harmonic vibration.
- Peak amplitudes remain $< 0.35$, well below event detection thresholds.
- Backend Result: `status: "PROCESSED_NO_EVENT"`, `events_detected: 0`.

### B. Transient (`--mode transient`)
- Baseline noise plus a moderate localized mechanical disturbance (peak $\sim 1.35$).
- Reaches event detection threshold without triggering extreme anomaly z-scores.
- Backend Result: `status: "PROCESSED_EVENT_DETECTED"`.

### C. Anomaly (`--mode anomaly`)
- High-amplitude acoustic burst release ($\text{peak} \approx 4.5$) with exponential ringdown decay.
- Significantly exceeds zone historical baseline ($\mu = 1.20, \sigma = 0.15$).
- Backend Result: `status: "PROCESSED_ANOMALY_DETECTED"`, `events_detected: 1`, `is_anomalous: true`, `|z| >= 3.0` sigma.

### D. 2-PZT Cross-Sensor Correlation (`--mode correlation`)
- Simulates representative temporally correlated stress signals with a 5 ms relative arrival offset.
- Sensor 1 (`PZT-Z05`) detects the burst wave first.
- Sensor 2 (`PZT-Z06`) detects the wave delayed by $5\text{ ms}$ (well within the backend's $25\text{ ms}$ correlation tolerance) and attenuated by $15\%$.
- Backend Result: Groups both events, computes relative lead/lag arrival order, and confirms `cross_sensor_correlation_confirmed: true`.

---

## 6. Installation & Prerequisites

The simulator is purely standalone and requires Python 3.10+:

```bash
cd simulator

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 7. Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configurable parameters:
- `BACKEND_URL`: URL of the FastAPI backend (e.g. `http://localhost:8000` or `http://192.168.1.50:8000`).
- `TELEMETRY_ENDPOINT`: Telemetry route path (default: `/api/v1/telemetry`).
- `TIMEOUT_SECONDS`: Request timeout in seconds (default: `5.0`).
- `DEFAULT_SAMPLE_RATE_HZ`: Sampling frequency in Hertz (default: `1000.0`).
- `DEFAULT_SAMPLE_COUNT`: Number of discrete samples per batch (default: `1000`).

---

## 8. Operating Modes

### One-Laptop Mode (Local Development)
Both FastAPI and the Simulator run on the same computer:

1. **Start Backend on Laptop 1**:
   ```bash
   cd backend
   .\.venv\Scripts\activate
   uvicorn app.main:app --reload --port 8000
   ```
2. **Run Simulator on Laptop 1**:
   ```bash
   cd simulator
   python main.py --mode normal
   ```

### Two-Laptop Mode (Demonstration / LAN Deployment)
FastAPI and the Database run on **Laptop 1**, while the Simulator runs on **Laptop 2**:

1. **On Laptop 1 (Server)**:
   - Identify Laptop 1's LAN IP address:
     - Windows: `ipconfig` (e.g. `192.168.1.50`)
     - Linux/macOS: `ip addr` or `ifconfig`
   - Start the FastAPI backend bound to `0.0.0.0` so it accepts LAN connections:
     ```bash
     cd backend
     .\.venv\Scripts\activate
     uvicorn app.main:app --host 0.0.0.0 --port 8000
     ```
   - Ensure Windows Defender Firewall or local firewall allows incoming TCP traffic on port 8000 (standard Windows prompt: "Allow Python to communicate on private networks").

2. **On Laptop 2 (Simulator)**:
   - Clone or copy the repository onto Laptop 2.
   - Configure `.env` in `simulator/`:
     ```env
     BACKEND_URL=http://192.168.1.50:8000
     TELEMETRY_ENDPOINT=/api/v1/telemetry
     ```
   - Run the simulator:
     ```bash
     cd simulator
     python main.py --backend-url http://192.168.1.50:8000 --mode normal
     ```
   - Observe the live processing response returned from Laptop 1!

---

## 9. CLI Usage & Examples

### Basic Normal Telemetry
```bash
python main.py --mode normal
```

### Anomaly Telemetry
```bash
python main.py --mode anomaly --batches 3 --interval 1.0
```

### 2-PZT Multi-Sensor Correlation Demo
```bash
python main.py --mode correlation --batches 1
```

### Continuous Telemetry Stream
```bash
python main.py --sensor PZT-Z01 --mode normal --batches 0 --interval 0.5
```

### Deterministic Seeded Reproduction
```bash
python main.py --mode anomaly --seed 42
```

### CLI Command Options
| Option | Default | Description |
|---|---|---|
| `--mode` | `normal` | Simulation mode: `normal`, `transient`, `anomaly`, `correlation` |
| `--sensor` | `PZT-Z01` | Sensor ID to transmit from |
| `--zone` | *auto-inferred* | Zone name override |
| `--backend-url` | *from config* | Target backend URL (e.g. `http://192.168.1.50:8000`) |
| `--batches` | `1` | Total batch count (`0` or negative for continuous loop) |
| `--interval` | `1.0` | Pause duration between batches in seconds |
| `--samples` | `1000` | Sample count per batch |
| `--sample-rate`| `1000.0` | Sampling frequency in Hertz |
| `--seed` | `None` | Integer RNG seed for reproducible demonstration |
| `--timeout` | `5.0` | HTTP request timeout in seconds |

---

## 10. Running Simulator Tests

Run all unit and integration tests:

```bash
cd simulator
python -m pytest tests/
```

*Expected output*: `20 passed` across signal generation, sensor models, HTTP transport, and backend integration.

---

## 11. Troubleshooting

- **`Backend unreachable at http://192.168.x.x:8000`**:
  - Verify Laptop 1 is running `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  - Check that both laptops are on the same Wi-Fi / subnet.
  - Verify Laptop 1's firewall permits incoming TCP connections on port 8000.
  - Test connectivity from Laptop 2 terminal: `curl http://192.168.x.x:8000/health`.

- **`HTTP 400 Bad Request: Sensor 'PZT-Z01' is inconsistent with target zone`**:
  - Ensure the sensor ID matches the target zone (`PZT-Z01`–`Z04` for Zone 2, `PZT-Z05`–`Z08` for Zone 1). Note that `PZT-Z09`–`Z12` are valid canonical Storey 03 sensors that are intentionally unassigned from the active monitoring-zone model and cannot be submitted against Zone 1 or Zone 2.

- **`HTTP 404 Not Found: Zone '...' not found`**:
  - Ensure the target zone name matches the backend database (`"Zone 1 - Main Deck Girder"`, `"Zone 2 - Substructure Pier B"`).
