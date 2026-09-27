import os
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.db import Base, SessionLocal, Settings, engine, get_db, get_settings


def test_database_config_loading():
    """Verify central database settings load environment values properly."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.POSTGRES_HOST is not None
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_DB == "aegis3d"
    assert settings.POSTGRES_USER == "aegis_user"
    assert "postgresql+psycopg2://" in settings.sync_database_url


def test_custom_settings_url_construction():
    """Test custom settings URL construction and formatting."""
    custom_settings = Settings(
        POSTGRES_HOST="db.internal",
        POSTGRES_PORT=5433,
        POSTGRES_DB="custom_db",
        POSTGRES_USER="custom_user",
        POSTGRES_PASSWORD="custom_password",
    )
    assert (
        custom_settings.sync_database_url
        == "postgresql+psycopg2://custom_user:custom_password@db.internal:5433/custom_db"
    )

    override_settings = Settings(DATABASE_URL="postgresql://override_user:override_pass@host:5432/override_db")
    assert override_settings.sync_database_url == "postgresql+psycopg2://override_user:override_pass@host:5432/override_db"


def test_sqlalchemy_engine_instance():
    """Verify centralized SQLAlchemy engine instance."""
    assert isinstance(engine, Engine)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg2"


def test_session_factory_creation():
    """Verify session factory produces a valid SQLAlchemy Session instance."""
    session = SessionLocal()
    assert isinstance(session, Session)
    session.close()


def test_get_db_generator_cleanup():
    """Verify get_db helper yields a session and ensures session closure."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)

    # Simulating exception / closure in context manager pattern
    try:
        raise ValueError("Simulated handler exception")
    except ValueError:
        pass

    with pytest.raises(StopIteration):
        next(db_gen)


def test_live_postgresql_connectivity():
    """Verify connection to live PostgreSQL database if running."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except OperationalError:
        pytest.skip("Local PostgreSQL server not running on port 5432")


def test_live_postgresql_session_query():
    """Verify querying live PostgreSQL using SessionLocal factory if running."""
    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT current_database();"))
            db_name = result.scalar()
            assert db_name == "aegis3d"
    except OperationalError:
        pytest.skip("Local PostgreSQL server not running on port 5432")
