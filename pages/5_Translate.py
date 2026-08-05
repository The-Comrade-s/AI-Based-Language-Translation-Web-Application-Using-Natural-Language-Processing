"""
pages/5_Translate.py
=====================
The core translation workspace. Full history/favorites/export UI is
built out in ALT-004 — this page covers the primary translate action.
"""

from __future__ import annotations

import streamlit as st

from ai.language_registry import language_choices
from auth.session import require_login, get_current_user
from services.translation_service import TranslationService
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Translate — ALT", page_icon="🌐", layout="wide")


@st.cache_resource
def _get_service() -> TranslationService:
    # Cached as a Streamlit resource so the (eventually model-holding)
    # service isn't rebuilt on every rerun.
    return TranslationService()


@require_login
def render() -> None:
    user = get_current_user()
    st.title("🌐 Translate")

    choices = language_choices()
    codes = ["auto"] + [c for c, _ in choices]
    labels = {"auto": "Auto-detect"} | {c: label for c, label in choices}

    col_src, col_swap, col_tgt = st.columns([5, 1, 5])
    with col_src:
        source_code = st.selectbox(
            "Source language", codes, format_func=lambda c: labels[c], key="source_lang"
        )
    with col_swap:
        st.write("")
        st.write("")
        swap_clicked = st.button("⇄", help="Swap languages")
    with col_tgt:
        target_default_codes = [c for c in codes if c != "auto"]
        target_code = st.selectbox(
            "Target language", target_default_codes, format_func=lambda c: labels[c], key="target_lang"
        )

    if swap_clicked and source_code != "auto":
        st.session_state.source_lang, st.session_state.target_lang = target_code, source_code
        st.rerun()

    col_in, col_out = st.columns(2)
    with col_in:
        source_text = st.text_area("Enter text", height=220, placeholder="Type or paste text to translate...")
        if source_text:
            st.caption(f"{len(source_text)} characters · {len(source_text.split())} words")
        translate_clicked = st.button("Translate", type="primary", use_container_width=True)

    with col_out:
        output_placeholder = st.empty()
        stats_placeholder = st.empty()

    if translate_clicked:
        if not source_text or not source_text.strip():
            st.warning("Please enter some text to translate.")
            return

        service = _get_service()
        with st.spinner("Translating..."):
            try:
                result = service.translate(
                    text=source_text,
                    source_code=source_code,
                    target_code=target_code,
                    user_id=user["id"],
                )
            except ALTError as exc:
                st.error(exc.user_message)
                logger.warning("Translation request failed: %s", exc.message)
                return
            except Exception:
                logger.exception("Unexpected error during translation")
                st.error("Something went wrong. Please try again.")
                return

        with col_out:
            st.text_area("Translation", value=result.translated_text, height=220, key="output_text")
            st.caption(
                f"{result.word_count} words · {result.character_count} characters · "
                f"{result.duration_seconds:.2f}s · model: {result.model_used}"
            )
            st.download_button(
                "Download translation",
                data=result.translated_text,
                file_name="translation.txt",
                mime="text/plain",
            )


render()
