import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.live_telemetry import LiveEventType, LiveProcessingEvent
from app.schemas.processing_trace import ProcessingTraceResponse
from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryLatestResponse,
)
from app.services.live_bus import get_live_event_bus
from app.services.telemetry_service import (
    InconsistentSensorZoneError,
    SessionNotFoundError,
    TelemetryService,
    ZoneNotFoundError,
)

router = APIRouter()


@router.get(
    "/live",
    summary="Subscribe to Live Telemetry Processing Event Stream (SSE)",
    description="Server-Sent Events endpoint streaming pipeline stage transitions and trace completion events.",
)
async def live_telemetry_stream(
    request: Request,
    max_events: Optional[int] = Query(None, description="Optional event count limit for diagnostics/testing"),
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) endpoint providing real-time telemetry processing stage events.

    Subscribers receive:
    - HEARTBEAT: periodic connection liveness events
    - PROCESSING_STARTED: telemetry packet accepted by backend pipeline
    - STAGE_STARTED: a specific processing stage (1 to 9) begins execution
    - STAGE_COMPLETED: a specific processing stage finishes execution with summary
    - PROCESSING_COMPLETED: pipeline completes; contains authoritative trace_id for trace handoff
    - PROCESSING_ERROR: pipeline failure or error event
    """
    bus = get_live_event_bus()
    try:
        bus.set_loop(asyncio.get_running_loop())
    except RuntimeError:
        pass
    queue = bus.subscribe()

    async def event_generator() -> AsyncGenerator[str, None]:
        emitted_count = 0
        try:
            # Initial connection confirmation
            initial_event = LiveProcessingEvent(
                type=LiveEventType.HEARTBEAT,
                status="connected",
                timestamp=datetime.now(timezone.utc),
                summary="Aegis3D Live Telemetry Stream Connected",
            )
            yield initial_event.to_sse_data()
            emitted_count += 1
            if max_events is not None and emitted_count >= max_events:
                return

            heartbeat_interval = 15.0
            last_heartbeat = asyncio.get_running_loop().time()

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event.to_sse_data()
                    emitted_count += 1
                    if max_events is not None and emitted_count >= max_events:
                        return
                    last_heartbeat = asyncio.get_running_loop().time()
                except asyncio.TimeoutError:
                    now = asyncio.get_running_loop().time()
                    if now - last_heartbeat >= heartbeat_interval:
                        hb = LiveProcessingEvent(
                            type=LiveEventType.HEARTBEAT,
                            status="ok",
                            timestamp=datetime.now(timezone.utc),
                            summary="ping",
                        )
                        yield hb.to_sse_data()
                        emitted_count += 1
                        if max_events is not None and emitted_count >= max_events:
                            return
                        last_heartbeat = now
        except asyncio.CancelledError:
            pass
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
    - A Sensor ID (e.g. 'PZT-Z01')
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
        description="Optional sensor identifier filter (e.g. 'PZT-Z01'). If omitted, returns latest packet from most recent sensor.",
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
