# Aegis3D Telemetry Ingestion & Processing Pipeline

## 1. Overview & Purpose
The Aegis3D Telemetry Layer provides discrete sensor time-series ingestion for the structural digital twin platform.

> [!NOTE]
> Telemetry ingested by this endpoint represents simulated / representative software sensor data for the Aegis3D prototype. It does not establish direct real physical PZT hardware acquisition or certified structural safety measurements.

---

## 2. Ingestion Endpoint
- **Method**: `POST`
- **Path**: `/api/v1/telemetry`
- **Content-Type**: `application/json`
- **Response Status**: `200 OK`

---

## 3. Telemetry Contract

### Request Schema (`TelemetryIngestRequest`)
| Field | Type | Required | Description |
|---|---|---|---|
| `sensor_id` | `string` | Yes | Stable sensor identifier (e.g., `"PZT-Z1-01"`, `"PZT-Z2-01"`). |
| `zone_name` | `string` | Yes | Stable domain zone name (e.g., `"Zone 1 - Main Deck Girder"`). |
| `timestamp` | `datetime` | No (default UTC now) | Sensor acquisition timestamp in UTC. |
| `sample_rate_hz` | `float` | Yes | Sampling frequency in Hz (`> 0`, alias `"sample_rate"`). |
| `sequence` | `integer` | No | Monotonic sequence packet counter (`>= 0`). |
| `samples` | `List[float]` | Yes | 1D discrete sample array (length `1` to `100,000`, finite numbers). |
| `detection_threshold` | `float` | No | Optional amplitude threshold override for event detection. |
| `session_id` | `integer` | No | Optional monitoring session ID override. |

### Example Request
```json
{
  "sensor_id": "PZT-Z1-01",
  "zone_name": "Zone 1 - Main Deck Girder",
  "timestamp": "2026-09-28T12:00:00Z",
  "sample_rate_hz": 1000.0,
  "sequence": 1042,
  "samples": [0.01, 0.02, 0.01, 4.5, 4.2, 3.8, 0.02, 0.01]
}
```

### Example Response (`TelemetryIngestResponse`)
```json
{
  "status": "PROCESSED_ANOMALY_DETECTED",
  "telemetry_accepted": true,
  "sensor_id": "PZT-Z1-01",
  "zone_id": 1,
  "zone_name": "Zone 1 - Main Deck Girder",
  "timestamp": "2026-09-28T12:00:00Z",
  "samples_count": 8,
  "sample_rate_hz": 1000.0,
  "sequence": 1042,
  "events_detected": 1,
  "events": [
    {
      "event_id": 42,
      "magnitude": 4.5,
      "energy": 53.4,
      "duration_ms": 3.0,
      "frequency_hz": 100.0,
      "severity": "HIGH",
      "is_anomalous": true,
      "magnitude_z_score": 22.0,
      "energy_z_score": 27.6,
      "anomaly_reasons": [
        "Magnitude deviation (|z| = 22.00σ) exceeded statistical threshold (3.00σ)",
        "Energy deviation (|z| = 27.60σ) exceeded statistical threshold (3.00σ)"
      ]
    }
  ],
  "extracted_features": {
    "peak_amplitude": 4.5,
    "rms_amplitude": 2.58,
    "energy": 53.4,
    "duration_ms": 3.0,
    "frequency_hz": 100.0,
    "sample_count": 3
  },
  "temporal_persistence_confirmed": false,
  "cross_sensor_correlation_confirmed": false,
  "health_score": 75.0,
  "health_status": "MONITOR",
  "health_trend": "STABLE",
  "alert_generated": false,
  "alert_id": null,
  "alert_severity": null,
  "alert_title": null,
  "message": "Telemetry from 'PZT-Z1-01' processed: 1 event(s) detected. SHI: 75.0/100 (MONITOR)."
}
```

---

## 4. End-to-End Processing Flow

```
Virtual / Representative Sensor Telemetry
        ↓
POST /api/v1/telemetry
        ↓
Resolve Zone Name & Validate Sensor Consistency
        ↓
Convert to hardware-agnostic SampledSignal
        ↓
Signal Preprocessing (DC Offset Subtraction)
        ↓
Bandpass / Moving Average Smoothing
        ↓
Threshold Activity Detection (`detect_events`)
        ↓
[Is Amplitude Burst Detected?]
  ├─ NO  → Return `PROCESSED_NO_EVENT` (0 events, no DB insertion)
  └─ YES → Feature Extraction (`extract_features`: peak, RMS, energy, duration, FFT frequency)
              ↓
           Persist `Event` Entity to Database
              ↓
           Statistical Z-Score Anomaly Analysis (`AnomalyService`)
              ↓
           Temporal Persistence & 2-PZT Cross-Sensor Correlation (`CorrelationService`)
              ↓
           Zone Structural Health Indicator (SHI) Recalculation (`HealthService`)
              ↓
           Persist `HealthSnapshot`
              ↓
           [Is SHI Status Critical / Alert Warranted?]
             ├─ YES → Persist `Alert` Record in Database
             └─ NO  → Continue
              ↓
           Return Structured `TelemetryIngestResponse`
```

---

## 5. Sensor & Zone Identity Resolution
- **Stable Zone Identity**: Uses immutable domain zone names (`"Zone 1 - Main Deck Girder"`, `"Zone 2 - Substructure Pier B"`). The backend dynamically resolves the active PostgreSQL autoincrement primary key ID.
- **Stable Sensor Identity**: Identifiers follow standard naming convention (`"PZT-Z1-01"`, `"PZT-Z1-02"`, `"PZT-Z2-01"`). Inconsistent sensor/zone combinations (e.g. `PZT-Z2-01` sent for Zone 1) are rejected with HTTP 400.

---

## 6. What the Telemetry Endpoint Does NOT Do
1. **No direct event pre-classification**: The client cannot declare an event or force an alert directly. The backend signal processing pipeline makes all detection and anomaly decisions.
2. **No arbitrary DB bypass**: Detected events and resulting health snapshots are validated and persisted through the domain repository/service layers.
3. **No certified physical damage ratings**: Telemetry calculations serve software visualization and prototyping only.
