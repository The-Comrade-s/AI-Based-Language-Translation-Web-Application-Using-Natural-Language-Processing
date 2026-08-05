"""
models/media.py
================
History tables for voice, document, and OCR translation activity
(ALT-005). Kept in a separate module from the core TranslationHistory
since these have distinct fields (file metadata, audio duration, etc.).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class VoiceHistory(Base):
    """A completed voice-translation request."""

    __tablename__ = "voice_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    audio_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship()  # noqa: F821


class DocumentHistory(Base):
    """A completed document-translation request."""

    __tablename__ = "document_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    translation_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship()  # noqa: F821


class OCRHistory(Base):
    """A completed OCR-translation request."""

    __tablename__ = "ocr_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship()  # noqa: F821
