"""
pages/9_Voice_Translation.py
=============================
Upload spoken audio, transcribe it, translate the transcript, and
optionally synthesize the translation as speech.
"""

from __future__ import annotations

import streamlit as st

from ai.language_registry import language_choices
from auth.session import require_login, get_current_user
from config import settings
from services.voice_service import VoiceTranslationService
from utils.exceptions import ALTError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Voice Translation — ALT", page_icon="🎙️")


@st.cache_resource
def _service() -> VoiceTranslationService:
    return VoiceTranslationService()


@require_login
def render() -> None:
    user = get_current_user()
    st.title("🎙️ Voice Translation")
    st.caption(f"Supported: {', '.join(settings.allowed_audio_extensions)} · max {settings.max_upload_size_mb}MB")

    choices = language_choices()
    col1, col2 = st.columns(2)
    with col1:
        source_code = st.selectbox("Spoken language", [c for c, _ in choices], format_func=lambda c: dict(choices)[c], key="voice_src")
    with col2:
        target_code = st.selectbox("Translate to", [c for c, _ in choices], format_func=lambda c: dict(choices)[c], key="voice_tgt")

    synthesize = st.checkbox("Read translation aloud (text-to-speech)", value=True)

    uploaded_audio = st.file_uploader("Upload audio", type=[ext.lstrip(".") for ext in settings.allowed_audio_extensions])

    if uploaded_audio is not None:
        st.audio(uploaded_audio)

        if st.button("Transcribe & Translate", type="primary"):
            service = _service()
            with st.spinner("Transcribing and translating..."):
                try:
                    result = service.translate_audio(
                        filename=uploaded_audio.name,
                        audio_bytes=uploaded_audio.getvalue(),
                        source_code=source_code,
                        target_code=target_code,
                        user_id=user["id"],
                        synthesize_output=synthesize,
                    )
                except ALTError as exc:
                    st.error(exc.user_message)
                    return
                except Exception:
                    logger.exception("Unexpected error during voice translation")
                    st.error("Something went wrong processing this audio.")
                    return

            st.success(f"Done in {result['duration_seconds']:.2f}s.")
            st.text_area("Transcript", value=result["transcript"], height=100)
            st.text_area("Translation", value=result["translated_text"], height=100)

            if result["output_audio"]:
                st.audio(result["output_audio"], format="audio/mp3")
                st.download_button(
                    "Download translated audio",
                    data=result["output_audio"],
                    file_name="translated_speech.mp3",
                    mime="audio/mp3",
                )
            elif synthesize:
                st.info("Audio playback for the translation could not be generated for this language.")


render()
