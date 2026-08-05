"""tests/test_translation_service.py — validation, detection, fallback."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from auth.service import register_user
from services.translation_service import TranslationService
from ai.model_manager import get_model_manager
from utils.exceptions import ValidationError, UnsupportedLanguageError, TranslationError


@pytest.fixture
def service():
    return TranslationService()


@pytest.fixture
def user_id():
    u = register_user("Translator", "translator@example.com", "Str0ng!Pass", "Str0ng!Pass")
    return u.id


def test_empty_text_rejected(service, user_id):
    with pytest.raises(ValidationError):
        service.translate("", source_code="en", target_code="yo", user_id=user_id)


def test_unsupported_language_rejected(service, user_id):
    with pytest.raises(UnsupportedLanguageError):
        service.translate("hi", source_code="xx-unknown", target_code="yo", user_id=user_id)


def test_identical_languages_rejected(service, user_id):
    with pytest.raises(ValidationError):
        service.translate("hi", source_code="en", target_code="en", user_id=user_id)


def test_successful_translation_saves_history(service, user_id):
    with patch.object(get_model_manager(), "generate_nllb", return_value="Bawo ni"):
        result = service.translate("Hello", source_code="en", target_code="yo", user_id=user_id)

    assert result.translated_text == "Bawo ni"
    assert result.model_used == "nllb-200"

    from services.history_service import HistoryService
    history = HistoryService().list_history(user_id)
    assert len(history) == 1
    assert history[0]["translated_text"] == "Bawo ni"


def test_fallback_used_when_primary_fails(service, user_id):
    with patch.object(get_model_manager(), "generate_nllb", side_effect=TranslationError("boom")), \
         patch.object(get_model_manager(), "generate_marian", return_value="Sannu"):
        result = service.translate("Hello", source_code="en", target_code="ha", user_id=user_id)

    assert result.translated_text == "Sannu"
    assert result.model_used == "marian-mt"


def test_both_models_failing_raises(service, user_id):
    with patch.object(get_model_manager(), "generate_nllb", side_effect=TranslationError("boom")), \
         patch.object(get_model_manager(), "generate_marian", side_effect=TranslationError("also boom")):
        with pytest.raises(TranslationError):
            service.translate("Hello", source_code="en", target_code="ha", user_id=user_id)
