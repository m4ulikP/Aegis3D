"""HTTP Client for dispatching sensor telemetry to the Aegis3D FastAPI backend."""

from dataclasses import dataclass
import json
from typing import Any, Dict, Optional
import urllib.error
import urllib.request


@dataclass
class TelemetryClientResult:
    """Structured result returned by the telemetry HTTP client."""

    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    raw_body: Optional[str] = None

    @property
    def backend_status(self) -> Optional[str]:
        """Backend processing status from API response (e.g. PROCESSED_ANOMALY_DETECTED)."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("status")
        return None

    @property
    def events_detected(self) -> int:
        """Count of structural activity events detected by backend signal processing."""
        if self.data and isinstance(self.data, dict):
            return int(self.data.get("events_detected", 0))
        return 0

    @property
    def health_score(self) -> Optional[float]:
        """Recalculated zone Structural Health Indicator (SHI 0-100) from backend."""
        if self.data and isinstance(self.data, dict):
            val = self.data.get("health_score")
            return float(val) if val is not None else None
        return None

    @property
    def health_status(self) -> Optional[str]:
        """HealthStatus classification from backend (NORMAL, MONITOR, INSPECTION_ADVISED, etc.)."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("health_status")
        return None

    @property
    def alert_generated(self) -> bool:
        """True if the backend evaluated that structural degradation warrants an Alert."""
        if self.data and isinstance(self.data, dict):
            return bool(self.data.get("alert_generated", False))
        return False

    @property
    def alert_severity(self) -> Optional[str]:
        """Severity of generated alert if applicable."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("alert_severity")
        return None

    @property
    def temporal_persistence_confirmed(self) -> Optional[bool]:
        """True if multi-event temporal persistence criteria was satisfied on backend."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("temporal_persistence_confirmed")
        return None

    @property
    def cross_sensor_correlation_confirmed(self) -> Optional[bool]:
        """True if 2-PZT cross-sensor correlation criteria was satisfied on backend."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("cross_sensor_correlation_confirmed")
        return None

    @property
    def message(self) -> Optional[str]:
        """Descriptive response message from backend processing pipeline."""
        if self.data and isinstance(self.data, dict):
            return self.data.get("message")
        return None


class TelemetryClient:
    """Lightweight HTTP client for transmitting telemetry payloads to the backend."""

    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        endpoint: str = "/api/v1/telemetry",
        timeout_seconds: float = 5.0,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        self.timeout_seconds = timeout_seconds
        self.full_url = f"{self.backend_url}{self.endpoint}"

    def send_telemetry(self, payload: Dict[str, Any]) -> TelemetryClientResult:
        """
        POST a telemetry dictionary payload to the backend ingestion endpoint.

        Handles:
        - Connection errors / unreachable hosts cleanly without unreadable crash tracebacks
        - Timeouts
        - HTTP 4xx client errors (validation, unknown zone, inconsistent sensor)
        - HTTP 5xx server errors
        - JSON response parsing
        """
        encoded_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=self.full_url,
            data=encoded_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                status_code = response.status
                body_bytes = response.read()
                raw_body = body_bytes.decode("utf-8", errors="replace")
                try:
                    parsed_json = json.loads(raw_body)
                except Exception:
                    parsed_json = None

                return TelemetryClientResult(
                    success=(200 <= status_code < 300),
                    status_code=status_code,
                    data=parsed_json,
                    raw_body=raw_body,
                )

        except urllib.error.HTTPError as exc:
            # Server responded with 4xx or 5xx status code
            try:
                body_bytes = exc.read()
                raw_body = body_bytes.decode("utf-8", errors="replace")
                parsed_json = json.loads(raw_body)
            except Exception:
                raw_body = ""
                parsed_json = None

            detail = ""
            if parsed_json and isinstance(parsed_json, dict):
                detail = parsed_json.get("detail", str(parsed_json))

            err_msg = f"HTTP {exc.code} {exc.reason}"
            if detail:
                err_msg += f": {detail}"

            return TelemetryClientResult(
                success=False,
                status_code=exc.code,
                data=parsed_json,
                error_message=err_msg,
                raw_body=raw_body,
            )

        except urllib.error.URLError as exc:
            # Connection refused, DNS failure, host unreachable
            reason_str = str(exc.reason)
            err_msg = f"Backend unreachable at {self.backend_url} ({reason_str})"
            return TelemetryClientResult(
                success=False,
                status_code=0,
                error_message=err_msg,
            )

        except TimeoutError:
            err_msg = f"Connection timed out after {self.timeout_seconds}s contacting {self.backend_url}"
            return TelemetryClientResult(
                success=False,
                status_code=0,
                error_message=err_msg,
            )

        except Exception as exc:
            err_msg = f"Unexpected communication error: {str(exc)}"
            return TelemetryClientResult(
                success=False,
                status_code=0,
                error_message=err_msg,
            )


def main() -> None:
    """Phase 1 Single Request Execution Slice."""
    import os
    import sys

    # Discover paths
    _dir = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_dir)
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)

    try:
        from simulator.config import SimulatorConfig
        from simulator.sensors.virtual_pzt import VirtualPZTSensor
    except ImportError:
        from config import SimulatorConfig
        from sensors.virtual_pzt import VirtualPZTSensor

    print("=" * 60)
    print("Aegis3D Virtual PZT Sensor Simulator — Phase 1 Vertical Slice")
    print("=" * 60)

    # 1. Load backend URL from environment
    config = SimulatorConfig.from_env()
    client = TelemetryClient(
        backend_url=config.backend_url,
        endpoint=config.telemetry_endpoint,
        timeout_seconds=config.timeout_seconds,
    )

    # 2. Construct valid TelemetryIngestRequest & 3. Generate healthy waveform
    sensor = VirtualPZTSensor(sensor_id="PZT-Z1-01")
    payload = sensor.generate_payload(mode="healthy", sample_count=1000, seed=42)

    print(f"\n[REQUEST SETUP]")
    print(f"  Target URL    : {client.full_url}")
    print(f"  Sensor ID     : {payload['sensor_id']}")
    print(f"  Zone Name     : {payload['zone_name']}")
    print(f"  Timestamp     : {payload['timestamp']}")
    print(f"  Sample Rate   : {payload['sample_rate_hz']} Hz")
    print(f"  Sample Count  : {len(payload['samples'])}")
    print(f"  Signal Peak   : {max(abs(x) for x in payload['samples']):.4f}")

    # 4. POST to /api/v1/telemetry
    print(f"\n[DISPATCHING TELEMETRY POST]")
    result = client.send_telemetry(payload)

    # 5. Print HTTP status
    print(f"  HTTP Status   : {result.status_code}")

    # 6. Print actual backend response in readable form
    if result.success and result.data:
        print("\n[BACKEND RESPONSE SUCCESS]")
        print(json.dumps(result.data, indent=2))
        print(f"\n  Pipeline Status : {result.backend_status}")
        print(f"  Events Detected : {result.events_detected}")
        print(f"  Health Score    : {result.health_score}")
        print(f"  Message         : {result.message}")
    elif result.success:
        print("\n[BACKEND RESPONSE SUCCESS (RAW)]")
        print(result.raw_body)
    else:
        # 7. Handle connection / HTTP errors cleanly
        print(f"\n[COMMUNICATION FAILED]")
        print(f"  Error Message   : {result.error_message}")
        if result.raw_body:
            print(f"  Raw Body        : {result.raw_body}")


if __name__ == "__main__":
    main()

