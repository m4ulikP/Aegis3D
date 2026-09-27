from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.health import HealthSummaryResponse
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.get("/summary", response_model=HealthSummaryResponse, status_code=status.HTTP_200_OK)
def get_health_summary(db: Session = Depends(get_db)) -> HealthSummaryResponse:
    """Return dashboard-level structural health monitoring summary."""
    service = MonitoringService(db)
    return service.get_health_summary()
