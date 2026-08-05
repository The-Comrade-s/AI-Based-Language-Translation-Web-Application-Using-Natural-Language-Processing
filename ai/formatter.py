"""
ai/formatter.py
================
Computes display statistics for a translation (word/character counts,
estimated reading time) and provides a consistent result shape used by
the translation service and the Streamlit UI.
"""

from __future__ import annotations

from dataclasses import dataclass

_AVERAGE_READING_WPM = 200
_AVERAGE_SPEAKING_WPM = 130


@dataclass(frozen=True)
class TranslationResult:
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    model_used: str
    duration_seconds: float
    word_count: int
    character_count: int
    estimated_reading_seconds: int
    estimated_speaking_seconds: int


class TranslationFormatter:
    """Builds a `TranslationResult` with consistent statistics."""

    def word_count(self, text: str) -> int:
        return len(text.split())

    def character_count(self, text: str) -> int:
        return len(text)

    def estimated_reading_seconds(self, text: str) -> int:
        words = self.word_count(text)
        return max(1, round(words / _AVERAGE_READING_WPM * 60))

    def estimated_speaking_seconds(self, text: str) -> int:
        words = self.word_count(text)
        return max(1, round(words / _AVERAGE_SPEAKING_WPM * 60))

    def build_result(
        self,
        *,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        model_used: str,
        duration_seconds: float,
    ) -> TranslationResult:
        return TranslationResult(
            source_text=source_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            model_used=model_used,
            duration_seconds=round(duration_seconds, 3),
            word_count=self.word_count(translated_text),
            character_count=self.character_count(translated_text),
            estimated_reading_seconds=self.estimated_reading_seconds(translated_text),
            estimated_speaking_seconds=self.estimated_speaking_seconds(translated_text),
        )
