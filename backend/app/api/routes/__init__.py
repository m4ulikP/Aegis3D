from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router

__all__ = ["health_router", "events_router"]
