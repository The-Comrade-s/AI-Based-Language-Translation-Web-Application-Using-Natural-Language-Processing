"""
services/history_service.py
============================
Query and mutation operations over TranslationHistory: listing, search,
filtering, favoriting, deletion. Kept separate from TranslationService
(which only creates records) so read/management concerns don't bloat
the write path.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select, delete, func

from database.base import get_session
from models.translation import TranslationHistory
from utils.exceptions import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)


class HistoryService:
    """Read/manage a user's translation history and favorites."""

    def list_history(
        self,
        user_id: int,
        *,
        search: str | None = None,
        source_language: str | None = None,
        target_language: str | None = None,
        favorites_only: bool = False,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Return a page of history records matching the given filters,
        newest first."""
        with get_session() as session:
            query = select(TranslationHistory).where(TranslationHistory.user_id == user_id)

            if search:
                like = f"%{search.strip()}%"
                query = query.where(
                    (TranslationHistory.source_text.ilike(like))
                    | (TranslationHistory.translated_text.ilike(like))
                )
            if source_language:
                query = query.where(TranslationHistory.source_language == source_language)
            if target_language:
                query = query.where(TranslationHistory.target_language == target_language)
            if favorites_only:
                query = query.where(TranslationHistory.is_favorite.is_(True))
            if start_date:
                query = query.where(TranslationHistory.created_at >= dt.datetime.combine(start_date, dt.time.min))
            if end_date:
                query = query.where(TranslationHistory.created_at <= dt.datetime.combine(end_date, dt.time.max))

            query = query.order_by(TranslationHistory.created_at.desc()).limit(limit).offset(offset)

            rows = session.execute(query).scalars().all()
            return [self._to_dict(row) for row in rows]

    def count_history(self, user_id: int, favorites_only: bool = False) -> int:
        with get_session() as session:
            query = select(func.count()).select_from(TranslationHistory).where(
                TranslationHistory.user_id == user_id
            )
            if favorites_only:
                query = query.where(TranslationHistory.is_favorite.is_(True))
            return session.execute(query).scalar_one()

    def toggle_favorite(self, user_id: int, record_id: int) -> bool:
        """Flip the favorite flag on a record owned by `user_id`. Returns
        the new favorite state. Raises ValidationError if the record
        doesn't exist or doesn't belong to this user."""
        with get_session() as session:
            record = session.get(TranslationHistory, record_id)
            if record is None or record.user_id != user_id:
                raise ValidationError(
                    f"Record {record_id} not found for user {user_id}",
                    user_message="That translation record could not be found.",
                )
            record.is_favorite = not record.is_favorite
            new_state = record.is_favorite
        logger.info("Toggled favorite: record_id=%s user_id=%s -> %s", record_id, user_id, new_state)
        return new_state

    def delete_record(self, user_id: int, record_id: int) -> None:
        with get_session() as session:
            record = session.get(TranslationHistory, record_id)
            if record is None or record.user_id != user_id:
                raise ValidationError(
                    f"Record {record_id} not found for user {user_id}",
                    user_message="That translation record could not be found.",
                )
            session.delete(record)
        logger.info("Deleted history record_id=%s for user_id=%s", record_id, user_id)

    def delete_records(self, user_id: int, record_ids: list[int]) -> int:
        """Bulk-delete records by id, scoped to the owning user. Returns
        the number of records actually deleted."""
        if not record_ids:
            return 0
        with get_session() as session:
            result = session.execute(
                delete(TranslationHistory).where(
                    TranslationHistory.user_id == user_id,
                    TranslationHistory.id.in_(record_ids),
                )
            )
            deleted_count = result.rowcount or 0
        logger.info("Bulk-deleted %s history records for user_id=%s", deleted_count, user_id)
        return deleted_count

    def clear_history(self, user_id: int) -> int:
        with get_session() as session:
            result = session.execute(delete(TranslationHistory).where(TranslationHistory.user_id == user_id))
            deleted_count = result.rowcount or 0
        logger.info("Cleared all history for user_id=%s (%s records)", user_id, deleted_count)
        return deleted_count

    def get_statistics(self, user_id: int) -> dict:
        """Aggregate usage statistics for a user's dashboard."""
        with get_session() as session:
            base = select(TranslationHistory).where(TranslationHistory.user_id == user_id)
            all_rows = session.execute(base).scalars().all()

            if not all_rows:
                return {
                    "total_translations": 0,
                    "favorite_count": 0,
                    "total_words": 0,
                    "average_duration_seconds": 0.0,
                    "most_used_target_language": None,
                }

            total = len(all_rows)
            favorites = sum(1 for r in all_rows if r.is_favorite)
            total_words = sum(r.word_count for r in all_rows)
            avg_duration = sum(r.duration_seconds for r in all_rows) / total

            target_counts: dict[str, int] = {}
            for r in all_rows:
                target_counts[r.target_language] = target_counts.get(r.target_language, 0) + 1
            most_used_target = max(target_counts, key=target_counts.get) if target_counts else None

            today = dt.datetime.utcnow().date()
            week_ago = today - dt.timedelta(days=7)
            month_ago = today - dt.timedelta(days=30)

            return {
                "total_translations": total,
                "today_translations": sum(1 for r in all_rows if r.created_at.date() == today),
                "weekly_translations": sum(1 for r in all_rows if r.created_at.date() >= week_ago),
                "monthly_translations": sum(1 for r in all_rows if r.created_at.date() >= month_ago),
                "favorite_count": favorites,
                "total_words": total_words,
                "average_duration_seconds": round(avg_duration, 3),
                "most_used_target_language": most_used_target,
            }

    @staticmethod
    def _to_dict(record: TranslationHistory) -> dict:
        return {
            "id": record.id,
            "source_language": record.source_language,
            "target_language": record.target_language,
            "source_text": record.source_text,
            "translated_text": record.translated_text,
            "model_used": record.model_used,
            "duration_seconds": record.duration_seconds,
            "word_count": record.word_count,
            "character_count": record.character_count,
            "is_favorite": record.is_favorite,
            "created_at": record.created_at,
        }
