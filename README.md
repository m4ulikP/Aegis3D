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
- **Relative Source Indication**: Determines relative wavefront arrival lead/lag (e.g., `"Event arrived first at sensor PZT-Z05 (lead time: 4.20 ms relative to PZT-Z06)"`).

> **Explicit Non-Localization Note**: Two-PZT correlation indicates **relative arrival precedence along a 1D path between two sensors**. It does **NOT** compute 2D/3D physical coordinates, trilateration, or crack geometric coordinates.

---

## Structural Health Indicator (SHI) Specification

The Structural Health Indicator (SHI) is a bounded, deterministic prototype score strictly ranging from `0` to `100`:

$$\text{raw score} = 100.0 - (\text{anomaly penalty} + \text{persistence penalty} + \text{correlation penalty} + \text{trend penalty})$$
$$\text{SHI} = \max(0.0, \min(100.0, \text{raw score}))$$

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

## Two-Laptop / Hackathon Setup

Aegis3D supports a distributed deployment architecture designed for live hackathon evaluations, demonstrations, and multi-node benchtop hardware testing. In this configuration, **Laptop 1** acts as the authoritative central platform host (PostgreSQL database, FastAPI backend, LiveEventBus SSE stream, and Next.js 3D Digital Twin frontend), while **Laptop 2** acts as a standalone sensor telemetry node running the Virtual PZT Simulator over the local area network (LAN).

### 📐 Distributed Architecture

```text
                    HACKATHON LAN
                         │
              ┌──────────┴──────────┐
              │                     │
          LAPTOP 1               LAPTOP 2
        Aegis3D Host          Virtual PZT Simulator
              │                     │
       ┌──────┼──────┐              │
       │      │      │              │
   PostgreSQL FastAPI Next.js       │
              │                     │
              └──── HTTP ──────────┘
                    telemetry
```

---

### 🌐 Network & IP Configuration Concept

When transitioning between different physical environments (e.g. from a home/office WiFi network to a hackathon venue network or mobile hotspot), **Laptop 1's LAN IP address will change**.

> **Important**: This IP change is completely normal. **Zero application source code changes are required.** Only the simulator's runtime configuration (`BACKEND_URL`) on Laptop 2 needs to point to Laptop 1's current active LAN IP address.

#### Example Scenario
- **Home Network**: `BACKEND_URL=http://192.168.1.39:8000` *(Example address)*
- **Hackathon Venue**: `BACKEND_URL=http://10.42.0.15:8000` *(Example address)*

*(Note: The IP addresses above are illustrative examples. Always use your network's actual assigned IP address represented by `<LAPTOP_1_IP>`)*.

> ⚠️ **Crucial Networking Distinction**: Laptop 2 must **NEVER** use `127.0.0.1` or `localhost` when attempting to reach Laptop 1. On Laptop 2, `localhost` resolves to Laptop 2 itself, causing connection refused errors (`ECONNREFUSED`). Laptop 2 must always explicitly target `http://<LAPTOP_1_IP>:8000`.

---

### 💻 Laptop 1 — Aegis3D Host Setup

Execute the following numbered procedure on **Laptop 1**:

1. **Connect to the Network**: Connect Laptop 1 to the venue WiFi, Ethernet switch, or mobile hotspot.
2. **Identify Laptop 1's LAN IPv4 Address**:
   Open Windows PowerShell or Command Prompt and run:
   ```cmd
   ipconfig
   ```
   Locate the active Wi-Fi or Ethernet adapter and note its IPv4 Address:
   ```text
   Wireless LAN adapter Wi-Fi:
      IPv4 Address . . . . . . . . . . . : 10.42.0.15
   ```
   In this example, `<LAPTOP_1_IP>` is `10.42.0.15`.

3. **Start PostgreSQL Database**:
   From the repository root on **Laptop 1**:
   ```powershell
   # Laptop 1
   docker compose up -d postgres
   ```
   *(Ensures PostgreSQL is running on `localhost:5432` with standard database credentials)*.

4. **Launch FastAPI Backend (Bind to All Interfaces)**:
   From the `backend/` directory on **Laptop 1**:
   ```powershell
   # Laptop 1
   cd backend
   .\.venv\Scripts\activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   *(Note: Passing `--host 0.0.0.0` is mandatory. It instructs Uvicorn to listen on all network interfaces so incoming HTTP requests from Laptop 2 are accepted)*.

5. **Configure / Verify Windows Firewall (Port 8000)**:
   Windows Firewall blocks incoming TCP connections on unlisted ports by default. To allow Laptop 2 to communicate with Laptop 1, run **ONE** of the following commands on **Laptop 1 as Administrator**:

   - **Option A — Windows PowerShell (Admin)**:
     ```powershell
     # Laptop 1 (Admin PowerShell)
     New-NetFirewallRule -DisplayName "Aegis3D FastAPI Backend (Port 8000)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
     ```

   - **Option B — Command Prompt (Admin)**:
     ```cmd
     :: Laptop 1 (Admin CMD)
     netsh advfirewall firewall add rule name="Aegis3D FastAPI Backend (Port 8000)" dir=in action=allow protocol=TCP localport=8000
     ```

   > **Security Note**: Disabling Windows Firewall entirely is strongly discouraged. Adding a targeted single-port rule for TCP 8000 preserves system security while enabling inter-laptop communication.
   > 
   > **Verification**: Verify the firewall rule in PowerShell:
   > ```powershell
   > Get-NetFirewallRule -DisplayName "*Aegis3D*"
   > ```

6. **Start Next.js Frontend Dashboard**:
   From the `frontend/` directory on **Laptop 1**:
   ```powershell
   # Laptop 1
   cd frontend
   npm run dev
   ```

7. **Verify Dashboard & 3D Digital Twin**:
   Open Google Chrome on **Laptop 1** and navigate to:
   `http://localhost:3000/dashboard`
   Verify that the 2.5D City Map, 3D Digital Twin model (`building_demo.glb`), and Telemetry HUD load completely.

---

### 💻 Laptop 2 — Virtual PZT Simulator Setup

Execute the following procedure on **Laptop 2**:

1. **Connect to the Same Network**: Ensure Laptop 2 is connected to the exact same Wi-Fi, Ethernet, or mobile hotspot network as Laptop 1.
2. **Verify Python Environment**:
   From the `simulator/` directory on **Laptop 2**:
   ```powershell
   # Laptop 2
   cd simulator
   python -m venv .venv
   .\.venv\Scripts\activate      # Windows
   # source .venv/bin/activate   # Linux/macOS
   pip install -r requirements.txt
   ```

3. **Configure `BACKEND_URL`**:
   The simulator accepts Laptop 1's base URL (`http://<LAPTOP_1_IP>:8000`) through either a command-line flag or an environment variable file:

   - **Method A — CLI Flag (Recommended for Quick Demos)**:
     Pass `--backend-url http://<LAPTOP_1_IP>:8000` directly to `main.py`.
   
   - **Method B — `.env` Configuration File**:
     Create `simulator/.env` (copied from `simulator/.env.example`) and set:
     ```env
     BACKEND_URL=http://<LAPTOP_1_IP>:8000
     ```

   > **URL Distinction**: `BACKEND_URL` represents the base URL of the FastAPI server (e.g. `http://10.42.0.15:8000`). **Do not** append `/api/v1/telemetry` to `BACKEND_URL`; the simulator client (`client.py`) automatically appends `/api/v1/telemetry` for HTTP POST ingestion and `/api/v1/telemetry/live` for SSE stream tracking.

4. **Verify Connectivity to Laptop 1**:
   Run the connectivity test from **Laptop 2** (see details below).

5. **Run Simulator Telemetry**:
   Transmit discrete PZT telemetry packets from **Laptop 2** to **Laptop 1**:
   ```powershell
   # Laptop 2
   python main.py --mode anomaly --sensor PZT-Z01 --backend-url http://<LAPTOP_1_IP>:8000 --batches 1
   ```

---

### 🔌 Verify Laptop-to-Laptop Connectivity

Before launching continuous telemetry streaming, verify network connectivity from **Laptop 2** to **Laptop 1**:

1. **Browser Test (Laptop 2)**:
   Open a browser on **Laptop 2** and navigate to:
   `http://<LAPTOP_1_IP>:8000/docs`
   *If the FastAPI Swagger UI opens successfully, basic HTTP network communication is working.*

2. **HTTP Health Test (Laptop 2 Command Line)**:
   ```cmd
   :: Laptop 2
   curl.exe http://<LAPTOP_1_IP>:8000/health
   ```
   *Expected Response*: `{"status":"healthy","service":"aegis3d-backend"}`

3. **PowerShell TCP Port Test (Laptop 2)**:
   ```powershell
   # Laptop 2 (PowerShell)
   Test-NetConnection -ComputerName <LAPTOP_1_IP> -Port 8000
   ```
   *Expected Output*: `TcpTestSucceeded : True`

---

### 🎯 Canonical Sensor Selection & Zone Semantics

Aegis3D maintains strict identity consistency based on the authoritative BIM sensor registry (`data/processed/bim/sensor_registry.json`). When selecting sensors for telemetry injection, use **ONLY** canonical IDs (`PZT-Z01` through `PZT-Z12`):

| Sensor ID Range | Storey | Monitored Structural Zone | Ingestion & SHI Status |
| :--- | :--- | :--- | :--- |
| **PZT-Z01 – PZT-Z04** | `01 - Entry Level` | **Zone 2** (`Zone 2 - Substructure Pier B`, ID: 2) | **Active Monitoring Zone** (Full SHI & Alert pipeline) |
| **PZT-Z05 – PZT-Z08** | `02 - Floor` | **Zone 1** (`Zone 1 - Main Deck Girder`, ID: 1) | **Active Monitoring Zone** (Full SHI & Alert pipeline) |
| **PZT-Z09 – PZT-Z12** | `03 - Floor` | *None* (Intentionally Unassigned) | **Valid Canonical Sensors** (Blocked from Zone 1/2 with HTTP 400; no SHI or alerts) |

> ⚠️ **Retired Sensor IDs**: Never use retired legacy IDs (`PZT-Z1-01`, `PZT-Z1-02`, `PZT-Z2-01`, `PZT-Z2-02`). They are completely removed from the system.
> 
> **Active Demonstration Recommendation**: For live telemetry demonstrations, use **`PZT-Z01`** (Zone 2 default) or **`PZT-Z05`** (Zone 1). `PZT-Z09`–`PZT-Z12` are valid Storey 03 canonical sensors that are intentionally unassigned from active backend monitoring zones and will return `HTTP 400 Bad Request` if submitted against Zone 1 or Zone 2.

---

### ▶️ Full Hackathon Demo Startup Order

For a smooth presentation, start components in the following exact order:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        LAPTOP 1 (Platform Host)                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Start PostgreSQL     ──► docker compose up -d postgres             │
│ 2. Start FastAPI        ──► uvicorn app.main:app --host 0.0.0.0 --port 8000 │
│ 3. Verify Health        ──► curl http://localhost:8000/health         │
│ 4. Start Next.js        ──► npm run dev                               │
│ 5. Open Dashboard       ──► http://localhost:3000/dashboard           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Ensure Laptop 1 is fully ready
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       LAPTOP 2 (Simulator Host)                        │
├────────────────────────────────────────────────────────────────────────┤
│ 6. Verify Laptop 1 IP   ──► Test-NetConnection <LAPTOP_1_IP> -Port 8000 │
│ 7. Test Ingestion       ──► python main.py --mode normal --batches 1   │
│ 8. Inject Anomaly       ──► python main.py --mode anomaly --batches 1  │
│ 9. Run Correlation      ──► python main.py --mode correlation --batches 1│
└────────────────────────────────────────────────────────────────────────┘
```

---

### 📡 Verify Live Telemetry Flow

When **Laptop 2** transmits a telemetry packet, verify the complete end-to-end execution flow:

```text
Laptop 2 (Virtual PZT Simulator)
  │
  ├── 1. HTTP POST /api/v1/telemetry JSON Packet
  │
  ▼
Laptop 1 (FastAPI Backend)
  │
  ├── 2. Ingestion & DC Offset Subtraction
  ├── 3. 4th-Order Butterworth Lowpass Signal Filtering
  ├── 4. Activity Window Event Detection
  ├── 5. Spectral Feature Extraction (Peak, RMS, Energy, FFT Frequency)
  ├── 6. Zone Baseline Comparison & Standardized Z-Score (|z| ≥ 3.0)
  ├── 7. Temporal Persistence Evaluation (Rolling Anomaly Ratio)
  ├── 8. 2-PZT Cross-Sensor TDOA Arrival Order Correlation
  ├── 9. Structural Health Indicator (SHI 0–100) Recalculation & Alert Evaluation
  │
  ├── 10. LiveEventBus Emits Real-Time Stage Events to SSE Stream
  │
  ▼
Laptop 1 (Next.js Dashboard & 3D Digital Twin)
  │
  ├── Telemetry Operations HUD updates status & discrete signal waveform trace
  ├── Processing Inspector opens with sequential 9-stage progression
  └── 3D Digital Twin elements update zone health highlight colors (Green/Amber/Red)
```

#### What to Check During Demo Verification
- **Laptop 2 Terminal**: Output displays `[SUCCESS] Telemetry accepted by backend (Status: 200 OK)`.
- **Laptop 1 Backend Logs**: Logs record `POST /api/v1/telemetry 200 OK` processed in sub-15 ms.
- **Laptop 1 Dashboard**: Telemetry HUD updates instantly; Processing Inspector steps through stages 1 → 9 with visual dwell pacing and automatically resets to Page 1 (Ingestion) upon completion.

---

### 🔄 If the Network / IP Address Changes

If you move Laptop 1 and Laptop 2 to a new WiFi network or switch to a mobile hotspot:

1. **Find Laptop 1's New IP**: Run `ipconfig` on Laptop 1 to get the new IPv4 address (e.g. `192.168.43.115`).
2. **Update Laptop 2 Target**:
   - If using CLI flag: Pass `--backend-url http://192.168.43.115:8000` on your next command.
   - If using `.env`: Edit `simulator/.env` and update `BACKEND_URL=http://192.168.43.115:8000`.
3. **Re-Run Simulator Command**: Re-run your `python main.py` command on Laptop 2.

> **Note**: No code compilation, backend rebuild, frontend restart, or database migration is required.

---

### 🛠️ Hackathon Troubleshooting Guide

| Problem | Likely Cause | Exact Recovery Action |
| :--- | :--- | :--- |
| **Laptop 2 cannot reach `http://<LAPTOP_1_IP>:8000/docs` (Connection Refused / Timeout)** | 1. FastAPI bound to `127.0.0.1` instead of `0.0.0.0`.<br>2. Windows Firewall blocking port 8000.<br>3. Incorrect IP address.<br>4. Client AP isolation active on venue Wi-Fi. | 1. On Laptop 1, launch FastAPI with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.<br>2. Add firewall rule on Laptop 1: `New-NetFirewallRule -DisplayName "Aegis3D Port 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000`.<br>3. Verify IP via `ipconfig`.<br>4. Switch to Mobile Hotspot backup. |
| **Both laptops have Internet but cannot communicate** | Hackathon venue Wi-Fi has Client/AP Isolation enabled (prevents device-to-device LAN connections). | Enable Mobile Hotspot on Laptop 1, connect Laptop 2 to Laptop 1's hotspot, update `<LAPTOP_1_IP>`, and retry. |
| **Simulator reports `HTTP 400 Bad Request: Sensor '...' is inconsistent with target zone`** | Simulator packet specifies an invalid sensor/zone pair or targets an unassigned sensor (`PZT-Z09`–`PZT-Z12`). | Use canonical assigned sensors: `PZT-Z01`–`PZT-Z04` for Zone 2 (`Zone 2 - Substructure Pier B`) or `PZT-Z05`–`PZT-Z08` for Zone 1 (`Zone 1 - Main Deck Girder`). |
| **Dashboard loads on Laptop 1 but receives no live telemetry stream** | 1. Simulator transmitting to wrong IP.<br>2. FastAPI backend not running. | 1. Verify `BACKEND_URL` on Laptop 2.<br>2. Check `http://localhost:8000/health` on Laptop 1. |
| **Next.js Error: `Cannot find module './682.js'`** | `npm run build` was executed while `npm run dev` was actively running, corrupting Next.js `.next` development server chunks. | **Safe Recovery Procedure**: <br>1. Stop Next.js dev server on Laptop 1.<br>2. Delete build directory: `Remove-Item -Recurse -Force frontend/.next`<br>3. Restart dev server: `cd frontend; npm run dev`. *(Do NOT delete `node_modules`)*. |

---

### 🛟 Venue Network Backup (Mobile Hotspot)

If the venue Wi-Fi blocks peer-to-peer communication via Client AP Isolation:

```text
┌────────────────────────────────────────────────────────┐
│ 1. Enable Mobile Hotspot on Laptop 1                   │
│ 2. Connect Laptop 2 to Laptop 1's Hotspot Wi-Fi        │
│ 3. Run ipconfig on Laptop 1 (Find Hotspot Adapter IP)  │
│ 4. Set BACKEND_URL=http://<HOTSPOT_IP>:8000 on Laptop 2│
│ 5. Test http://<HOTSPOT_IP>:8000/docs from Laptop 2    │
│ 6. Launch Simulator on Laptop 2                        │
└────────────────────────────────────────────────────────┘
```

---

### ✅ Final Hackathon Checklist

#### Network Verification
- [ ] Laptop 1 and Laptop 2 connected to the same Wi-Fi, Ethernet, or Hotspot
- [ ] Active IPv4 address of Laptop 1 identified via `ipconfig`
- [ ] Windows Firewall TCP Port 8000 allowed on Laptop 1
- [ ] Laptop 2 verifies connectivity via `http://<LAPTOP_1_IP>:8000/docs`

#### Laptop 1 (Platform Host)
- [ ] PostgreSQL container running (`docker compose up -d postgres`)
- [ ] FastAPI backend running bound to `0.0.0.0:8000`
- [ ] Backend health endpoint returns 200 OK (`http://localhost:8000/health`)
- [ ] Next.js frontend running (`npm run dev`)
- [ ] Dashboard accessible at `http://localhost:3000/dashboard`
- [ ] 3D Digital Twin viewer and City Map rendered clean without errors

#### Laptop 2 (Simulator Host)
- [ ] Python virtual environment configured (`simulator/.venv`)
- [ ] `BACKEND_URL` configured to `http://<LAPTOP_1_IP>:8000`
- [ ] Canonical sensor selection verified (`PZT-Z01` or `PZT-Z05`)
- [ ] Test packet transmission returns HTTP 200 OK

#### Live Demonstration Flow
- [ ] Simulator telemetry packet transmitted from Laptop 2
- [ ] Backend processes packet in ~10 ms and emits real SSE events
- [ ] Telemetry HUD displays live telemetry waveform and sequence counter
- [ ] Processing Inspector panel opens with 9-stage progression
- [ ] 3D Digital Twin highlights affected structural zone in real time

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
python main.py --mode anomaly --sensor PZT-Z01 --backend-url http://localhost:8000 --batches 1
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
