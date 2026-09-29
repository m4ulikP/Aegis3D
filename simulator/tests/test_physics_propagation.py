"""
Focused unit and integration tests for the Aegis3D physics-driven
guided-wave propagation, structural damage, and localized scattering model.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from simulator.physics import (
    DamageEffect,
    DamageModel,
    PropagationPath,
    ReceiverAcquisition,
)
from simulator.sensors.virtual_pzt import VirtualPZTSensor
from simulator.signal_generator import generate_pzt_tone_burst

try:
    from app.schemas.telemetry import TelemetryIngestRequest
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE_BACKEND = True
except ImportError:
    HAVE_BACKEND = False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NETWORK_PATH = PROJECT_ROOT / "data" / "processed" / "bim" / "propagation_network.json"


@pytest.fixture
def sample_path() -> PropagationPath:
    """Fixture providing a known 16.3m structural propagation path (PZT-Z04 -> PZT-Z05)."""
    return PropagationPath(
        actuator_id="PZT-Z04",
        receiver_id="PZT-Z05",
        component_guids=("2UD3D7uxP8kecbbBCRtz8h", "1WrzGm1SD2ev45B_OWQ3El", "2UD3D7uxP8kecbbBCRtzBI"),
        distance_m=16.30,
        wave_velocity_m_s=3200.0,
        attenuation_db_per_m=0.8,
    )


@pytest.fixture
def sample_influences() -> list[dict]:
    """Fixture providing component influences for PATH-007."""
    return [
        {
            "ifc_guid": "1WrzGm1SD2ev45B_OWQ3El",
            "distance_to_path_m": 0.45,
            "path_position": 0.52,
            "influence_factor": 0.6958,
        }
    ]


def test_deterministic_healthy_waveform(sample_path: PropagationPath):
    """Verify that identical parameters produce byte-for-byte identical healthy signals."""
    excitation1 = generate_pzt_tone_burst(sample_count=1000, sample_rate_hz=100_000.0)
    excitation2 = generate_pzt_tone_burst(sample_count=1000, sample_rate_hz=100_000.0)
    assert excitation1 == excitation2

    prop1 = sample_path.propagate(excitation1, sample_rate_hz=100_000.0)
    prop2 = sample_path.propagate(excitation2, sample_rate_hz=100_000.0)
    assert prop1 == prop2


def test_deterministic_damaged_waveform(sample_path: PropagationPath, sample_influences: list[dict]):
    """Verify that identical damage configuration produces deterministic damaged signals."""
    excitation = generate_pzt_tone_burst(sample_count=1000, sample_rate_hz=100_000.0)

    model1 = DamageModel()
    model1.set_damaged_component("1WrzGm1SD2ev45B_OWQ3El")
    effect1 = model1.get_path_effect(sample_influences, sample_rate_hz=100_000.0)

    model2 = DamageModel()
    model2.set_damaged_component("1WrzGm1SD2ev45B_OWQ3El")
    effect2 = model2.get_path_effect(sample_influences, sample_rate_hz=100_000.0)

    prop1 = sample_path.propagate(excitation, sample_rate_hz=100_000.0, damage_effect=effect1)
    prop2 = sample_path.propagate(excitation, sample_rate_hz=100_000.0, damage_effect=effect2)
    assert prop1 == prop2


def test_propagation_delay_increases_with_distance():
    """Verify that acoustic travel time delay is strictly monotonic with path distance."""
    p_short = PropagationPath("Z01", "Z02", ("g1",), distance_m=5.0, wave_velocity_m_s=3200.0)
    p_long = PropagationPath("Z01", "Z03", ("g1", "g2"), distance_m=15.0, wave_velocity_m_s=3200.0)

    assert p_long.propagation_delay_s > p_short.propagation_delay_s
    assert p_long.propagation_delay_ms == pytest.approx(15.0 / 3200.0 * 1000.0)
    assert p_short.propagation_delay_ms == pytest.approx(5.0 / 3200.0 * 1000.0)


def test_attenuation_responds_to_path_distance():
    """Verify that dB attenuation increases and linear amplitude factor decreases with distance."""
    p_short = PropagationPath("Z01", "Z02", ("g1",), distance_m=4.0, wave_velocity_m_s=3200.0, attenuation_db_per_m=0.8)
    p_long = PropagationPath("Z01", "Z03", ("g1", "g2"), distance_m=16.0, wave_velocity_m_s=3200.0, attenuation_db_per_m=0.8)

    assert p_long.attenuation_db > p_short.attenuation_db
    assert p_long.amplitude_factor < p_short.amplitude_factor
    assert p_long.amplitude_factor == pytest.approx(10.0 ** (- (0.8 * 16.0) / 20.0))


def test_healthy_contains_no_damage_scattering(sample_path: PropagationPath):
    """Verify that a healthy path contains no secondary scattering arrival."""
    excitation = generate_pzt_tone_burst(sample_count=2000, sample_rate_hz=100_000.0, amplitude=0.8)
    healthy_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0, damage_effect=None)

    total_delay = round(sample_path.propagation_delay_s * 100_000.0)
    burst_len = round(5 / 10_000.0 * 100_000.0)  # 50 samples

    # Beyond primary burst window, healthy signal is quiet (zero)
    quiet_region = healthy_prop[total_delay + burst_len + 50 : total_delay + burst_len + 300]
    assert len(quiet_region) > 0
    assert all(abs(val) == 0.0 for val in quiet_region)


def test_damaged_contains_localized_scattering(sample_path: PropagationPath, sample_influences: list[dict]):
    """Verify that a damaged path contains a localized secondary scattering arrival."""
    excitation = generate_pzt_tone_burst(sample_count=2000, sample_rate_hz=100_000.0, amplitude=0.8)

    model = DamageModel()
    model.set_damaged_component("1WrzGm1SD2ev45B_OWQ3El")
    effect = model.get_path_effect(sample_influences, sample_rate_hz=100_000.0)

    damaged_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0, damage_effect=effect)

    total_delay = round(sample_path.propagation_delay_s * 100_000.0) + effect.delay_shift_samples
    scat_start = total_delay + effect.scattering_delay_samples

    # Region around secondary scattering contains active samples
    scat_region = damaged_prop[scat_start : scat_start + 50]
    assert len(scat_region) > 0
    assert max(abs(val) for val in scat_region) > 0.1


def test_damage_is_not_global_gain(sample_path: PropagationPath, sample_influences: list[dict]):
    """Assert that damage does NOT globally amplify the waveform; primary wave is attenuated."""
    excitation = generate_pzt_tone_burst(sample_count=2000, sample_rate_hz=100_000.0, amplitude=0.8)

    model = DamageModel()
    model.set_damaged_component("1WrzGm1SD2ev45B_OWQ3El")
    effect = model.get_path_effect(sample_influences, sample_rate_hz=100_000.0)

    healthy_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0)
    damaged_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0, damage_effect=effect)

    h_delay = round(sample_path.propagation_delay_s * 100_000.0)
    d_delay = h_delay + effect.delay_shift_samples

    h_primary_peak = max(abs(x) for x in healthy_prop[h_delay : h_delay + 60])
    d_primary_peak = max(abs(x) for x in damaged_prop[d_delay : d_delay + 60])

    # The primary wave arrival in the damaged state is WEAKER than healthy (attenuation_multiplier < 1.0)
    assert d_primary_peak < h_primary_peak
    assert d_primary_peak == pytest.approx(h_primary_peak * effect.attenuation_multiplier, rel=1e-3)


def test_scattering_parameters_deterministic(sample_influences: list[dict]):
    """Verify scattering delay and amplitude calculations are deterministic."""
    model = DamageModel(max_scattering_amplitude=0.65, scattering_delay_ms=1.5)
    model.set_damaged_component("1WrzGm1SD2ev45B_OWQ3El")
    effect = model.get_path_effect(sample_influences, sample_rate_hz=100_000.0)

    expected_delay = round(1.5 * 0.001 * 100_000.0)  # 150 samples
    expected_amplitude = 0.65 * 0.6958

    assert effect.scattering_delay_samples == expected_delay
    assert effect.scattering_amplitude == pytest.approx(expected_amplitude, rel=1e-4)


def test_healthy_remains_below_event_threshold(sample_path: PropagationPath):
    """Verify that after receiver acquisition, healthy peak stays below backend threshold (1.05)."""
    receiver = ReceiverAcquisition(gain=5.0)
    excitation = generate_pzt_tone_burst(sample_count=2000, sample_rate_hz=100_000.0, amplitude=0.8)
    healthy_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0)
    healthy_sig = receiver.apply(healthy_prop)

    healthy_peak = max(abs(x) for x in healthy_sig)
    # Zone 2 baseline is 0.85 + 2*0.10 = 1.05
    assert healthy_peak < 1.05
    assert healthy_peak == pytest.approx(0.840, abs=0.06)


@pytest.mark.skipif(not HAVE_BACKEND, reason="FastAPI backend not importable in test environment")
def test_damaged_creates_detectable_backend_event(sample_path: PropagationPath, sample_influences: list[dict]):
    """Verify that damaged waveform produces a detectable event and anomaly in backend."""
    client = TestClient(app)
    receiver = ReceiverAcquisition(gain=5.0)
    excitation = generate_pzt_tone_burst(sample_count=10_000, sample_rate_hz=100_000.0, amplitude=0.8)

    # 1. Healthy Telemetry
    healthy_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0)
    healthy_sig = receiver.apply(healthy_prop)

    h_payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": "Zone 2 - Substructure Pier B",
        "sample_rate_hz": 100_000.0,
        "sequence": 501,
        "samples": healthy_sig,
    }
    h_resp = client.post("/api/v1/telemetry", json=h_payload)
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert h_data["status"] == "PROCESSED_NO_EVENT"
    assert h_data["events_detected"] == 0

    # 2. Damaged Telemetry
    model = DamageModel()
    model.set_damaged_component("1WrzGm1SD2ev45B_OWQ3El")
    effect = model.get_path_effect(sample_influences, sample_rate_hz=100_000.0)

    damaged_prop = sample_path.propagate(excitation, sample_rate_hz=100_000.0, damage_effect=effect)
    damaged_sig = receiver.apply(damaged_prop)

    d_payload = {
        "sensor_id": "PZT-Z01",
        "zone_name": "Zone 2 - Substructure Pier B",
        "sample_rate_hz": 100_000.0,
        "sequence": 502,
        "samples": damaged_sig,
    }
    d_resp = client.post("/api/v1/telemetry", json=d_payload)
    assert d_resp.status_code == 200
    d_data = d_resp.json()
    assert d_data["status"] == "PROCESSED_ANOMALY_DETECTED"
    assert d_data["events_detected"] >= 1
    assert any(evt["is_anomalous"] for evt in d_data["events"])
    assert d_data["health_score"] is not None
