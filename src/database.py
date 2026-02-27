"""
Database engine and session factory for TTAB toolkit.

Uses SQLAlchemy 2.x with a PostgreSQL backend.
The connection URL is read from [database].url in settings.toml
or the DATABASE_URL environment variable (takes precedence).
"""

import logging

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from src.settings import get as get_setting
from src.db_models import Base

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return (and lazily create) the shared SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = get_setting("database", "url")
        if not url:
            raise RuntimeError(
                "No database URL configured. "
                "Set [database].url in settings.toml or the DATABASE_URL environment variable."
            )
        _engine = create_engine(url, pool_pre_ping=True)
        logger.debug("SQLAlchemy engine created for %s", url)
    return _engine


def get_session() -> Session:
    """Return a new database session. Caller is responsible for closing it."""
    factory = sessionmaker(bind=get_engine())
    return factory()


def init_db() -> None:
    """Create all tables if they don't already exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")
