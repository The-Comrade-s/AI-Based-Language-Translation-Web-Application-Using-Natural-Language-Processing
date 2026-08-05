"""
ai/language_registry.py
========================
Central registry of every language ALT supports. This is the single
source of truth for language codes, display names, and native names —
no other module should hard-code a language list.

Each entry's `nllb_code` is the FLORES-200 code Meta's NLLB-200 model
expects (e.g. "eng_Latn"). The short `code` is a simpler UI-facing key
(mostly ISO 639-1) used for dropdowns, history records, and settings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str            # short UI code, e.g. "en", "yo"
    name: str             # English display name
    native_name: str      # name in the language itself
    nllb_code: str         # FLORES-200 code used by NLLB-200
    is_available: bool = True


# --------------------------------------------------------------------------
# Registry — 50+ languages, including the mandatory Nigerian languages.
# --------------------------------------------------------------------------

_LANGUAGES: list[Language] = [
    Language("en", "English", "English", "eng_Latn"),
    Language("es", "Spanish", "Español", "spa_Latn"),
    Language("fr", "French", "Français", "fra_Latn"),
    Language("de", "German", "Deutsch", "deu_Latn"),
    Language("pt", "Portuguese", "Português", "por_Latn"),
    Language("it", "Italian", "Italiano", "ita_Latn"),
    Language("nl", "Dutch", "Nederlands", "nld_Latn"),
    Language("ru", "Russian", "Русский", "rus_Cyrl"),
    Language("uk", "Ukrainian", "Українська", "ukr_Cyrl"),
    Language("pl", "Polish", "Polski", "pol_Latn"),
    Language("tr", "Turkish", "Türkçe", "tur_Latn"),
    Language("ar", "Arabic", "العربية", "arb_Arab"),
    Language("he", "Hebrew", "עברית", "heb_Hebr"),
    Language("fa", "Persian", "فارسی", "pes_Arab"),
    Language("ur", "Urdu", "اردو", "urd_Arab"),
    Language("hi", "Hindi", "हिन्दी", "hin_Deva"),
    Language("bn", "Bengali", "বাংলা", "ben_Beng"),
    Language("pa", "Punjabi", "ਪੰਜਾਬੀ", "pan_Guru"),
    Language("gu", "Gujarati", "ગુજરાતી", "guj_Gujr"),
    Language("mr", "Marathi", "मराठी", "mar_Deva"),
    Language("ta", "Tamil", "தமிழ்", "tam_Taml"),
    Language("te", "Telugu", "తెలుగు", "tel_Telu"),
    Language("kn", "Kannada", "ಕನ್ನಡ", "kan_Knda"),
    Language("ml", "Malayalam", "മലയാളം", "mal_Mlym"),
    Language("si", "Sinhala", "සිංහල", "sin_Sinh"),
    Language("ne", "Nepali", "नेपाली", "npi_Deva"),
    Language("zh-CN", "Chinese (Simplified)", "简体中文", "zho_Hans"),
    Language("zh-TW", "Chinese (Traditional)", "繁體中文", "zho_Hant"),
    Language("ja", "Japanese", "日本語", "jpn_Jpan"),
    Language("ko", "Korean", "한국어", "kor_Hang"),
    Language("th", "Thai", "ไทย", "tha_Thai"),
    Language("vi", "Vietnamese", "Tiếng Việt", "vie_Latn"),
    Language("id", "Indonesian", "Bahasa Indonesia", "ind_Latn"),
    Language("ms", "Malay", "Bahasa Melayu", "zsm_Latn"),
    Language("fil", "Filipino", "Filipino", "fil_Latn"),
    Language("sw", "Swahili", "Kiswahili", "swh_Latn"),
    Language("am", "Amharic", "አማርኛ", "amh_Ethi"),
    Language("so", "Somali", "Soomaali", "som_Latn"),
    Language("af", "Afrikaans", "Afrikaans", "afr_Latn"),
    Language("zu", "Zulu", "isiZulu", "zul_Latn"),
    Language("xh", "Xhosa", "isiXhosa", "xho_Latn"),
    Language("cs", "Czech", "Čeština", "ces_Latn"),
    Language("sk", "Slovak", "Slovenčina", "slk_Latn"),
    Language("hu", "Hungarian", "Magyar", "hun_Latn"),
    Language("ro", "Romanian", "Română", "ron_Latn"),
    Language("el", "Greek", "Ελληνικά", "ell_Grek"),
    Language("bg", "Bulgarian", "Български", "bul_Cyrl"),
    Language("da", "Danish", "Dansk", "dan_Latn"),
    Language("sv", "Swedish", "Svenska", "swe_Latn"),
    Language("no", "Norwegian", "Norsk", "nob_Latn"),
    Language("fi", "Finnish", "Suomi", "fin_Latn"),
    # --- Mandatory Nigerian languages ---
    Language("yo", "Yoruba", "Yorùbá", "yor_Latn"),
    Language("ha", "Hausa", "Hausa", "hau_Latn"),
    Language("ig", "Igbo", "Igbo", "ibo_Latn"),
]

# Fast lookup indexes, built once at import time.
_BY_CODE: dict[str, Language] = {lang.code: lang for lang in _LANGUAGES}
_BY_NLLB_CODE: dict[str, Language] = {lang.nllb_code: lang for lang in _LANGUAGES}

MANDATORY_LANGUAGE_CODES = ("yo", "ha", "ig")


def all_languages() -> list[Language]:
    """Return every registered language, in registry order."""
    return list(_LANGUAGES)


def available_languages() -> list[Language]:
    """Return only languages currently marked available."""
    return [lang for lang in _LANGUAGES if lang.is_available]


def get_language(code: str) -> Language | None:
    """Look up a language by its short UI code (e.g. 'yo')."""
    return _BY_CODE.get(code)


def get_language_by_nllb_code(nllb_code: str) -> Language | None:
    """Look up a language by its FLORES-200/NLLB code (e.g. 'yor_Latn')."""
    return _BY_NLLB_CODE.get(nllb_code)


def is_supported(code: str) -> bool:
    lang = get_language(code)
    return lang is not None and lang.is_available


def to_nllb_code(code: str) -> str | None:
    """Convert a short UI code to the NLLB FLORES-200 code it maps to."""
    lang = get_language(code)
    return lang.nllb_code if lang else None


def language_choices() -> list[tuple[str, str]]:
    """Return (code, display_label) pairs, sorted by display name, for use
    in Streamlit selectboxes."""
    return sorted(
        ((lang.code, f"{lang.name} ({lang.native_name})") for lang in available_languages()),
        key=lambda pair: pair[1],
    )


# Sanity check at import time: every mandatory language must be present.
for _code in MANDATORY_LANGUAGE_CODES:
    assert _code in _BY_CODE, f"Mandatory language missing from registry: {_code}"
assert len(_LANGUAGES) >= 50, f"Registry must have 50+ languages, has {len(_LANGUAGES)}"
