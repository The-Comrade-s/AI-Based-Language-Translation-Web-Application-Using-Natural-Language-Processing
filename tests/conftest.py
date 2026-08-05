"""
tests/conftest.py
==================
Shared pytest fixtures. Every test run gets its own throwaway SQLite
database file (never the developer's real database.db), created fresh
and torn down automatically.
"""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch, tmp_path):
    """Point the app at a fresh temp SQLite file for every test, and
    rebuild the SQLAlchemy engine/session bound to it. autouse=True means
    every test gets isolation without needing to request this fixture
    explicitly."""
    db_path = tmp_path / "test_alt.db"

    import config
    original_db_path = config.settings.database_path
    original_db_url = config.settings.database_url

    # AppConfig is a frozen dataclass (intentionally, so runtime code can't
    # accidentally mutate shared config) — tests bypass that deliberately,
    # via object.__setattr__, to point the *same* settings singleton every
    # already-imported module holds a reference to at an isolated test DB.
    object.__setattr__(config.settings, "database_path", db_path)
    object.__setattr__(config.settings, "database_url", f"sqlite:///{db_path.as_posix()}")

    # database.base built its engine/session at import time from the old
    # settings — rebuild both against the patched settings for this test.
    import database.base as db_base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    new_engine = create_engine(
        config.settings.database_url, connect_args={"check_same_thread": False}, future=True
    )
    monkeypatch.setattr(db_base, "engine", new_engine)
    monkeypatch.setattr(
        db_base, "SessionLocal", sessionmaker(bind=new_engine, autoflush=False, autocommit=False, future=True)
    )

    db_base.init_db()
    yield
    new_engine.dispose()
    object.__setattr__(config.settings, "database_path", original_db_path)
    object.__setattr__(config.settings, "database_url", original_db_url)
