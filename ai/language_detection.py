"""
ai/language_detection.py
=========================
Automatic source-language detection. Wraps the `langdetect` library and
maps its ISO 639-1 output onto ALT's language registry, since langdetect
has no concept of Yoruba/Hausa/Igbo and other low-resource languages we
support.
"""

from __future__ import annotations

from ai.language_registry import get_language, Language
from utils.exceptions import UnsupportedLanguageError
from utils.logger import get_logger

logger = get_logger(__name__)


class LanguageDetectionService:
    """Detects the most likely language of a piece of text."""

    def detect(self, text: str) -> Language:
        """Detect the language of `text` and return the matching registry
        entry. Raises UnsupportedLanguageError if detection succeeds but
        the detected language isn't one ALT supports, or if detection
        fails outright (e.g. text too short/ambiguous)."""
        cleaned = text.strip()
        if not cleaned:
            raise UnsupportedLanguageError(
                "Cannot detect language of empty text.",
                user_message="Please enter some text to translate.",
            )

        try:
            # Imported lazily so the rest of the app doesn't pay the
            # import cost (and langdetect's data-file load) unless
            # auto-detection is actually used.
            from langdetect import detect, LangDetectException

            iso_code = detect(cleaned)
        except LangDetectException:
            raise UnsupportedLanguageError(
                "Language detection failed — text may be too short or ambiguous.",
                user_message="Couldn't detect the language automatically. Please select it manually.",
            )

        language = get_language(iso_code)
        if language is None:
            # langdetect uses some codes ALT's registry doesn't carry
            # (e.g. regional variants). Try a couple of common aliases
            # before giving up.
            language = get_language(iso_code.split("-")[0])

        if language is None:
            raise UnsupportedLanguageError(
                f"Detected language '{iso_code}' is not supported.",
                user_message="The detected language isn't supported yet. Please select it manually.",
            )

        logger.info("Detected language: %s -> %s", iso_code, language.code)
        return language
