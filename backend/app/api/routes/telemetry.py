from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.processing_trace import ProcessingTraceResponse
from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryLatestResponse,
)
from app.services.telemetry_service import (
    InconsistentSensorZoneError,
    SessionNotFoundError,
    TelemetryService,
    ZoneNotFoundError,
)

router = APIRouter()


@router.get(
    "/{identifier}/processing-trace",
    response_model=ProcessingTraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Telemetry Processing Trace",
)
def get_processing_trace(
    identifier: str,
    db: Session = Depends(get_db),
) -> ProcessingTraceResponse:
    """
    Retrieve the detailed signal-processing execution trace and evidence for an ingested telemetry packet or event.

    Identifier parameter supports:
    - An Event ID (e.g. '42')
    - A Sensor ID (e.g. 'PZT-Z1-01')
    - A Trace ID (e.g. 'trace-evt-42')
    - 'latest' for the most recently processed telemetry
    """
    service = TelemetryService(db)
    trace = service.get_processing_trace(identifier)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry processing trace for identifier '{identifier}' not found",
        )
    return trace



@router.get("/latest", response_model=Optional[TelemetryLatestResponse], status_code=status.HTTP_200_OK)
def get_latest_telemetry(
    sensor_id: Optional[str] = Query(
        None,
        description="Optional sensor identifier filter (e.g. 'PZT-Z1-01'). If omitted, returns latest packet from most recent sensor.",
    )
) -> Optional[TelemetryLatestResponse]:
    """
    Retrieve the latest ingested sensor telemetry record and bounded waveform samples.

    If sensor_id is provided, returns that sensor's latest cached snapshot.
    If sensor_id is omitted, returns the latest packet from whichever sensor was most recently received.
    """
    return TelemetryService.get_latest_telemetry(sensor_id=sensor_id)


@router.post("", response_model=TelemetryIngestResponse, status_code=status.HTTP_200_OK)
def ingest_telemetry(
    telemetry_in: TelemetryIngestRequest,
    db: Session = Depends(get_db),
) -> TelemetryIngestResponse:
    """
    Ingest discrete sensor telemetry samples into the backend signal-processing pipeline.

    Flow:
    - Resolves the stable zone and monitoring session.
    - Converts raw samples into a hardware-agnostic SampledSignal.
    - Executes DC removal, filtering, and event detection.
    - If events are detected, evaluates statistical anomaly z-scores, temporal persistence,
      cross-sensor correlation, updates Structural Health Indicator (SHI), and generates alerts if warranted.
    - Returns a structured processing summary.
    """
    service = TelemetryService(db)
    try:
        return service.ingest_telemetry(telemetry_in)
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except InconsistentSensorZoneError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
