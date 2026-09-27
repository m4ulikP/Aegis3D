from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import AlertSeverity, AlertStatus
from app.schemas.alert import AlertResponse
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.get("", response_model=List[AlertResponse], status_code=status.HTTP_200_OK)
def list_alerts(
    zone_id: Optional[int] = Query(None, description="Optional zone ID filter"),
    status_filter: Optional[AlertStatus] = Query(None, alias="status", description="Optional alert status filter"),
    severity: Optional[AlertSeverity] = Query(None, description="Optional alert severity filter"),
    limit: int = Query(50, ge=1, le=500, description="Max number of alerts to return"),
    db: Session = Depends(get_db),
) -> List[AlertResponse]:
    """Return actionable system alerts with optional filtering."""
    service = MonitoringService(db)
    alerts = service.get_alerts(
        zone_id=zone_id,
        status=status_filter,
        severity=severity,
        limit=limit,
    )
    return [AlertResponse.model_validate(alt) for alt in alerts]
