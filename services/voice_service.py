"""
services/voice_service.py
==========================
Speech-to-text (via SpeechRecognition) and text-to-speech (via gTTS),
plus the orchestration to go from an uploaded audio file to a translated
transcript. Live microphone capture is a browser/client-side concern in
Streamlit and is wired up in the page layer, not here.
"""

from __future__ import annotations

import io
import time

from config import settings
from services.translation_service import TranslationService
from utils.exceptions import VoiceProcessingError, ValidationError
from utils.file_validation import validate_file
from utils.logger import get_logger

logger = get_logger(__name__)

# SpeechRecognition's Google Web Speech API needs a BCP-47 locale, not our
# short registry code — map the common ones explicitly rather than guessing.
_SPEECH_RECOGNITION_LOCALES = {
    "en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "pt": "pt-PT",
    "it": "it-IT", "ru": "ru-RU", "ar": "ar-SA", "hi": "hi-IN", "zh-CN": "zh-CN",
    "ja": "ja-JP", "ko": "ko-KR", "sw": "sw-KE", "tr": "tr-TR",
}


class SpeechRecognitionService:
    """Converts spoken audio into text."""

    def transcribe(self, audio_bytes: bytes, language_code: str = "en") -> str:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise VoiceProcessingError(
                f"SpeechRecognition not installed: {exc}",
                user_message="Voice transcription is not available right now.",
            ) from exc

        recognizer = sr.Recognizer()
        locale = _SPEECH_RECOGNITION_LOCALES.get(language_code, "en-US")

        try:
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = recognizer.record(source)
            transcript = recognizer.recognize_google(audio, language=locale)
        except sr.UnknownValueError as exc:
            raise VoiceProcessingError(
                f"Speech not understood: {exc}",
                user_message="Couldn't understand the audio. Please try again with clearer speech.",
            ) from exc
        except sr.RequestError as exc:
            raise VoiceProcessingError(
                f"Speech recognition service error: {exc}",
                user_message="Speech recognition service is unavailable right now.",
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise VoiceProcessingError(f"Transcription failed: {exc}", user_message="Could not process this audio file.") from exc

        cleaned = transcript.strip()
        if not cleaned:
            raise VoiceProcessingError("Empty transcript.", user_message="No speech was detected in the audio.")
        return cleaned


class TextToSpeechService:
    """Converts translated text into speech audio."""

    def synthesize(self, text: str, language_code: str = "en", slow: bool = False) -> bytes:
        try:
            from gtts import gTTS
        except ImportError as exc:
            raise VoiceProcessingError(
                f"gTTS not installed: {exc}",
                user_message="Text-to-speech is not available right now.",
            ) from exc

        if not text.strip():
            raise ValidationError("Empty text for speech synthesis.", user_message="There's no text to read aloud.")

        # gTTS uses its own language code set, mostly matching ISO 639-1;
        # our registry codes align closely enough for the languages gTTS
        # supports (it does not support Yoruba/Hausa/Igbo — that's a real
        # limitation of gTTS, not of ALT's architecture).
        gtts_lang = language_code.split("-")[0]

        try:
            buffer = io.BytesIO()
            tts = gTTS(text=text, lang=gtts_lang, slow=slow)
            tts.write_to_fp(buffer)
            return buffer.getvalue()
        except Exception as exc:  # noqa: BLE001
            raise VoiceProcessingError(
                f"Speech synthesis failed for lang={gtts_lang}: {exc}",
                user_message="Could not generate audio for this language.",
            ) from exc


class VoiceTranslationService:
    """Orchestrates: audio -> transcript -> translation, and optionally
    -> synthesized speech of the translation."""

    def __init__(
        self,
        translation_service: TranslationService | None = None,
        speech_recognition: SpeechRecognitionService | None = None,
        text_to_speech: TextToSpeechService | None = None,
    ) -> None:
        self._translator = translation_service or TranslationService()
        self._stt = speech_recognition or SpeechRecognitionService()
        self._tts = text_to_speech or TextToSpeechService()

    def translate_audio(
        self,
        filename: str,
        audio_bytes: bytes,
        source_code: str,
        target_code: str,
        user_id: int | None = None,
        synthesize_output: bool = False,
    ) -> dict:
        safe_name = validate_file(filename, len(audio_bytes), settings.allowed_audio_extensions)

        start = time.perf_counter()
        transcript = self._stt.transcribe(audio_bytes, language_code=source_code)

        result = self._translator.translate(
            transcript, source_code=source_code, target_code=target_code, user_id=user_id, save_history=False
        )

        output_audio: bytes | None = None
        if synthesize_output:
            try:
                output_audio = self._tts.synthesize(result.translated_text, language_code=target_code)
            except VoiceProcessingError as exc:
                # Synthesis is a nice-to-have on top of a successful
                # translation — don't fail the whole request for it.
                logger.warning("Speech synthesis skipped: %s", exc.message)

        duration = time.perf_counter() - start
        logger.info("Voice translated: %s in %.2fs", safe_name, duration)

        return {
            "filename": safe_name,
            "transcript": transcript,
            "translated_text": result.translated_text,
            "output_audio": output_audio,
            "duration_seconds": round(duration, 3),
        }
