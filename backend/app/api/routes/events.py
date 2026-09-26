from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services.event_service import (
    EventNotFoundError,
    EventService,
    SessionNotFoundError,
    ZoneNotFoundError,
)

router = APIRouter()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
) -> EventResponse:
    """Create and persist a new generic structural observation event."""
    service = EventService(db)
    try:
        created_event = service.create_event(event_in)
        return EventResponse.from_orm_event(created_event)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> EventResponse:
    """Retrieve a structural observation event by ID."""
    service = EventService(db)
    try:
        event = service.get_event(event_id)
        return EventResponse.from_orm_event(event)
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
