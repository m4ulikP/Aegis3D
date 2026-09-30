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

Aegis3D supports a distributed deployment architecture designed for live hackathon evaluations, demonstrations, and multi-node benchtop hardware testing. In this configuration, **Laptop 1** acts as the central platform host (PostgreSQL database, FastAPI backend, LiveEventBus SSE stream, and Next.js 3D Digital Twin frontend), while **Laptop 2** acts as a standalone sensor telemetry node running the Virtual PZT Sensor Simulator over the local area network (LAN).

> [!IMPORTANT]
> **Single-Backend Architecture**: The simulator on Laptop 2 is purely a lightweight client (`client.py`). It does **NOT** run a second FastAPI backend server or database. Laptop 1's backend remains the sole authoritative engine for processing signals, evaluating baseline z-scores, managing state, computing SHI scores, and persisting final results.

---

### 1. Architecture Overview

```text
Laptop 2
Virtual PZT Simulator
        |
        | HTTP POST /api/v1/telemetry
        | SSE/live processing where applicable
        v
   Local LAN / Wi-Fi
        |
        v
Laptop 1
FastAPI :8000
        |
        +---- PostgreSQL :5432
        |
        +---- Next.js :3000
                  |
                  +---- City Map
                  +---- Digital Twin / BIM
```

#### Core Components & Responsibilities
- **Laptop 1 — Platform Host**:
  - **PostgreSQL Database** (`:5432`): Persistent relational store for zones, baselines, telemetry events, processing traces, health snapshots, and system alerts.
  - **FastAPI Backend** (`:8000`): Authoritative processing engine. Ingests raw PZT voltage samples, runs the 9-stage signal pipeline, calculates z-scores ($|z| \ge 3.0$), tracks temporal persistence, evaluates 2-PZT TDOA correlation, computes bounded SHI scores, and streams real-time stage events over SSE (`/api/v1/telemetry/live`).
  - **Next.js Dashboard** (`:3000`): Real-time engineering console rendering the 2.5D MapLibre City Map, 3D R3F Digital Twin (`building_demo.glb`), Telemetry Operations HUD, and continuous Processing Inspector.
- **Laptop 2 — Virtual PZT Sensor Simulator**:
  - Runs **only** the physics-based virtual sensor simulator (`simulator/main.py`).
  - Generates discrete PZT voltage samples representing ambient normal noise, acoustic stress bursts, or multi-sensor correlation wavefronts.
  - Transmits telemetry packets over the local network via HTTP `POST /api/v1/telemetry` to Laptop 1's FastAPI backend.

#### Fundamental Networking Rules
- Both laptops must be connected to the same LAN (Wi-Fi, Ethernet, or Mobile Hotspot) and able to reach Laptop 1 over the network.
- **Laptop 1's IP address** is the critical runtime configuration value required by Laptop 2.
- When the physical network changes (e.g. moving from home to a hackathon venue), Laptop 1's assigned IP address may change.
- **Source code does NOT need to change** when the IP changes; only the simulator's runtime `BACKEND_URL` on Laptop 2 must point to Laptop 1's active IPv4 address.

---

### 2. Prerequisites

Ensure the following tools and environments are installed before setup:

#### Laptop 1 (Platform Host)
- **Git** (for repository access)
- **Python 3.10+** (with virtual environment support for backend dependencies)
- **Docker Desktop & Docker Compose** (for running PostgreSQL container)
- **Node.js 18+ & npm** (for building and serving the Next.js frontend)
- **Aegis3D Repository** clone

#### Laptop 2 (Simulator Host)
- **Git** (for repository access)
- **Python 3.10+** (for running the simulator)
- **Simulator Dependencies** (`pip install -r simulator/requirements.txt`)
- **Aegis3D Repository** clone

#### Network Requirements
- Both laptops must be connected to the exact same:
  - Venue Wi-Fi network, **OR**
  - Dedicated local router / Ethernet switch, **OR**
  - Mobile phone / laptop Wi-Fi Hotspot.

> [!WARNING]
> **Client / AP Isolation Warning**: Many institutional, corporate, and public venue Wi-Fi networks enable **Client / AP Isolation** (also called Station Isolation). AP isolation prevents wireless devices on the same Wi-Fi network from communicating directly with each other, even though both laptops have working internet access. If AP isolation is active on the venue network, use the **Mobile Hotspot Backup** procedure documented below.

---

### 3. Step 1 — Identify Laptop IP Addresses

To configure inter-laptop communication, determine the active IPv4 addresses of both laptops on Windows using `ipconfig`.

#### On Laptop 1 (Platform Host)
Open PowerShell or Command Prompt and run:
```cmd
ipconfig
```
Locate the active network adapter (e.g., `Wireless LAN adapter Wi-Fi` or `Ethernet adapter`).

*Example Output*:
```text
Wireless LAN adapter Wi-Fi:
   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 192.168.1.39
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
```
In this example, **Laptop 1 IPv4 = `192.168.1.39`**.

#### On Laptop 2 (Simulator Host)
Open PowerShell or Command Prompt and run:
```cmd
ipconfig
```
*Example Output*:
```text
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 192.168.1.40
```
In this example, **Laptop 2 IPv4 = `192.168.1.40`**.

> [!IMPORTANT]
> - The IP addresses above (`192.168.1.39` and `192.168.1.40`) are **examples only** and **MUST NOT be hardcoded**. Always identify the actual assigned IPv4 address on your current network.
> - **Do NOT use `127.0.0.1` or `localhost` from Laptop 2 when referring to Laptop 1**. On Laptop 2, `localhost` resolves locally to Laptop 2 itself, resulting in connection refused errors (`ECONNREFUSED`). Laptop 2 must explicitly target Laptop 1's LAN IPv4 address (e.g. `http://192.168.1.39:8000`).

---

### 4. Step 2 — Start PostgreSQL on Laptop 1

PostgreSQL stores domain entities, baselines, raw events, processing traces, health snapshots, and active alerts. PostgreSQL **must** be running before launching the FastAPI backend.

From the repository root on **Laptop 1**:
```powershell
# Laptop 1 (Repository Root)
docker compose up -d postgres
```

#### Verification
Verify PostgreSQL container liveness and database port (`5432`) binding:
```powershell
docker compose ps
```
*Expected Output*: `aegis3d-postgres` container in `Up` or `running` state with port `5432->5432/tcp`.

---

### 5. Step 3 — Start FastAPI on Laptop 1

The FastAPI backend executes signal conditioning, feature extraction, z-score anomaly scoring, and SSE stream broadcasting.

From the `backend/` directory on **Laptop 1**:
```powershell
# Laptop 1
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> [!IMPORTANT]
> **Why `--host 0.0.0.0` is Mandatory**:
> Binding Uvicorn to `127.0.0.1` (or `localhost`) restricts the server to local loopback connections on Laptop 1 only. Binding to `0.0.0.0` instructs FastAPI to listen on **all network interfaces**, allowing incoming HTTP requests from Laptop 2 over the local network.

#### Health Verification Checks
1. **Laptop 1 Local Loopback Liveness**:
   Open a browser or terminal on Laptop 1:
   ```cmd
   curl.exe http://127.0.0.1:8000/health
   ```
   *Expected Response*: `{"status":"healthy","service":"aegis3d-backend"}`

2. **Laptop 1 Database Liveness**:
   ```cmd
   curl.exe http://127.0.0.1:8000/health/db
   ```
   *Expected Response*: `{"status":"healthy","database":"connected"}`

3. **Laptop 1 LAN Interface Check**:
   Test accessing the endpoint using Laptop 1's active LAN IPv4 address from Laptop 1:
   ```cmd
   curl.exe http://<LAPTOP1_IP>:8000/health
   ```
   *Example*: `curl.exe http://192.168.1.39:8000/health`  
   *(Replace `192.168.1.39` with Laptop 1's actual LAN IPv4).*

---

### 6. Step 4 — Windows Firewall Configuration

Windows Firewall blocks incoming TCP network traffic on unlisted ports by default. To allow Laptop 2 to send HTTP requests to FastAPI on port 8000, create an inbound firewall rule on Laptop 1.

Run the following command in **PowerShell as Administrator** on **Laptop 1**:
```powershell
# Laptop 1 (Elevated Admin PowerShell)
New-NetFirewallRule -DisplayName "Aegis3D FastAPI LAN" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

#### Why This Configuration is Used
- **Targeted Port Exposure**: Allows inbound TCP connections strictly on port `8000`.
- **Private Profile Scoping**: Restricts rule application to trusted `Private` network profiles.
- **Security Compliance**: Avoids turning off Windows Firewall globally. Never disable Windows Firewall entirely.

#### Windows Network Profile Verification (Private vs Public)
Windows Firewall applies strict inbound blocking when a network is classified as `Public`. To verify and adjust the network profile on **Laptop 1**:
1. Check current network profile:
   ```powershell
   Get-NetConnectionProfile
   ```
2. If `NetworkCategory` displays `Public` and policy permits, change it to `Private` in Admin PowerShell:
   ```powershell
   Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private
   ```

#### Rule Inspection Command
To verify that the rule exists and is active on Laptop 1:
```powershell
Get-NetFirewallRule -DisplayName "Aegis3D FastAPI LAN"
```
*Expected Output*: Displays rule properties showing `Enabled : True`, `Direction : Inbound`, `Action : Allow`, `LocalPort : 8000`.

---

### 7. Step 5 — Verify Laptop-to-Laptop Connectivity

Before starting the simulator on Laptop 2, run this systematic connectivity verification sequence from **Laptop 2**.

#### 1. TCP Port 8000 Verification (Strongest Diagnostic Test)
From **Laptop 2** PowerShell:
```powershell
# Laptop 2 (PowerShell)
Test-NetConnection <LAPTOP1_IP> -Port 8000
```
*Example*: `Test-NetConnection 192.168.1.39 -Port 8000`

- **Expected Key Result**:
  ```text
  TcpTestSucceeded : True
  ```

#### 2. Network Layer Ping Verification
From **Laptop 2** command line:
```cmd
:: Laptop 2
ping <LAPTOP1_IP>
```
> [!NOTE]
> Ping uses the ICMP protocol. A ping failure (`Request timed out` or `Destination host unreachable`) does **NOT** necessarily mean TCP connectivity is broken, as ICMP echo requests are frequently blocked by default network security policies. Always rely on `Test-NetConnection` as the definitive TCP test.

#### 3. Application Layer HTTP Health Verification
From **Laptop 2** command line or browser:
```cmd
:: Laptop 2
curl.exe http://<LAPTOP1_IP>:8000/health
```
*Expected Output*: `{"status":"healthy","service":"aegis3d-backend"}`

#### Connectivity Diagnostic Logic
- **If `Test-NetConnection` fails (`TcpTestSucceeded : False`)**:
  $\rightarrow$ Investigate physical LAN connection, IP address accuracy, Windows Firewall rules, Uvicorn `0.0.0.0` binding, or Wi-Fi AP isolation **before** modifying simulator code.
- **If `Test-NetConnection` succeeds (`True`) but `/health` fails (HTTP 500/timeout)**:
  $\rightarrow$ Investigate FastAPI server execution, backend Python environment, or PostgreSQL database state on Laptop 1.
- **If `/health` returns `200 OK`**:
  $\rightarrow$ Network path and FastAPI port binding are 100% verified and functional.

---

### 8. Step 6 — Configure the Simulator on Laptop 2

Configure the simulator on **Laptop 2** to direct all telemetry ingestion requests to Laptop 1's active FastAPI IP address.

#### Configuration Methods

- **Method A — Command-Line Flag (Recommended for Live Hackathon Demos)**:
  Pass `--backend-url http://<LAPTOP1_IP>:8000` directly to `main.py`:
  ```bash
  python main.py --mode normal --sensor PZT-Z01 --backend-url http://192.168.1.39:8000 --batches 1
  ```

- **Method B — Environment Configuration File (`simulator/.env`)**:
  Create or edit `simulator/.env` (copied from `simulator/.env.example`):
  ```env
  BACKEND_URL=http://192.168.1.39:8000
  ```

#### Critical Configuration Rules
- **Replace Example IP**: Replace `192.168.1.39` with Laptop 1's **current IPv4 address**.
- **Do NOT use `localhost` or `127.0.0.1`**: On Laptop 2, `localhost` points back to Laptop 2.
- **Do NOT hardcode example IPs permanently**: When moving between networks, update `BACKEND_URL` to reflect Laptop 1's new IP.
- **Runtime Configuration Only**: Changing `BACKEND_URL` is a runtime parameters update; source code modification is unnecessary.
- **Do NOT append `/api/v1/telemetry`**: Set `BACKEND_URL` to the base server origin (e.g. `http://192.168.1.39:8000`). The simulator client automatically appends REST endpoints (`/api/v1/telemetry` and `/api/v1/telemetry/live`).

---

### 9. Step 7 — Start the Next.js Dashboard

The Next.js frontend dashboard provides real-time GIS city mapping, 3D Digital Twin BIM visualization, telemetry HUD instrumentation, and the continuous Processing Inspector. The dashboard normally runs on **Laptop 1**.

From the `frontend/` directory on **Laptop 1**:
```powershell
# Laptop 1
cd frontend
npm run dev
```

#### Expected Access URL
Open Google Chrome on **Laptop 1** and navigate to:
[http://localhost:3000/dashboard](http://localhost:3000/dashboard)

> [!CAUTION]
> **Build Lifecycle Conflict Warning**:
> Do **NOT** execute `npm run build` while `npm run dev` is actively running against the same `frontend/.next` build directory. Running development and production build processes concurrently corrupts Next.js webpack compilation artifacts.

#### Known Issue & Recovery: `Error: Cannot find module './682.js'`
If `npm run build` was executed while `npm run dev` was running, or if stale webpack chunks persist in `.next`, Next.js will crash with an unhandled server error referencing missing module chunks (e.g., `Error: Cannot find module './682.js'`).

**Standard Recovery Procedure**:
1. Stop the active Next.js development server (`Ctrl + C` in Laptop 1 terminal).
2. Stop any orphaned Node processes if necessary (`Get-Process node | Stop-Process` in PowerShell).
3. Delete **ONLY** the build cache directory `frontend/.next`:
   ```powershell
   # Laptop 1 (frontend directory)
   Remove-Item -Recurse -Force .next
   ```
4. Restart the development server:
   ```powershell
   npm run dev
   ```
5. Reload `http://localhost:3000/dashboard` in the browser.

#### Production Testing Guidelines
If production bundle testing is explicitly required:
1. Stop the dev server (`npm run dev`) completely.
2. Run production compilation: `npm run build`.
3. Start production server: `npm run start`.

---

### 10. Step 8 — Start the Simulator on Laptop 2

Launch the physics-based PZT Virtual Sensor Simulator on **Laptop 2** to transmit telemetry packets over the LAN to Laptop 1 (`POST /api/v1/telemetry`).

From the `simulator/` directory on **Laptop 2**:
```powershell
# Laptop 2
cd simulator
.\.venv\Scripts\activate
python main.py --mode normal --sensor PZT-Z01 --backend-url http://<LAPTOP1_IP>:8000 --batches 1
```

#### Canonical Sensor Registry Rules
Aegis3D enforces strict identity matching based on `data/processed/bim/sensor_registry.json`. Use **ONLY** valid canonical sensor IDs:

| Sensor ID Range | Storey | Monitored Structural Zone | Application Behavior |
| :--- | :--- | :--- | :--- |
| **`PZT-Z01` – `PZT-Z04`** | `01 - Entry Level` | **Zone 2** (`Zone 2 - Substructure Pier B`) | Active monitoring zone; updates SHI and alerts |
| **`PZT-Z05` – `PZT-Z08`** | `02 - Floor` | **Zone 1** (`Zone 1 - Main Deck Girder`) | Active monitoring zone; updates SHI and alerts |
| **`PZT-Z09` – `PZT-Z12`** | `03 - Floor` | *Unassigned* | Valid Storey 03 canonical sensors unassigned to active monitoring zones (returns `HTTP 400 Bad Request` if submitted against Zone 1 or Zone 2) |

> [!WARNING]
> **Retired Sensor IDs**: Never use retired legacy sensor identifiers (such as `PZT-Z1-01`, `PZT-Z1-02`, `PZT-Z2-01`, `PZT-Z2-02`). They are completely removed from the schema and codebase.

---

### 11. Step 9 — Run a Healthy Test

Verify baseline normal operations using low-amplitude background noise telemetry.

From **Laptop 2**:
```bash
# Laptop 2
python main.py --mode normal --sensor PZT-Z01 --backend-url http://<LAPTOP1_IP>:8000 --batches 1
```

#### Expected Behavior & Results
- **Simulator Terminal Output (Laptop 2)**:
  `[SUCCESS] Telemetry accepted by backend (Status: 200 OK)`
- **Backend Log Output (Laptop 1)**:
  `POST /api/v1/telemetry 200 OK` processed in sub-15 ms with status `PROCESSED_NO_EVENT`.
- **Healthy Telemetry Parameters**:
  - Signal amplitude remains below event detection threshold ($V_{\text{thresh}}$).
  - Detected events: `0`.
  - Active alerts: `0` (no alerts triggered).
  - Zone Structural Health Indicator (SHI): Maintains **`100.0`** (`NORMAL`).
- **Verification Locations**:
  - Laptop 2 simulator CLI output.
  - Laptop 1 FastAPI Uvicorn logs.
  - Laptop 1 Next.js Telemetry HUD (`http://localhost:3000/dashboard`).
  - Laptop 1 3D Digital Twin (Zone 2 remains green).

---

### 12. Step 10 — Run an Anomaly Test

Verify stress wave detection, z-score evaluation, temporal persistence tracking, alert generation, and 3D Digital Twin highlighting.

From **Laptop 2**:
```bash
# Laptop 2
python main.py --mode anomaly --sensor PZT-Z05 --backend-url http://<LAPTOP1_IP>:8000 --batches 1
```

#### Complete Telemetry Execution Chain
```text
Laptop 2 Simulator
   │ Transmits high-amplitude PZT burst telemetry (peak ≈ 4.5V)
   ▼
Laptop 1 FastAPI Backend
   │ 1. Ingestion & DC offset subtraction
   │ 2. 4th-order Butterworth lowpass filtering
   │ 3. Contiguous sample event window detection
   │ 4. Spectral feature extraction (Peak, RMS, Energy, FFT dominant frequency)
   │ 5. Baseline reference z-score computation (|z| ≥ 3.0)
   │ 6. Temporal persistence ratio tracking
   │ 7. Health score deduction & alert evaluation
   │ 8. LiveEventBus broadcasts SSE stage events
   ▼
Laptop 1 Dashboard & 3D Digital Twin
   │ 1. Telemetry HUD updates waveform trace and status
   │ 2. Processing Inspector advances through stages 1 → 9
   │ 3. Active alert banner appears for Zone 1
   │ 4. 3D Digital Twin highlights Storey 02 / Main Deck Girder in red
```

#### Technical Terminology & Engineering Boundaries
- **Correct System Description**: Structural acoustic stress wave anomaly detected; baseline statistical deviation $|z| \ge 3.0$; structural inspection advised; zone/component-level BIM element highlighting updated.
- **Engineering Boundaries**: Aegis3D does **NOT** image cracks, calculate 2D/3D crack coordinates, predict structural collapse, or provide certified structural safety compliance ratings.

---

### 13. Step 11 — Verify Real-Time Processing / SSE

Verify that the client-side **Processing Inspector** (`TelemetryProcessingInspector.tsx`) receives real backend processing evidence via Server-Sent Events (`GET /api/v1/telemetry/live`).

#### Pipeline Stage Lifecycle
The authoritative backend executes the 9 processing stages sequentially:
1. `INGESTION`
2. `CONDITIONING`
3. `EVENT DETECTION`
4. `FEATURE EXTRACTION`
5. `BASELINE`
6. `ANOMALY`
7. `PERSISTENCE`
8. `CORRELATION`
9. `HEALTH / ALERT`

#### Client Presentation Lifecycle
- **Stage Progression State**: `READY` $\rightarrow$ `SENDING/TRANSMITTING` $\rightarrow$ `PROCESSING` $\rightarrow$ `SUCCESS` $\rightarrow$ `READY`.
- **Frontend Dwell Pacing**: Real backend processing completes in 5–15 ms. The frontend queue presents events with human-readable dwell timing (~350–500 ms per stage) while displaying actual backend execution duration in status badges (e.g., `STAGE 04 (12ms)`).
- **Automatic Page 1 Reset**: Upon receiving `PROCESSING_COMPLETED`, the Processing Inspector fetches the completed authoritative trace (`GET /api/v1/telemetry/{id}/processing-trace`) and **automatically snaps view pagination to Page 1 (Ingestion)**.
- **Completed Trace Inspection**: Presenters can manually click pagination controls (Pages 1 $\rightarrow$ 9) to inspect evidence without triggering additional backend processing.

---

### 14. Step 12 — Verify Dashboard + Digital Twin

After transmitting an anomaly packet from Laptop 2, verify visual updates across Laptop 1's dashboard:

#### Dashboard Engineering Console Checkpoints
1. **Active Alert Banner**: System Alert panel displays an active warning for **Zone 1** (`Zone 1 - Main Deck Girder`).
2. **Zone Health Summary**: Structural Health Indicator drops below 100.0, displaying `INSPECTION_ADVISED` or `HIGH_PRIORITY_INSPECTION`.
3. **2.5D City Map**: Building footprint polygon in Delhi updates visual status to reflect active alert condition.
4. **3D Digital Twin BIM Viewer**:
   - Storey `02 - Floor` / `Zone 1 - Main Deck Girder` is highlighted with structural anomaly color coding (amber/red).
   - Component structural groups highlight associated girder elements based on zone BIM mapping.

#### Inferred Zone Mapping Limitations
- Digital Twin highlighting maps anomalies to **zone-level and structural group-level BIM elements**.
- Highlighting does **NOT** represent exact physical crack coordinates or millimeter-level PZT surface locations.
- Missing telemetry packets or disconnected backend connections must not be interpreted as `HEALTHY`; the dashboard explicitly distinguishes `OFFLINE` status from healthy baseline operations.

#### Alert Clearing Behavior
When active alerts are dismissed or cleared via the API (`POST /api/v1/alerts/{id}/clear`), active alert banners dissolve and Digital Twin visual highlights revert to baseline status.

---

### 15. If the Wi-Fi Network or IP Address Changes

When moving between network locations (e.g. from home to hackathon venue, or switching Wi-Fi networks):

1. Connect both Laptop 1 and Laptop 2 to the new network.
2. Run `ipconfig` on **Laptop 1** to identify the new IPv4 address (e.g., `10.42.0.15`).
3. Verify Uvicorn on Laptop 1 is still running bound to `0.0.0.0:8000`.
4. Verify the Windows Firewall rule (`Aegis3D FastAPI LAN`) is active.
5. On **Laptop 2**, verify network connectivity to the new IP:
   ```powershell
   Test-NetConnection <NEW_LAPTOP1_IP> -Port 8000
   ```
6. On **Laptop 2**, verify HTTP backend liveness:
   ```cmd
   curl.exe http://<NEW_LAPTOP1_IP>:8000/health
   ```
7. Update **Laptop 2's** `BACKEND_URL`:
   - If using CLI flag: Pass `--backend-url http://<NEW_LAPTOP1_IP>:8000`.
   - If using `.env`: Update `BACKEND_URL=http://<NEW_LAPTOP1_IP>:8000` in `simulator/.env`.
8. Restart the simulator process on Laptop 2 if necessary.
9. Execute a normal test packet:
   `python main.py --mode normal --sensor PZT-Z01 --batches 1`
10. Confirm Laptop 1's dashboard receives and displays the telemetry.

> [!NOTE]
> You **normally do NOT need to modify backend or frontend source code** merely because Laptop 1 received a different LAN IP address.

---

### 16. Complete Startup Order

For reliable live presentations, execute commands in this exact canonical sequence:

```text
================================================================================
LAPTOP 1 (Platform Host)
================================================================================
1. Connect to Network          --> Verify Wi-Fi / Ethernet / Hotspot connection
2. Identify LAN IPv4           --> ipconfig (e.g. 192.168.1.39)
3. Start PostgreSQL            --> docker compose up -d postgres
4. Start FastAPI Backend       --> cd backend; uvicorn app.main:app --host 0.0.0.0 --port 8000
5. Verify Local Health         --> curl.exe http://127.0.0.1:8000/health
6. Verify Firewall Rule        --> Get-NetFirewallRule -DisplayName "Aegis3D FastAPI LAN"
7. Start Next.js Dashboard     --> cd frontend; npm run dev
8. Verify Dashboard Browser    --> http://localhost:3000/dashboard

================================================================================
LAPTOP 2 (Simulator Host)
================================================================================
1. Connect to Same Network     --> Join exact same Wi-Fi / LAN as Laptop 1
2. Check Network Layer Ping    --> ping <LAPTOP1_IP>
3. Check TCP Port 8000         --> Test-NetConnection <LAPTOP1_IP> -Port 8000
4. Check HTTP Health           --> curl.exe http://<LAPTOP1_IP>:8000/health
5. Configure Target URL        --> set BACKEND_URL=http://<LAPTOP1_IP>:8000
6. Start Simulator             --> cd simulator; .\.venv\Scripts\activate
7. Run Healthy Baseline Test   --> python main.py --mode normal --sensor PZT-Z01 --batches 1
8. Run Anomaly Test            --> python main.py --mode anomaly --sensor PZT-Z05 --batches 1
9. Verify Processing Inspector --> Observe 9-stage progression & Page 1 reset on Laptop 1
10. Verify 3D Digital Twin     --> Inspect zone highlighting on Laptop 1 dashboard
```

---

### 17. Troubleshooting

| Failure Layer | Observed Symptom | Underlying Root Cause | Exact Diagnostic & Recovery Action |
| :--- | :--- | :--- | :--- |
| **A. Physical LAN / Ping** | Laptop 2 `ping <LAPTOP1_IP>` fails (`Destination host unreachable` / `Request timed out`). | Laptops are on different network subnets, Wi-Fi AP isolation is active, or ICMP is blocked. | 1. Run `ipconfig` on both laptops to verify matching subnet prefixes.<br>2. Note that ping failure does **not** prove TCP is broken (ICMP may be blocked).<br>3. Proceed directly to `Test-NetConnection` to test TCP port 8000.<br>4. If network isolation persists, switch to **Mobile Hotspot** fallback. |
| **B. Firewall / Binding** | `Test-NetConnection <LAPTOP1_IP> -Port 8000` returns `TcpTestSucceeded : False`. | FastAPI Uvicorn bound strictly to `127.0.0.1`, Windows Firewall blocking port 8000, or network profile is `Public`. | 1. On Laptop 1, verify Uvicorn binding: `netstat -ano \| findstr :8000` (must show `0.0.0.0:8000 LISTENING`).<br>2. On Laptop 1 (Admin), re-add firewall rule: `New-NetFirewallRule -DisplayName "Aegis3D FastAPI LAN" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private`.<br>3. Check network profile: `Get-NetConnectionProfile`; set to `Private` if permitted. |
| **C. Routing / LAN IP** | `/health` works locally on Laptop 1 (`127.0.0.1:8000`), but fails from Laptop 2. | Firewall blocking inbound LAN traffic, or wrong IPv4 address entered on Laptop 2. | 1. Re-verify Laptop 1 IPv4 using `ipconfig`.<br>2. Confirm Laptop 1 firewall rule `Aegis3D FastAPI LAN` is enabled.<br>3. Test `curl.exe http://<LAPTOP1_IP>:8000/health` directly on Laptop 1's LAN IP interface. |
| **D. Simulator Config** | Simulator reports `API Disconnected` or `ECONNREFUSED`. | `BACKEND_URL` on Laptop 2 set to `localhost`/`127.0.0.1`, FastAPI not running, or wrong port. | 1. Ensure `BACKEND_URL` points to Laptop 1's LAN IP (e.g., `http://192.168.1.39:8000`).<br>2. Verify FastAPI Uvicorn process is running on Laptop 1.<br>3. Do **not** use `localhost` on Laptop 2. |
| **E. Telemetry Rejected** | Simulator sends telemetry but backend returns `HTTP 400 Bad Request`. | Telemetry packet contains invalid sensor/zone pair or unassigned sensor (`PZT-Z09`–`PZT-Z12`). | 1. Use canonical assigned sensors: `PZT-Z01`–`PZT-Z04` for Zone 2, or `PZT-Z05`–`PZT-Z08` for Zone 1.<br>2. Inspect Uvicorn tracebacks on Laptop 1.<br>3. Do not modify simulator DSP code. |
| **F. Real-Time SSE Stream** | Processing Inspector displays `SSE: DISCONNECTED` or `Connecting...`. | SSE endpoint `/api/v1/telemetry/live` blocked by network proxy or backend event bus error. | 1. Test `curl.exe http://<LAPTOP1_IP>:8000/api/v1/telemetry/live` in terminal.<br>2. Verify FastAPI backend process is active.<br>3. Note: HTTP telemetry ingestion can still succeed even if live SSE UI visualization disconnects. |
| **G. Frontend Stale State** | Simulator sends telemetry successfully, but Dashboard HUD does not update. | Dashboard connected to wrong backend IP, or browser state stale. | 1. Verify `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` points to correct FastAPI host.<br>2. Hard-refresh browser (`Ctrl + F5`).<br>3. Verify backend emitted `POST /api/v1/telemetry 200 OK`. |
| **H. 3D Twin Highlight** | Telemetry processed with anomaly, but 3D Digital Twin element does not highlight. | Active alert not generated, or BIM zone mapping unassigned. | 1. Check if $|z| \ge 3.0$ threshold was exceeded.<br>2. Verify active alert appears in System Alerts panel.<br>3. Note that Digital Twin highlights structural zones, not exact 3D crack points. |
| **I. Next.js Chunk Error** | `Error: Cannot find module './682.js'` from `webpack-runtime.js`. | `npm run build` was executed while `npm run dev` was actively running, corrupting `.next` artifacts. | **Safe Recovery**: <br>1. Stop Next.js dev server on Laptop 1.<br>2. Delete build directory: `Remove-Item -Recurse -Force frontend/.next`.<br>3. Restart dev server: `cd frontend; npm run dev`. *(Do NOT delete `node_modules` or source files)*. |
| **J. Unstyled Frontend** | Dashboard renders completely unstyled plain HTML, with `API: DISCONNECTED`. | Next.js development build cache corrupted or CSS compilation failed. | 1. Stop Next.js dev server.<br>2. Delete `frontend/.next`.<br>3. Restart `npm run dev`.<br>4. Do not rewrite UI code. |
| **K. Hackathon Network** | Setup worked on Home Wi-Fi but fails at Hackathon venue network. | Venue Wi-Fi enforces Client AP Isolation or assigned new IP addresses. | 1. Re-run `ipconfig` on Laptop 1 to obtain new venue IP.<br>2. Test `Test-NetConnection <NEW_IP> -Port 8000`.<br>3. If AP isolation blocks traffic, switch to **Mobile Hotspot** fallback. |
| **L. Hotspot Fallback** | Venue Wi-Fi completely blocks laptop-to-laptop traffic. | Network router enforces AP Isolation. | 1. Turn on Mobile Hotspot on Laptop 1 (or smartphone).<br>2. Connect Laptop 2 to Hotspot Wi-Fi.<br>3. Obtain Laptop 1 Hotspot adapter IP via `ipconfig`.<br>4. Update `BACKEND_URL` on Laptop 2. |

---

### 18. Quick Hackathon Checklist

Print or scan this quick checklist at the venue before demonstration:

- [ ] **Network**: Laptop 1 and Laptop 2 connected to the same Wi-Fi, Ethernet, or Hotspot network.
- [ ] **Laptop 1 IP**: Active IPv4 address identified via `ipconfig` on Laptop 1.
- [ ] **PostgreSQL**: PostgreSQL container running on Laptop 1 (`docker compose up -d postgres`).
- [ ] **FastAPI Backend**: FastAPI running on Laptop 1 bound to `0.0.0.0:8000`.
- [ ] **FastAPI Liveness**: `http://127.0.0.1:8000/health` returns `200 OK` on Laptop 1.
- [ ] **Windows Firewall**: Inbound TCP rule `Aegis3D FastAPI LAN` active for port 8000 on Laptop 1.
- [ ] **Laptop 2 TCP Test**: `Test-NetConnection <LAPTOP1_IP> -Port 8000` returns `TcpTestSucceeded : True` on Laptop 2.
- [ ] **Laptop 2 HTTP Test**: `curl.exe http://<LAPTOP1_IP>:8000/health` returns `200 OK` on Laptop 2.
- [ ] **Simulator Config**: `BACKEND_URL` on Laptop 2 points to `http://<LAPTOP1_IP>:8000` (no trailing path).
- [ ] **Next.js Dashboard**: Next.js running on Laptop 1 (`npm run dev`) and accessible at `http://localhost:3000/dashboard`.
- [ ] **Build Safety**: No `npm run build` running concurrently with `npm run dev`.
- [ ] **Healthy Test**: `python main.py --mode normal --sensor PZT-Z01 --batches 1` succeeds from Laptop 2.
- [ ] **Anomaly Test**: `python main.py --mode anomaly --sensor PZT-Z05 --batches 1` succeeds from Laptop 2.
- [ ] **Processing Inspector**: Stage progression 1 $\rightarrow$ 9 and automatic Page 1 reset verified on Laptop 1.
- [ ] **3D Digital Twin**: Zone 1 highlight and active alert banner verified on Laptop 1 dashboard.
- [ ] **IP Change Procedure**: Procedure understood for updating `BACKEND_URL` if venue IP changes.

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
