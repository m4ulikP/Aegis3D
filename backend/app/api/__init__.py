from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.zones import router as zones_router

api_router = APIRouter()

# Unversioned health endpoints (/health, /health/db)
api_router.include_router(health_router)

# Versioned API v1 routes (/api/v1/events, /api/v1/zones, /api/v1/alerts, /api/v1/health/summary, /api/v1/telemetry)
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(events_router, prefix="/events", tags=["events"])
v1_router.include_router(zones_router, prefix="/zones", tags=["zones"])
v1_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
v1_router.include_router(monitoring_router, prefix="/health", tags=["health"])
v1_router.include_router(telemetry_router, prefix="/telemetry", tags=["telemetry"])

api_router.include_router(v1_router)

__all__ = ["api_router"]

