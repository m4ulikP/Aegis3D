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

*Note: The script automatically falls back to `sqlite:///aegis3d_dev.db` if `DATABASE_URL` is not set, providing zero-config execution for local development.*

To connect to PostgreSQL or a specific database:
```bash
DATABASE_URL=postgresql+psycopg2://aegis_user:aegis_password@localhost:5432/aegis3d python scripts/seed_demo.py
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
