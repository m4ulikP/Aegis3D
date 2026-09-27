from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.config import get_settings

settings = get_settings()

db_url = settings.sync_database_url
engine_kwargs = {"echo": settings.DB_ECHO}
if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
    })

# Reusable centralized SQLAlchemy 2.x engine
engine = create_engine(
    db_url,
    **engine_kwargs,
)

# Reusable centralized SQLAlchemy session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency/helper.

    Yields a SQLAlchemy session and guarantees proper session cleanup/closure.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
