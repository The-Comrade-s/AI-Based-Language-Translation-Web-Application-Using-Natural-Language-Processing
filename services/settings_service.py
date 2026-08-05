"""
services/settings_service.py
=============================
Reads and updates a user's preferences (UserSettings row created at
registration). Also handles data export/deletion requests, which are
personalization/privacy features rather than translation ones so they
live here instead of in HistoryService.
"""

from __future__ import annotations

import json

from sqlalchemy import select

from database.base import get_session
from models.user import User, UserSettings
from models.translation import TranslationHistory
from utils.exceptions import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

_VALID_THEMES = ("light", "dark", "system")


class SettingsService:
    """Manages per-user settings and personal-data export/deletion."""

    def get_settings(self, user_id: int) -> dict:
        with get_session() as session:
            settings_row = session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            ).scalar_one_or_none()

            if settings_row is None:
                # Defensive fallback — every user should get a UserSettings
                # row at registration, but don't crash the settings page
                # if one is somehow missing.
                settings_row = UserSettings(user_id=user_id)
                session.add(settings_row)
                session.flush()

            return self._to_dict(settings_row)

    def update_settings(
        self,
        user_id: int,
        *,
        preferred_source_language: str | None = None,
        preferred_target_language: str | None = None,
        theme: str | None = None,
        notifications_enabled: bool | None = None,
        accessibility_options: dict | None = None,
    ) -> dict:
        if theme is not None and theme not in _VALID_THEMES:
            raise ValidationError(f"Invalid theme: {theme}", user_message="Invalid theme selection.")

        with get_session() as session:
            settings_row = session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            ).scalar_one_or_none()

            if settings_row is None:
                raise ValidationError(f"No settings row for user {user_id}", user_message="Settings not found.")

            if preferred_source_language is not None:
                settings_row.preferred_source_language = preferred_source_language
            if preferred_target_language is not None:
                settings_row.preferred_target_language = preferred_target_language
            if theme is not None:
                settings_row.theme = theme
            if notifications_enabled is not None:
                settings_row.notifications_enabled = notifications_enabled
            if accessibility_options is not None:
                settings_row.accessibility_options = json.dumps(accessibility_options)

            session.flush()
            result = self._to_dict(settings_row)

        logger.info("Settings updated for user_id=%s", user_id)
        return result

    def export_user_data(self, user_id: int) -> dict:
        """Return a JSON-serializable snapshot of everything ALT stores
        about this user, for the data-export/portability feature."""
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValidationError(f"User {user_id} not found", user_message="Account not found.")

            settings_row = session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            ).scalar_one_or_none()

            history = session.execute(
                select(TranslationHistory).where(TranslationHistory.user_id == user_id)
            ).scalars().all()

            return {
                "profile": {
                    "full_name": user.full_name,
                    "email": user.email,
                    "username": user.username,
                    "created_at": str(user.created_at),
                },
                "settings": self._to_dict(settings_row) if settings_row else None,
                "translation_history": [
                    {
                        "source_language": h.source_language,
                        "target_language": h.target_language,
                        "source_text": h.source_text,
                        "translated_text": h.translated_text,
                        "created_at": str(h.created_at),
                    }
                    for h in history
                ],
            }

    @staticmethod
    def _to_dict(settings_row: UserSettings) -> dict:
        return {
            "preferred_source_language": settings_row.preferred_source_language,
            "preferred_target_language": settings_row.preferred_target_language,
            "theme": settings_row.theme,
            "notifications_enabled": settings_row.notifications_enabled,
            "accessibility_options": (
                json.loads(settings_row.accessibility_options) if settings_row.accessibility_options else {}
            ),
        }
