import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, str]:
    """Liveness check endpoint.

    Confirms that the Aegis3D API process is alive.
    Does not perform database or external queries.
    """
    return {"status": "ok", "service": "Aegis3D API"}


@router.get("/health/db", status_code=status.HTTP_200_OK)
def health_db_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """Database readiness check endpoint.

    Verifies communication with PostgreSQL using the existing get_db persistence foundation.
    """
    try:
        result = db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            return {"status": "ok", "database": "reachable"}
        raise Exception("Database query returned unexpected result")
    except Exception as exc:
        logger.error(f"Database readiness check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "unreachable"},
        )
