"""
ai/validators.py
=================
Input validation for translation requests, kept separate from the
translation service itself so validation rules can be unit-tested and
reused (e.g. by the batch/file translation modules in ALT-005) without
pulling in model-loading code.
"""

from __future__ import annotations

import re

from config import settings
from ai.language_registry import is_supported
from utils.exceptions import ValidationError, UnsupportedLanguageError

_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;")


class TranslationValidator:
    """Validates raw translation requests before they reach the model."""

    def validate_text(self, text: str) -> str:
        """Validate and normalize input text. Returns the cleaned text.
        Raises ValidationError on any rule violation."""
        if text is None:
            raise ValidationError("Text is None.", user_message="Please enter some text to translate.")

        cleaned = text.strip()

        if not cleaned:
            raise ValidationError("Empty text.", user_message="Please enter some text to translate.")

        if len(cleaned) > settings.max_translation_chars:
            raise ValidationError(
                f"Text too long: {len(cleaned)} chars (limit {settings.max_translation_chars}).",
                user_message=(
                    f"Text is too long ({len(cleaned)} characters). "
                    f"Please shorten it to {settings.max_translation_chars} characters or fewer."
                ),
            )

        # Collapse excessive whitespace (3+ consecutive blank lines/spaces)
        # without touching intentional single line breaks or paragraphing.
        cleaned = re.sub(r"[ \t]{3,}", "  ", cleaned)
        cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)

        return cleaned

    def validate_language_pair(self, source_code: str, target_code: str) -> None:
        """Raise UnsupportedLanguageError if either language isn't in the
        registry, or if source and target are identical."""
        if source_code != "auto" and not is_supported(source_code):
            raise UnsupportedLanguageError(
                f"Unsupported source language: {source_code}",
                user_message="The selected source language isn't supported.",
            )
        if not is_supported(target_code):
            raise UnsupportedLanguageError(
                f"Unsupported target language: {target_code}",
                user_message="The selected target language isn't supported.",
            )
        if source_code == target_code:
            raise ValidationError(
                "Source and target languages are identical.",
                user_message="Please choose two different languages.",
            )

    def is_emoji_only(self, text: str) -> bool:
        """Return True if the text contains no letters or digits at all
        (i.e. it's purely emoji/punctuation/whitespace)."""
        return not any(ch.isalnum() for ch in text)
