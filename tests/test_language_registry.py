"""tests/test_language_registry.py — registry integrity checks."""

from __future__ import annotations

from ai.language_registry import (
    all_languages, get_language, is_supported, to_nllb_code,
    MANDATORY_LANGUAGE_CODES, language_choices,
)


def test_registry_has_50_plus_languages():
    assert len(all_languages()) >= 50


def test_mandatory_nigerian_languages_present():
    for code in MANDATORY_LANGUAGE_CODES:
        lang = get_language(code)
        assert lang is not None
        assert lang.nllb_code.endswith("_Latn")


def test_get_language_unknown_code_returns_none():
    assert get_language("not-a-real-code") is None


def test_is_supported():
    assert is_supported("en") is True
    assert is_supported("yo") is True
    assert is_supported("xx-unknown") is False


def test_to_nllb_code():
    assert to_nllb_code("en") == "eng_Latn"
    assert to_nllb_code("yo") == "yor_Latn"
    assert to_nllb_code("unknown") is None


def test_language_choices_sorted_and_unique():
    choices = language_choices()
    codes = [c for c, _ in choices]
    assert len(codes) == len(set(codes)), "duplicate language codes in choices"
    labels = [label for _, label in choices]
    assert labels == sorted(labels)
