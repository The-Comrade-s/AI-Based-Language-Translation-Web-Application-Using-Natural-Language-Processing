"""
services/document_service.py
=============================
Extracts text from uploaded documents (TXT, DOCX, PDF, CSV, JSON, MD)
and runs it through TranslationService. Text extraction is isolated per
format in small `_extract_*` methods so new formats can be added without
touching the orchestration logic.
"""

from __future__ import annotations

import io
import json
import time

from config import settings
from services.translation_service import TranslationService
from utils.exceptions import ValidationError
from utils.file_validation import validate_file
from utils.logger import get_logger

logger = get_logger(__name__)


class DocumentTranslationService:
    """Translates whole documents by extracting their text, translating
    it, and returning the translated text (and, for DOCX, a rebuilt
    document)."""

    def __init__(self, translation_service: TranslationService | None = None) -> None:
        self._translator = translation_service or TranslationService()

    # ----------------------------------------------------------------
    # Extraction
    # ----------------------------------------------------------------

    def _extract_txt(self, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8", errors="replace")

    def _extract_md(self, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8", errors="replace")

    def _extract_csv(self, file_bytes: bytes) -> str:
        import csv as csv_module

        text_stream = io.StringIO(file_bytes.decode("utf-8", errors="replace"))
        reader = csv_module.reader(text_stream)
        rows = [", ".join(row) for row in reader]
        return "\n".join(rows)

    def _extract_json(self, file_bytes: bytes) -> str:
        try:
            data = json.loads(file_bytes.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON: {exc}", user_message="This file is not valid JSON.") from exc
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _extract_docx(self, file_bytes: bytes) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise ValidationError(
                f"python-docx not installed: {exc}", user_message="DOCX processing is unavailable."
            ) from exc

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _extract_pdf(self, file_bytes: bytes) -> str:
        try:
            import pdfplumber
        except ImportError as exc:
            raise ValidationError(
                f"pdfplumber not installed: {exc}", user_message="PDF processing is unavailable."
            ) from exc

        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    _EXTRACTORS = {
        ".txt": _extract_txt,
        ".md": _extract_md,
        ".csv": _extract_csv,
        ".json": _extract_json,
        ".docx": _extract_docx,
        ".pdf": _extract_pdf,
    }

    def extract_text(self, filename: str, file_bytes: bytes) -> str:
        """Extract plain text from a document, dispatching by extension."""
        from pathlib import Path

        extension = Path(filename).suffix.lower()
        extractor = self._EXTRACTORS.get(extension)
        if extractor is None:
            raise ValidationError(
                f"No extractor for extension: {extension}",
                user_message=f"Unsupported document type: {extension}",
            )
        text = extractor(self, file_bytes)
        if not text.strip():
            raise ValidationError("Document contains no extractable text.", user_message="No text found in this document.")
        return text

    # ----------------------------------------------------------------
    # Orchestration
    # ----------------------------------------------------------------

    def translate_document(
        self,
        filename: str,
        file_bytes: bytes,
        source_code: str,
        target_code: str,
        user_id: int | None = None,
    ) -> dict:
        """Validate, extract, and translate a document. Returns a dict
        with the extracted text, translated text, and timing/metadata —
        callers build the download artifact (e.g. via ExportService)."""
        safe_name = validate_file(filename, len(file_bytes), settings.allowed_document_extensions)

        start = time.perf_counter()
        extracted_text = self.extract_text(safe_name, file_bytes)

        # Long documents are translated in chunks to respect the model's
        # max-length limits, then rejoined — paragraph breaks are used as
        # natural chunk boundaries so context isn't split mid-sentence.
        chunks = self._chunk_text(extracted_text)
        translated_chunks = []
        for chunk in chunks:
            result = self._translator.translate(
                chunk, source_code=source_code, target_code=target_code, user_id=user_id, save_history=False
            )
            translated_chunks.append(result.translated_text)

        translated_text = "\n\n".join(translated_chunks)
        duration = time.perf_counter() - start

        logger.info("Document translated: %s (%d chunks) in %.2fs", safe_name, len(chunks), duration)

        return {
            "filename": safe_name,
            "extracted_text": extracted_text,
            "translated_text": translated_text,
            "chunk_count": len(chunks),
            "duration_seconds": round(duration, 3),
        }

    def _chunk_text(self, text: str, max_chunk_chars: int | None = None) -> list[str]:
        """Split text into chunks no larger than max_chunk_chars,
        breaking on paragraph boundaries where possible."""
        limit = max_chunk_chars or settings.max_translation_chars
        paragraphs = text.split("\n\n")

        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}" if current else para
            if len(candidate) > limit and current:
                chunks.append(current)
                current = para
            else:
                current = candidate
        if current:
            chunks.append(current)

        return chunks or [text[:limit]]
