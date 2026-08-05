"""
services/ocr_service.py
========================
Extracts text from images via pytesseract and translates it. Image
preprocessing (grayscale + contrast) is applied before OCR to improve
extraction accuracy on photos of text (signs, screenshots, scanned
pages) rather than only clean digital documents.
"""

from __future__ import annotations

import io
import time

from config import settings
from services.translation_service import TranslationService
from utils.exceptions import OCRError, ValidationError
from utils.file_validation import validate_file
from utils.logger import get_logger

logger = get_logger(__name__)


class OCRService:
    """Extracts and translates text found in images."""

    def __init__(self, translation_service: TranslationService | None = None) -> None:
        self._translator = translation_service or TranslationService()

    def _preprocess_image(self, image):
        """Apply light preprocessing to improve OCR accuracy: convert to
        grayscale and boost contrast. Kept minimal and safe — aggressive
        preprocessing can hurt accuracy on already-clean images."""
        from PIL import ImageOps, ImageEnhance

        grayscale = ImageOps.grayscale(image)
        enhancer = ImageEnhance.Contrast(grayscale)
        return enhancer.enhance(1.5)

    def extract_text(self, image_bytes: bytes) -> str:
        """Run OCR on raw image bytes and return the extracted text."""
        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            raise OCRError(
                f"OCR dependencies not installed: {exc}",
                user_message="Image text extraction is not available right now.",
            ) from exc

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(
                f"Could not open image: {exc}", user_message="This file doesn't look like a valid image."
            ) from exc

        try:
            processed = self._preprocess_image(image)
            text = pytesseract.image_to_string(processed)
        except pytesseract.TesseractNotFoundError as exc:
            raise OCRError(
                f"Tesseract binary not found: {exc}",
                user_message="OCR engine is not installed on this server.",
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise OCRError(f"OCR extraction failed: {exc}", user_message="Could not extract text from this image.") from exc

        cleaned = text.strip()
        if not cleaned:
            raise OCRError(
                "No text detected in image.",
                user_message="No readable text was found in this image. Try a clearer photo.",
            )
        return cleaned

    def translate_image(
        self,
        filename: str,
        image_bytes: bytes,
        source_code: str,
        target_code: str,
        user_id: int | None = None,
    ) -> dict:
        """Validate, OCR, and translate the text found in an image."""
        safe_name = validate_file(filename, len(image_bytes), settings.allowed_image_extensions)

        start = time.perf_counter()
        extracted_text = self.extract_text(image_bytes)

        result = self._translator.translate(
            extracted_text, source_code=source_code, target_code=target_code, user_id=user_id, save_history=False
        )
        duration = time.perf_counter() - start

        logger.info("Image translated: %s in %.2fs", safe_name, duration)

        return {
            "filename": safe_name,
            "extracted_text": extracted_text,
            "translated_text": result.translated_text,
            "duration_seconds": round(duration, 3),
        }
