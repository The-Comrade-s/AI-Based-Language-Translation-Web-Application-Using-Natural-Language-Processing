"""tests/test_history_and_export.py"""

from __future__ import annotations

import pytest

from auth.service import register_user
from database.base import get_session
from models.translation import TranslationHistory
from services.history_service import HistoryService
from services.export_service import ExportService
from utils.exceptions import ValidationError


@pytest.fixture
def user_id():
    u = register_user("Hist", "hist@example.com", "Str0ng!Pass", "Str0ng!Pass")
    return u.id


@pytest.fixture
def seeded_history(user_id):
    with get_session() as session:
        session.add_all([
            TranslationHistory(user_id=user_id, source_language="en", target_language="yo",
                                source_text="Hello", translated_text="Bawo ni", model_used="nllb-200",
                                duration_seconds=0.5, word_count=2, character_count=7),
            TranslationHistory(user_id=user_id, source_language="en", target_language="ha",
                                source_text="Good morning", translated_text="Barka da safiya",
                                model_used="nllb-200", duration_seconds=0.6, word_count=3,
                                character_count=15, is_favorite=True),
        ])
    return user_id


def test_list_and_count(seeded_history):
    svc = HistoryService()
    records = svc.list_history(seeded_history)
    assert len(records) == 2
    assert svc.count_history(seeded_history) == 2


def test_favorites_filter(seeded_history):
    svc = HistoryService()
    favs = svc.list_history(seeded_history, favorites_only=True)
    assert len(favs) == 1
    assert favs[0]["is_favorite"] is True


def test_search(seeded_history):
    svc = HistoryService()
    results = svc.list_history(seeded_history, search="morning")
    assert len(results) == 1


def test_toggle_favorite_cross_user_blocked(seeded_history):
    svc = HistoryService()
    records = svc.list_history(seeded_history)
    with pytest.raises(ValidationError):
        svc.toggle_favorite(user_id=999999, record_id=records[0]["id"])


def test_delete_and_clear(seeded_history):
    svc = HistoryService()
    records = svc.list_history(seeded_history)
    svc.delete_record(seeded_history, records[0]["id"])
    assert svc.count_history(seeded_history) == 1

    deleted = svc.clear_history(seeded_history)
    assert deleted == 1
    assert svc.count_history(seeded_history) == 0


def test_statistics(seeded_history):
    svc = HistoryService()
    stats = svc.get_statistics(seeded_history)
    assert stats["total_translations"] == 2
    assert stats["favorite_count"] == 1


def test_exports_produce_nonempty_bytes(seeded_history):
    svc = HistoryService()
    export_svc = ExportService()
    records = svc.list_history(seeded_history)

    assert len(export_svc.to_txt(records)) > 0
    assert len(export_svc.to_csv(records)) > 0
    assert len(export_svc.to_json(records)) > 0
    assert len(export_svc.to_docx(records)) > 0
    assert len(export_svc.to_pdf(records)) > 0
