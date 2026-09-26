# Aegis3D

## Smart PZT-Based Structural Health Monitoring & Early-Warning System

### Team BRIKS
- Maulik Pandey
- Shikhar Sadhu
- Pratyush Bhaskar Ram
- Madhav Kumar

### MAITRON 2026
Hardware Track  
SDG 11 — Sustainable Cities and Communities

---

### Overview

Aegis3D is a Smart PZT-Based Structural Health Monitoring & Early-Warning System prototype designed to continuously observe acoustic and elastic structural activity. By analyzing signals collected across multi-sensor PZT nodes, Aegis3D helps identify potential structural stress anomalies and prioritize specific locations for targeted physical inspection.

> **Note on Scope**: Aegis3D is an early-warning and continuous monitoring prototype. It does not provide exact structural collapse prediction, guaranteed disaster prevention, formal structural certification, machine learning inference, or real-world deployment validation.

---

### Current Scope

- PZT sensors (Piezoelectric transducer arrays)
- ESP32 microcontroller with built-in ADC
- Analog signal conditioning circuitry
- Wi-Fi and MQTT protocol communication
- Signal processing and baseline metric extraction
- Building-specific baseline comparison
- Rule-based anomaly detection
- Multi-PZT signal correlation
- Trend analysis over time
- Structural Health Indicator scoring
- FastAPI backend application
- PostgreSQL database
- Next.js / React / TypeScript dashboard frontend

*No machine learning is used in the current MVP.*  
*No IMU or temperature/humidity sensing is included in the current MVP.*

---

### Repository Structure

- **`firmware/`**: ESP32 PlatformIO project scaffolding, PZT sampling, and MQTT client definitions.
- **`backend/`**: FastAPI application service, database schemas, rules engine, and API endpoints.
- **`frontend/`**: Next.js dashboard visual interface and components.
- **`hardware/`**: Circuit schematics, PCB layout specs, BOM, and hardware prototype documentation.
- **`signal-processing/`**: Signal processing pipelines, filtering, event detection, baseline, and correlation modules.
- **`data/`**: Raw and processed signal data storage folders.
- **`docs/`**: Architecture diagrams, protocols, test plans, and presentation assets.
- **`scripts/`**: Development and data utility scripts.

---

### Team Ownership

- **Maulik Pandey**: Backend + system integration
- **Madhav Kumar**: Backend + signal processing + validation
- **Shikhar Sadhu**: Frontend + hardware/firmware integration
- **Pratyush Bhaskar Ram**: Frontend + visualization

---

### Development Status

Repository scaffold created. Implementation has not started yet.
