from fastapi import APIRouter

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router

api_router = APIRouter()

# Unversioned health endpoints (/health, /health/db)
api_router.include_router(health_router)

# Versioned API v1 routes (/api/v1/events, etc.)
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(events_router, prefix="/events", tags=["events"])

api_router.include_router(v1_router)

__all__ = ["api_router"]
