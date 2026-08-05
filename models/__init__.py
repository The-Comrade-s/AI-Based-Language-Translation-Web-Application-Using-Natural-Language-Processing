"""
models/__init__.py
===================
Importing this package registers every ORM model on `database.base.Base`,
so `Base.metadata.create_all()` creates all tables. Add new model modules
here as they're introduced in later phases.
"""

from models.user import User, UserSettings, ActivityLog, PasswordResetToken  # noqa: F401
from models.translation import TranslationHistory  # noqa: F401
from models.media import VoiceHistory, DocumentHistory, OCRHistory  # noqa: F401

__all__ = [
    "User",
    "UserSettings",
    "ActivityLog",
    "PasswordResetToken",
    "TranslationHistory",
    "VoiceHistory",
    "DocumentHistory",
    "OCRHistory",
]
