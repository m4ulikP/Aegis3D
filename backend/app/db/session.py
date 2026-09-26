from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.config import get_settings

settings = get_settings()

# Reusable centralized SQLAlchemy 2.x engine
engine = create_engine(
    settings.sync_database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=settings.DB_ECHO,
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
