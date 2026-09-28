"""Unit tests for VirtualPZTSensor abstraction."""

from datetime import datetime, timezone
import os
import sys
import pytest

from simulator.config import ZONE_MAIN_DECK, ZONE_SUBSTRUCTURE
from simulator.sensors.virtual_pzt import VirtualPZTSensor

# Optionally verify against backend Pydantic model if backend is present in environment
try:
    from app.schemas.telemetry import TelemetryIngestRequest
    HAVE_BACKEND_SCHEMA = True
except ImportError:
    HAVE_BACKEND_SCHEMA = False


def test_virtual_pzt_initialization_and_inference():
    """Verify sensor initialization and zone name auto-inference."""
    # Sensor in Zone 1
    s1 = VirtualPZTSensor(sensor_id="PZT-Z1-01")
    assert s1.sensor_id == "PZT-Z1-01"
    assert s1.zone_name == ZONE_MAIN_DECK
    assert s1.sample_rate_hz == 1000.0
    assert s1.sequence == 1

    # Sensor in Zone 2
    s2 = VirtualPZTSensor(sensor_id="PZT-Z2-01")
    assert s2.zone_name == ZONE_SUBSTRUCTURE

    # Custom zone override
    s_custom = VirtualPZTSensor(sensor_id="PZT-CUSTOM", zone_name="Custom Structural Area")
    assert s_custom.zone_name == "Custom Structural Area"


def test_virtual_pzt_invalid_init_parameters():
    """Verify validation on sensor initialization."""
    with pytest.raises(ValueError, match="sensor_id cannot be empty"):
        VirtualPZTSensor(sensor_id="")

    with pytest.raises(ValueError, match="sample_rate_hz must be positive"):
        VirtualPZTSensor(sensor_id="PZT-Z1-01", sample_rate_hz=0)

    with pytest.raises(ValueError, match="initial_sequence cannot be negative"):
        VirtualPZTSensor(sensor_id="PZT-Z1-01", initial_sequence=-5)


def test_generate_payload_monotonic_sequence():
    """Verify sequence counter increments monotonically across payload calls."""
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-01", initial_sequence=100)

    p1 = sensor.generate_payload(mode="normal", sample_count=50)
    assert p1["sequence"] == 100

    p2 = sensor.generate_payload(mode="normal", sample_count=50)
    assert p2["sequence"] == 101

    p3 = sensor.generate_payload(mode="anomaly", sample_count=50)
    assert p3["sequence"] == 102


def test_payload_contract_adherence_and_backend_schema_validation():
    """Verify generated payload satisfies the backend TelemetryIngestRequest schema."""
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-01", zone_name=ZONE_MAIN_DECK)
    payload = sensor.generate_payload(mode="anomaly", sample_count=200, seed=42)

    # 1. Structural keys
    assert payload["sensor_id"] == "PZT-Z1-01"
    assert payload["zone_name"] == ZONE_MAIN_DECK
    assert payload["sample_rate_hz"] == 1000.0
    assert isinstance(payload["samples"], list)
    assert len(payload["samples"]) == 200

    # 2. Strict non-inclusion of backend decisions
    forbidden_keys = [
        "anomaly",
        "is_anomalous",
        "severity",
        "health",
        "health_score",
        "alert",
        "alert_generated",
        "event_detected",
        "correlation",
    ]
    for key in forbidden_keys:
        assert key not in payload, f"Simulator payload must not contain backend decision key '{key}'"

    # 3. Backend Pydantic validation (when available)
    if HAVE_BACKEND_SCHEMA:
        request_model = TelemetryIngestRequest(**payload)
        assert request_model.sensor_id == "PZT-Z1-01"
        assert request_model.zone_name == ZONE_MAIN_DECK
        assert len(request_model.samples) == 200


def test_generate_payload_custom_samples_and_overrides():
    """Verify custom samples and optional parameters (detection_threshold, session_id)."""
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-02", zone_name=ZONE_MAIN_DECK)
    custom_samples = [0.01, 0.02, 0.03, 0.04]
    custom_ts = datetime(2026, 9, 28, 14, 0, 0, tzinfo=timezone.utc)

    payload = sensor.generate_payload(
        samples=custom_samples,
        timestamp=custom_ts,
        detection_threshold=0.85,
        session_id=42,
    )

    assert payload["samples"] == custom_samples
    assert payload["timestamp"] == "2026-09-28T14:00:00+00:00"
    assert payload["detection_threshold"] == 0.85
    assert payload["session_id"] == 42


def test_generate_payload_unsupported_mode():
    """Verify error on unsupported signal mode."""
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-01")
    with pytest.raises(ValueError, match="Unsupported signal mode"):
        sensor.generate_payload(mode="unknown_mode")
