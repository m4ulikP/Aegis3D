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
