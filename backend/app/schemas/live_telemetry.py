"""Pydantic schemas and enums for the live telemetry processing SSE stream."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class LiveEventType(str, Enum):
    """Event types emitted during telemetry ingestion and pipeline execution."""
    PROCESSING_STARTED = "processing_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_ERROR = "processing_error"
    HEARTBEAT = "heartbeat"


class ProcessingStage(str, Enum):
    """The 9 sequential processing stages of the Aegis3D intelligence engine."""
    INGESTION = "INGESTION"
    CONDITIONING = "CONDITIONING"
    EVENT_DETECTION = "EVENT_DETECTION"
    FEATURE_EXTRACTION = "FEATURE_EXTRACTION"
    BASELINE_REFERENCE = "BASELINE_REFERENCE"
    ANOMALY_EVALUATION = "ANOMALY_EVALUATION"
    PERSISTENCE = "PERSISTENCE"
    CROSS_SENSOR_CORRELATION = "CROSS_SENSOR_CORRELATION"
    HEALTH_AND_ALERT = "HEALTH_AND_ALERT"


STAGE_ORDER = [
    ProcessingStage.INGESTION,
    ProcessingStage.CONDITIONING,
    ProcessingStage.EVENT_DETECTION,
    ProcessingStage.FEATURE_EXTRACTION,
    ProcessingStage.BASELINE_REFERENCE,
    ProcessingStage.ANOMALY_EVALUATION,
    ProcessingStage.PERSISTENCE,
    ProcessingStage.CROSS_SENSOR_CORRELATION,
    ProcessingStage.HEALTH_AND_ALERT,
]


def stage_to_index(stage: ProcessingStage) -> int:
    """Return the 1-based index (1-9) for a processing stage."""
    try:
        return STAGE_ORDER.index(stage) + 1
    except ValueError:
        return 0


class LiveProcessingEvent(BaseModel):
    """Strongly typed lightweight event payload emitted to SSE subscribers."""

    type: LiveEventType = Field(..., description="Classification of the live event")
    trace_id: Optional[str] = Field(None, description="Authoritative or preliminary processing trace identifier")
    event_id: Optional[int] = Field(None, description="Database event ID if detected and persisted")
    sensor_id: Optional[str] = Field(None, description="Sensor identifier (e.g. PZT-Z01)")
    zone_id: Optional[int] = Field(None, description="Logical monitoring zone database ID")
    zone_name: Optional[str] = Field(None, description="Logical monitoring zone name")
    stage: Optional[ProcessingStage] = Field(None, description="Active processing stage if applicable")
    stage_index: Optional[int] = Field(None, description="1-based stage index (1 to 9)")
    status: str = Field("started", description="Status string: started, completed, error, ok")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event creation timestamp (UTC)",
    )
    sequence: Optional[int] = Field(None, description="Telemetry sequence packet number if provided")
    duration_ms: Optional[float] = Field(None, description="Stage or processing execution duration in milliseconds")
    summary: Optional[str] = Field(None, description="Concise one-line evidence summary for UI visualization")
    error_message: Optional[str] = Field(None, description="Error message if type is processing_error")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional lightweight stage metadata")

    def to_sse_data(self) -> str:
        """Format as an SSE-compliant data payload string."""
        return f"data: {self.model_dump_json()}\n\n"
