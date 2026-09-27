# Aegis3D Demo Dataset Seeding Guide

This guide describes the reproducible demo dataset seeder mechanism created for Aegis3D backend & frontend integration.

---

## 1. Overview & Purpose

The Aegis3D demo dataset populates the backend database with a complete, realistic, and internally coherent structural monitoring scenario. This allows frontend developers to instantly inspect all 8 Step 11 REST API endpoints with rich, connected structural data without manually generating signals or database rows.

---

## 2. Seeded Entities & Scenario Summary

Running the seed command creates the following domain entities using existing application logic:

| Entity | Count | Details & Role in Demo Scenario |
| :--- | :---: | :--- |
| **Zone** | 2 | **Zone 1** (`Zone 1 - Main Deck Girder`, Level 2)<br>**Zone 2** (`Zone 2 - Substructure Pier B`, Substructure) |
| **MonitoringSession** | 1 | `Demo Structural Health Session` (Mode: `LIVE`, Status: `RUNNING`) |
| **Baseline** | 2 | Historical statistical baselines for Zone 1 ($\mu=1.20, \sigma=0.15$) and Zone 2 ($\mu=0.85, \sigma=0.10$) |
| **Event** | 10 | **Zone 1**: 4 normal historical events + 4 anomalous events<br>**Zone 2**: 2 normal historical events |
| **HealthSnapshot** | 2 | Evaluated dynamically via `HealthService.evaluate_zone_health` for both zones |
| **Alert** | 1 | Active `HIGH` severity alert (`Cross-Sensor Structural Anomaly Cluster`) linked to Zone 1 |

### Demo Anomaly & Correlation Highlights in Zone 1:
- **Rule-Based Anomalies**: 4 recent events exceed baseline z-score threshold ($|z| > 3.0\sigma$).
- **2-PZT Cross-Sensor Correlation**: Events `A1` and `A2` occur across sensors `PZT-Z1-01` and `PZT-Z1-02` within a 15ms window (triggers 2-PZT cross-sensor correlation).
- **Temporal Persistence**: Multiple anomalous observations occur within the 5-minute persistence window.
- **Structural Health Indicator (SHI)**: Evaluates reduced health score reflecting recent acoustic emission anomalies.

---

## 3. How to Run the Seed

Execute the single CLI script from the `backend/` directory:

```bash
python scripts/seed_demo.py
```

The script connects to the application's configured PostgreSQL database (`postgresql+psycopg2://aegis_user:aegis_password@localhost:5432/aegis3d` by default, or the `DATABASE_URL` specified in your environment).

To pass a custom PostgreSQL database URL:
```bash
DATABASE_URL=postgresql+psycopg2://custom_user:pass@host:5432/dbname python scripts/seed_demo.py
```

---

## 4. Idempotency & Reset

- **Idempotent by Default**: If demo data is already present in the database, running `python scripts/seed_demo.py` will report `ALREADY_SEEDED` and safely skip duplicate row insertion.
- **Explicit Reset/Reseed**: To purge prior demo records and perform a clean re-seed, pass the `--reset` (or `-r`) flag:
  ```bash
  python scripts/seed_demo.py --reset
  ```

---

## 5. API Inspection Endpoints

Once seeded, start the FastAPI server (`uvicorn app.main:app --reload`) and query any of the REST endpoints:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/zones` | `GET` | List all zones (includes Zone 1 and Zone 2) |
| `/api/v1/zones/1` | `GET` | Zone 1 metadata, event counts, active alert count |
| `/api/v1/zones/1/events` | `GET` | List Zone 1 events (filtered by limit, severity, or status) |
| `/api/v1/zones/1/health` | `GET` | Latest Zone 1 HealthSnapshot score, status, and disclaimer |
| `/api/v1/zones/1/trend` | `GET` | Zone 1 trend analysis comparing period anomaly rates |
| `/api/v1/zones/1/correlation` | `GET` | Zone 1 temporal persistence & 2-PZT correlated groups |
| `/api/v1/alerts` | `GET` | List active alerts (includes Zone 1 anomaly cluster alert) |
| `/api/v1/health/summary` | `GET` | Overall dashboard health status summary across all zones |

---

## 6. Limitations & Architectural Disclaimers

1. **Simulated PZT Telemetry**: The seeded PZT event data consists of simulated signals for demonstration and software integration. Physical PZT sensors or hardware microcontrollers are **not** required to run the demo seed or backend API.
2. **No Real Physical Measurements**: The seeded dataset must **not** be interpreted as real physical structural material measurements, crack growth, or safety evaluations.
3. **Prototype SHI Indicator**: The Structural Health Indicator (SHI) is a prototype evidence-based monitoring indicator summarizing statistical acoustic emission evidence. It is **NOT** a certified structural safety score or material integrity certificate.
4. **Relative Arrival Timing**: Two-PZT event correlation evaluates relative source arrival timing across two sensing channels within a zone. It does **NOT** provide 3D spatial crack localization.
5. **Software Monitoring Pipeline**: Physical hardware telemetry represents a future input path; the current seed exists to exercise and demonstrate the software monitoring pipeline.
