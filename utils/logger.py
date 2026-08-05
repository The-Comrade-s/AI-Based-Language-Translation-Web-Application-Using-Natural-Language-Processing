"""
utils/logger.py
================
Centralized logging configuration for ALT.

Every module should obtain its logger via `get_logger(__name__)` rather
than configuring `logging` directly, so log format, level, and file
rotation stay consistent across the whole application.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _configure_root_logger() -> None:
    """Attach a rotating file handler and console handler to the root
    logger exactly once, regardless of how many times get_logger() is
    called across the application."""
    global _configured
    if _configured:
        return

    root_logger = logging.getLogger("alt")
    root_logger.setLevel(settings.log_level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        filename=settings.log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    root_logger.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (e.g. 'alt.auth.service') that writes to
    both the rotating log file and the console."""
    _configure_root_logger()
    return logging.getLogger(f"alt.{name}")
