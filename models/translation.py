"""
models/translation.py
======================
Persistence for translation activity: history and favorites. Voice/OCR/
Document history tables are added in ALT-005; this file covers the core
text-translation record used by ALT-003 and ALT-004.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class TranslationHistory(Base):
    """A single completed translation, tied to the user who requested it."""

    __tablename__ = "translation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)

    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)

    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship()  # noqa: F821  (User imported lazily to avoid circular import)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<TranslationHistory id={self.id} {self.source_language}->{self.target_language} "
            f"user_id={self.user_id}>"
        )
