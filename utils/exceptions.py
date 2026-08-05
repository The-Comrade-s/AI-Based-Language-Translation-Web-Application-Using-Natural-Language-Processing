"""
utils/exceptions.py
====================
Custom exception hierarchy for ALT.

Services raise these instead of bare Exception/ValueError so that the
Streamlit UI layer can catch a specific, known exception type and show a
friendly message, while the full technical detail still goes to the logs.
"""

from __future__ import annotations


class ALTError(Exception):
    """Base class for all application-specific errors in ALT."""

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        # A safe, non-technical message that can be shown directly in the UI.
        self.user_message = user_message or "Something went wrong. Please try again."


# --- Authentication & Authorization -----------------------------------

class AuthenticationError(ALTError):
    """Raised when login credentials are invalid or a session is not valid."""


class AccountLockedError(ALTError):
    """Raised when a user account is temporarily locked due to failed logins."""


class PermissionDeniedError(ALTError):
    """Raised when a user attempts an action their role does not permit."""


class ValidationError(ALTError):
    """Raised when user-supplied input fails validation rules."""


# --- Translation ---------------------------------------------------------

class TranslationError(ALTError):
    """Raised when a translation request cannot be completed."""


class UnsupportedLanguageError(TranslationError):
    """Raised when a requested language code is not in the language registry."""


class ModelLoadError(TranslationError):
    """Raised when an AI translation model fails to load."""


# --- Files / OCR / Voice --------------------------------------------------

class FileValidationError(ALTError):
    """Raised when an uploaded file fails type, size, or safety validation."""


class OCRError(ALTError):
    """Raised when text extraction from an image fails."""


class VoiceProcessingError(ALTError):
    """Raised when speech-to-text or text-to-speech processing fails."""


class ExportError(ALTError):
    """Raised when generating an export file (PDF/DOCX/CSV/JSON) fails."""


# --- Database --------------------------------------------------------------

class DatabaseError(ALTError):
    """Raised when a database operation fails unexpectedly."""
