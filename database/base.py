"""
database/base.py
=================
SQLAlchemy engine, session management, and declarative base for ALT.

Every model in `models/` inherits from `Base`. All database access should
go through `get_session()` (a context manager) rather than instantiating
sessions ad hoc, so transactions are always committed or rolled back
consistently.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base class shared by every ORM model in the project."""
    pass


# SQLite requires this connect_arg when accessed from multiple threads,
# which Streamlit's execution model can trigger.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables that don't yet exist.

    Safe to call on every application startup — it is a no-op for tables
    that already exist. Actual schema changes across versions should be
    handled by an explicit migration, not by this function.
    """
    # Import models here (not at module load time) to avoid circular
    # imports, while still ensuring every model is registered on Base
    # before create_all() runs.
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", settings.database_url)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of database operations.

    Usage:
        with get_session() as session:
            session.add(obj)
            # commits automatically on successful exit, rolls back on error
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database session rolled back due to an error")
        raise
    finally:
        session.close()
