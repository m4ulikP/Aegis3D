from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import EventSeverity, EventStatus
from app.schemas.event import EventResponse
from app.schemas.zone import (
    ZoneCorrelationResponse,
    ZoneDetailResponse,
    ZoneHealthResponse,
    ZoneResponse,
    ZoneTrendResponse,
)
from app.services.monitoring_service import MonitoringService, ZoneNotFoundError

router = APIRouter()


@router.get("", response_model=List[ZoneResponse], status_code=status.HTTP_200_OK)
def list_zones(db: Session = Depends(get_db)) -> List[ZoneResponse]:
    """Return all monitoring zones."""
    service = MonitoringService(db)
    zones = service.get_all_zones()
    return [ZoneResponse.model_validate(z) for z in zones]


@router.get("/{zone_id}", response_model=ZoneDetailResponse, status_code=status.HTTP_200_OK)
def get_zone_detail(zone_id: int, db: Session = Depends(get_db)) -> ZoneDetailResponse:
    """Return specific zone and its monitoring metadata."""
    service = MonitoringService(db)
    try:
        return service.get_zone_detail(zone_id)
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/{zone_id}/events", response_model=List[EventResponse], status_code=status.HTTP_200_OK)
def get_zone_events(
    zone_id: int,
    limit: int = Query(50, ge=1, le=500, description="Max number of events to return"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_time: Optional[datetime] = Query(None, description="End timestamp filter"),
    severity: Optional[EventSeverity] = Query(None, description="Event severity filter"),
    status_filter: Optional[EventStatus] = Query(None, alias="status", description="Event status filter"),
    db: Session = Depends(get_db),
) -> List[EventResponse]:
    """Return events associated with a zone."""
    service = MonitoringService(db)
    try:
        events = service.get_zone_events(
            zone_id=zone_id,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
            severity=severity,
            status=status_filter,
        )
        return [EventResponse.from_orm_event(evt) for evt in events]
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/{zone_id}/health", response_model=ZoneHealthResponse, status_code=status.HTTP_200_OK)
def get_zone_health(
    zone_id: int,
    reference_time: Optional[datetime] = Query(None, description="Reference end time for health evaluation"),
    window_duration_seconds: float = Query(3600.0, ge=60.0, le=86400.0, description="Analysis window in seconds"),
    db: Session = Depends(get_db),
) -> ZoneHealthResponse:
    """Return the latest Structural Health Indicator information for a zone."""
    service = MonitoringService(db)
    try:
        return service.get_zone_health(
            zone_id=zone_id,
            reference_time=reference_time,
            window_duration_seconds=window_duration_seconds,
        )
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/{zone_id}/trend", response_model=ZoneTrendResponse, status_code=status.HTTP_200_OK)
def get_zone_trend(
    zone_id: int,
    reference_time: Optional[datetime] = Query(None, description="Reference end time for trend evaluation"),
    analysis_window_seconds: float = Query(3600.0, ge=60.0, le=86400.0, description="Analysis window in seconds"),
    db: Session = Depends(get_db),
) -> ZoneTrendResponse:
    """Expose deterministic trend analysis service for a zone."""
    service = MonitoringService(db)
    try:
        return service.get_zone_trend(
            zone_id=zone_id,
            reference_time=reference_time,
            analysis_window_seconds=analysis_window_seconds,
        )
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/{zone_id}/correlation", response_model=ZoneCorrelationResponse, status_code=status.HTTP_200_OK)
def get_zone_correlation(
    zone_id: int,
    reference_time: Optional[datetime] = Query(None, description="Reference end time for correlation evaluation"),
    window_duration_seconds: float = Query(300.0, ge=10.0, le=3600.0, description="Persistence window in seconds"),
    tolerance_seconds: float = Query(0.025, ge=0.001, le=1.0, description="Cross-sensor tolerance in seconds"),
    db: Session = Depends(get_db),
) -> ZoneCorrelationResponse:
    """Expose temporal persistence and two-PZT cross-sensor correlation for a zone."""
    service = MonitoringService(db)
    try:
        return service.get_zone_correlation(
            zone_id=zone_id,
            reference_time=reference_time,
            window_duration_seconds=window_duration_seconds,
            tolerance_seconds=tolerance_seconds,
        )
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
