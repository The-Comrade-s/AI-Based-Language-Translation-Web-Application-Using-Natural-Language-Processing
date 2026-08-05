"""
pages/8_OCR_Translation.py
===========================
Upload an image, extract text via OCR, and translate it.
"""

from __future__ import annotations

import streamlit as st

from ai.language_registry import language_choices
from auth.session import require_login, get_current_user
from config import settings
from services.ocr_service import OCRService
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="OCR Translation — ALT", page_icon="🖼️")


@st.cache_resource
def _service() -> OCRService:
    return OCRService()


@require_login
def render() -> None:
    user = get_current_user()
    st.title("🖼️ Image (OCR) Translation")
    st.caption(f"Supported: {', '.join(settings.allowed_image_extensions)} · max {settings.max_upload_size_mb}MB")

    choices = language_choices()
    col1, col2 = st.columns(2)
    with col1:
        source_code = st.selectbox("Source language", [c for c, _ in choices], format_func=lambda c: dict(choices)[c], key="ocr_src")
    with col2:
        target_code = st.selectbox("Target language", [c for c, _ in choices], format_func=lambda c: dict(choices)[c], key="ocr_tgt")

    uploaded_image = st.file_uploader("Upload an image", type=[ext.lstrip(".") for ext in settings.allowed_image_extensions])

    if uploaded_image is not None:
        st.image(uploaded_image, caption="Preview", use_container_width=True)

        if st.button("Extract & Translate", type="primary"):
            service = _service()
            with st.spinner("Extracting text and translating..."):
                try:
                    result = service.translate_image(
                        filename=uploaded_image.name,
                        image_bytes=uploaded_image.getvalue(),
                        source_code=source_code,
                        target_code=target_code,
                        user_id=user["id"],
                    )
                except ALTError as exc:
                    st.error(exc.user_message)
                    return
                except Exception:
                    logger.exception("Unexpected error during OCR translation")
                    st.error("Something went wrong processing this image.")
                    return

            st.success(f"Done in {result['duration_seconds']:.2f}s.")
            col_orig, col_trans = st.columns(2)
            with col_orig:
                st.text_area("Extracted text", value=result["extracted_text"], height=200)
            with col_trans:
                st.text_area("Translated text", value=result["translated_text"], height=200)


render()
