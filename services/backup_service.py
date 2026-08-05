"""
services/backup_service.py
===========================
Full-database backup and restore. SQLite makes this straightforward: a
backup is a byte-for-byte copy of the database file taken through
SQLite's own backup API (safe to run even while the app is live, unlike
a plain file copy which could catch a write mid-transaction).
"""

from __future__ import annotations

import datetime as dt
import shutil
import sqlite3
from pathlib import Path

from config import settings
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

_BACKUP_DIR = settings.database_path.parent / "backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class BackupError(ALTError):
    """Raised when a backup or restore operation fails."""


class BackupService:
    """Creates and restores full-database backups for SQLite."""

    def create_backup(self, label: str | None = None) -> Path:
        """Create a consistent backup of the live database using
        SQLite's backup API, and return the backup file path."""
        if not settings.database_url.startswith("sqlite"):
            raise BackupError(
                "Backup is only implemented for the SQLite backend.",
                user_message="Backups are only supported for the default SQLite database.",
            )

        timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        backup_path = _BACKUP_DIR / f"alt_backup_{timestamp}{suffix}.db"

        try:
            source_conn = sqlite3.connect(str(settings.database_path))
            dest_conn = sqlite3.connect(str(backup_path))
            with dest_conn:
                source_conn.backup(dest_conn)
            source_conn.close()
            dest_conn.close()
        except sqlite3.Error as exc:
            raise BackupError(f"Backup failed: {exc}", user_message="Could not create a backup.") from exc

        logger.info("Database backup created: %s", backup_path)
        return backup_path

    def list_backups(self) -> list[dict]:
        backups = []
        for f in sorted(_BACKUP_DIR.glob("alt_backup_*.db"), reverse=True):
            stat = f.stat()
            backups.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": dt.datetime.fromtimestamp(stat.st_mtime),
                }
            )
        return backups

    def restore_backup(self, backup_filename: str) -> None:
        """Restore the live database from a previously created backup.
        The current database is itself backed up first (as a safety net)
        before being overwritten."""
        backup_path = _BACKUP_DIR / backup_filename
        if not backup_path.exists() or backup_path.parent != _BACKUP_DIR:
            raise BackupError(
                f"Backup file not found: {backup_filename}",
                user_message="That backup file could not be found.",
            )

        # Safety net: snapshot the current state before overwriting it.
        self.create_backup(label="pre_restore")

        try:
            shutil.copy2(backup_path, settings.database_path)
        except OSError as exc:
            raise BackupError(f"Restore failed: {exc}", user_message="Could not restore this backup.") from exc

        logger.warning("Database restored from backup: %s", backup_filename)

    def verify_backup_integrity(self, backup_filename: str) -> bool:
        """Run SQLite's built-in integrity check against a backup file
        without touching the live database."""
        backup_path = _BACKUP_DIR / backup_filename
        if not backup_path.exists():
            return False

        try:
            conn = sqlite3.connect(str(backup_path))
            result = conn.execute("PRAGMA integrity_check;").fetchone()
            conn.close()
            return result is not None and result[0] == "ok"
        except sqlite3.Error:
            logger.exception("Integrity check failed for backup: %s", backup_filename)
            return False
