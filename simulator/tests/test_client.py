"""Unit tests for simulator HTTP telemetry client."""

from io import BytesIO
import json
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from simulator.client import TelemetryClient


def test_successful_telemetry_post():
    """Verify successful HTTP 200 response parsing into structured client result."""
    client = TelemetryClient(backend_url="http://localhost:8000")

    mock_response_data = {
        "status": "PROCESSED_ANOMALY_DETECTED",
        "telemetry_accepted": True,
        "sensor_id": "PZT-Z01",
        "zone_id": 1,
        "zone_name": "Zone 1 - Main Deck Girder",
        "timestamp": "2026-09-28T12:00:00Z",
        "samples_count": 500,
        "sample_rate_hz": 1000.0,
        "sequence": 42,
        "events_detected": 1,
        "events": [],
        "temporal_persistence_confirmed": False,
        "cross_sensor_correlation_confirmed": False,
        "health_score": 75.0,
        "health_status": "MONITOR",
        "health_trend": "STABLE",
        "alert_generated": True,
        "alert_severity": "MEDIUM",
        "message": "Telemetry processed successfully.",
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = client.send_telemetry({"sensor_id": "PZT-Z01", "samples": [0.1]})

    assert result.success is True
    assert result.status_code == 200
    assert result.backend_status == "PROCESSED_ANOMALY_DETECTED"
    assert result.events_detected == 1
    assert result.health_score == 75.0
    assert result.health_status == "MONITOR"
    assert result.alert_generated is True
    assert result.alert_severity == "MEDIUM"
    assert result.message == "Telemetry processed successfully."


def test_connection_failure_handled_cleanly():
    """Verify network connection refusal returns clean error without crashing."""
    client = TelemetryClient(backend_url="http://192.168.1.99:8000")

    url_error = urllib.error.URLError(reason="Connection refused")
    with patch("urllib.request.urlopen", side_effect=url_error):
        result = client.send_telemetry({"sensor_id": "PZT-Z01", "samples": [0.1]})

    assert result.success is False
    assert result.status_code == 0
    assert "Backend unreachable at http://192.168.1.99:8000" in result.error_message
    assert "Connection refused" in result.error_message


def test_timeout_handled_cleanly():
    """Verify request timeout returns clean error without crashing."""
    client = TelemetryClient(backend_url="http://192.168.1.50:8000", timeout_seconds=2.5)

    with patch("urllib.request.urlopen", side_effect=TimeoutError()):
        result = client.send_telemetry({"sensor_id": "PZT-Z01", "samples": [0.1]})

    assert result.success is False
    assert result.status_code == 0
    assert "Connection timed out after 2.5s contacting http://192.168.1.50:8000" in result.error_message


def test_http_404_error_parsed():
    """Verify HTTP 404 response parsing."""
    client = TelemetryClient(backend_url="http://localhost:8000")

    err_body = json.dumps({"detail": "Zone 'Unknown' not found"}).encode("utf-8")
    http_err = urllib.error.HTTPError(
        url="http://localhost:8000/api/v1/telemetry",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=BytesIO(err_body),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        result = client.send_telemetry({"sensor_id": "PZT-Z01", "zone_name": "Unknown", "samples": [0.1]})

    assert result.success is False
    assert result.status_code == 404
    assert "Zone 'Unknown' not found" in result.error_message


def test_http_400_error_parsed():
    """Verify HTTP 400 inconsistent sensor error parsing."""
    client = TelemetryClient(backend_url="http://localhost:8000")

    err_body = json.dumps({"detail": "Sensor 'PZT-Z01' is inconsistent with target zone"}).encode("utf-8")
    http_err = urllib.error.HTTPError(
        url="http://localhost:8000/api/v1/telemetry",
        code=400,
        msg="Bad Request",
        hdrs={},
        fp=BytesIO(err_body),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        result = client.send_telemetry({"sensor_id": "PZT-Z01", "zone_name": "Zone 2 - Substructure Pier B", "samples": [0.1]})

    assert result.success is False
    assert result.status_code == 400
    assert "is inconsistent with target zone" in result.error_message
