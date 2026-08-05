"""
pages/7_Document_Translation.py
================================
Upload and translate TXT/DOCX/PDF/CSV/JSON/MD documents.
"""

from __future__ import annotations

import streamlit as st

from ai.language_registry import language_choices
from auth.session import require_login, get_current_user
from config import settings
from services.document_service import DocumentTranslationService
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Document Translation — ALT", page_icon="📄")


@st.cache_resource
def _service() -> DocumentTranslationService:
    return DocumentTranslationService()


@require_login
def render() -> None:
    user = get_current_user()
    st.title("📄 Document Translation")
    st.caption(f"Supported: {', '.join(settings.allowed_document_extensions)} · max {settings.max_upload_size_mb}MB")

    choices = language_choices()
    col1, col2 = st.columns(2)
    with col1:
        source_code = st.selectbox("Source language", [c for c, _ in choices], format_func=lambda c: dict(choices)[c], key="doc_src")
    with col2:
        target_code = st.selectbox("Target language", [c for c, _ in choices], format_func=lambda c: dict(choices)[c], key="doc_tgt")

    uploaded_file = st.file_uploader("Upload a document", type=[ext.lstrip(".") for ext in settings.allowed_document_extensions])

    if uploaded_file is not None and st.button("Translate Document", type="primary"):
        service = _service()
        with st.spinner("Extracting and translating..."):
            try:
                result = service.translate_document(
                    filename=uploaded_file.name,
                    file_bytes=uploaded_file.getvalue(),
                    source_code=source_code,
                    target_code=target_code,
                    user_id=user["id"],
                )
            except ALTError as exc:
                st.error(exc.user_message)
                return
            except Exception:
                logger.exception("Unexpected error during document translation")
                st.error("Something went wrong translating this document.")
                return

        st.success(f"Translated in {result['duration_seconds']:.2f}s ({result['chunk_count']} chunk(s)).")
        col_orig, col_trans = st.columns(2)
        with col_orig:
            st.text_area("Original text", value=result["extracted_text"], height=300)
        with col_trans:
            st.text_area("Translated text", value=result["translated_text"], height=300)

        st.download_button(
            "Download translated text (.txt)",
            data=result["translated_text"],
            file_name=f"translated_{result['filename']}.txt",
            mime="text/plain",
        )


render()
