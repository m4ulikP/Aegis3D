"""API route for discrete sensor telemetry ingestion and signal processing."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse
from app.services.telemetry_service import (
    InconsistentSensorZoneError,
    SessionNotFoundError,
    TelemetryService,
    ZoneNotFoundError,
)

router = APIRouter()


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
