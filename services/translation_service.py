"""
services/translation_service.py
================================
Top-level orchestration for a translation request: validate input,
resolve/detect languages, run inference (NLLB-200 primary, MarianMT
fallback), format the result, and persist history. Streamlit pages call
only this service — they never touch ModelManager or the database
directly for translation.
"""

from __future__ import annotations

import time

from ai.formatter import TranslationFormatter, TranslationResult
from ai.language_detection import LanguageDetectionService
from ai.language_registry import get_language
from ai.model_manager import ModelManager, get_model_manager
from ai.validators import TranslationValidator
from database.base import get_session
from models.translation import TranslationHistory
from utils.exceptions import TranslationError, ModelLoadError, ValidationError
from utils.logger import get_logger
from utils.rate_limiter import translation_rate_limiter

logger = get_logger(__name__)


class TranslationService:
    """Coordinates the full translate-and-record workflow.

    Dependencies (model manager, validator, detector, formatter) are
    injected so this class can be unit-tested with fakes/mocks instead
    of real AI models.
    """

    def __init__(
        self,
        model_manager: ModelManager | None = None,
        validator: TranslationValidator | None = None,
        detector: LanguageDetectionService | None = None,
        formatter: TranslationFormatter | None = None,
    ) -> None:
        self._models = model_manager or get_model_manager()
        self._validator = validator or TranslationValidator()
        self._detector = detector or LanguageDetectionService()
        self._formatter = formatter or TranslationFormatter()

    def translate(
        self,
        text: str,
        source_code: str,
        target_code: str,
        user_id: int | None = None,
        save_history: bool = True,
    ) -> TranslationResult:
        """Translate `text` from `source_code` to `target_code`.

        `source_code` may be the literal string "auto" to trigger
        automatic language detection. Raises ValidationError,
        UnsupportedLanguageError, ModelLoadError, or TranslationError
        on failure — callers (Streamlit pages) should catch ALTError
        and show `.user_message`.
        """
        cleaned_text = self._validator.validate_text(text)

        rate_key = str(user_id) if user_id is not None else "anonymous"
        if not translation_rate_limiter.is_allowed(rate_key):
            raise ValidationError(
                f"Rate limit exceeded for key={rate_key}",
                user_message="You're translating too quickly. Please wait a moment and try again.",
            )

        if source_code == "auto":
            detected = self._detector.detect(cleaned_text)
            resolved_source_code = detected.code
        else:
            resolved_source_code = source_code

        self._validator.validate_language_pair(resolved_source_code, target_code)

        source_lang = get_language(resolved_source_code)
        target_lang = get_language(target_code)
        assert source_lang is not None and target_lang is not None  # validated above

        start = time.perf_counter()
        model_used = "nllb-200"

        try:
            translated_text = self._models.generate_nllb(
                cleaned_text, source_lang.nllb_code, target_lang.nllb_code
            )
        except (ModelLoadError, TranslationError) as primary_exc:
            logger.warning(
                "Primary model failed (%s -> %s), attempting fallback: %s",
                source_lang.code, target_lang.code, primary_exc,
            )
            try:
                translated_text = self._models.generate_marian(
                    cleaned_text, source_lang.code, target_lang.code
                )
                model_used = "marian-mt"
            except (ModelLoadError, TranslationError) as fallback_exc:
                logger.error(
                    "Fallback model also failed (%s -> %s): %s",
                    source_lang.code, target_lang.code, fallback_exc,
                )
                raise TranslationError(
                    f"Both primary and fallback translation failed: {fallback_exc}",
                    user_message="Translation is currently unavailable for this language pair. Please try again later.",
                ) from fallback_exc

        duration = time.perf_counter() - start

        result = self._formatter.build_result(
            source_text=cleaned_text,
            translated_text=translated_text,
            source_language=source_lang.code,
            target_language=target_lang.code,
            model_used=model_used,
            duration_seconds=duration,
        )

        if save_history and user_id is not None:
            self._save_history(user_id, result)

        logger.info(
            "Translation completed: %s->%s in %.3fs via %s",
            source_lang.code, target_lang.code, duration, model_used,
        )
        return result

    def _save_history(self, user_id: int, result: TranslationResult) -> None:
        try:
            with get_session() as session:
                session.add(
                    TranslationHistory(
                        user_id=user_id,
                        source_language=result.source_language,
                        target_language=result.target_language,
                        source_text=result.source_text,
                        translated_text=result.translated_text,
                        model_used=result.model_used,
                        duration_seconds=result.duration_seconds,
                        word_count=result.word_count,
                        character_count=result.character_count,
                    )
                )
        except Exception:
            # History persistence failing should never mask a successful
            # translation from the user — log it and move on.
            logger.exception("Failed to save translation history for user_id=%s", user_id)
