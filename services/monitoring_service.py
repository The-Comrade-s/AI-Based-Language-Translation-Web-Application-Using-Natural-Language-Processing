"""
services/monitoring_service.py
===============================
Lightweight system health snapshot for the admin monitoring page.
Uses psutil where available and degrades gracefully (returns None for
a metric) rather than crashing the dashboard if psutil or a particular
stat is unavailable in a given deployment environment.
"""

from __future__ import annotations

import os

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class MonitoringService:
    """Reports process/system resource usage and basic database health."""

    def get_system_health(self) -> dict:
        health: dict = {
            "cpu_percent": None,
            "memory_percent": None,
            "memory_used_mb": None,
            "disk_percent": None,
            "database_size_mb": None,
        }

        try:
            import psutil

            health["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            health["memory_percent"] = mem.percent
            health["memory_used_mb"] = round(mem.used / (1024 * 1024), 1)
            disk = psutil.disk_usage(str(settings.database_path.parent))
            health["disk_percent"] = disk.percent
        except ImportError:
            logger.warning("psutil not installed — system health metrics unavailable")
        except Exception:
            logger.exception("Failed to collect system health metrics")

        try:
            if settings.database_path.exists():
                health["database_size_mb"] = round(
                    os.path.getsize(settings.database_path) / (1024 * 1024), 2
                )
        except OSError:
            logger.exception("Failed to read database file size")

        return health

    def get_cache_stats(self) -> dict:
        """Report on-disk size of the model cache and temp directories."""
        from config import MODELS_CACHE_DIR, TEMP_DIR

        def _dir_size_mb(path) -> float:
            total = 0
            if path.exists():
                for f in path.rglob("*"):
                    if f.is_file():
                        total += f.stat().st_size
            return round(total / (1024 * 1024), 2)

        return {
            "model_cache_mb": _dir_size_mb(MODELS_CACHE_DIR),
            "temp_files_mb": _dir_size_mb(TEMP_DIR),
        }
