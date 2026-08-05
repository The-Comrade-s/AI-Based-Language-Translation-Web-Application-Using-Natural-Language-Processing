"""
services/admin_service.py
==========================
Administrator operations: user management, system-wide statistics, and
activity-log access. All methods here should be called only after
`auth.session.check_permission(Roles.ADMIN)` or the `require_admin` page
decorator has already gated access — this service does not re-check
permissions itself, to keep it usable from background/report contexts.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select, func

from config import Roles
from database.base import get_session
from models.user import User, ActivityLog
from models.translation import TranslationHistory
from utils.exceptions import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)


class AdminService:
    """User management and system-wide reporting for administrators."""

    # ------------------------------------------------------------
    # User management
    # ------------------------------------------------------------

    def list_users(self, search: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        with get_session() as session:
            query = select(User)
            if search:
                like = f"%{search.strip()}%"
                query = query.where(
                    (User.email.ilike(like)) | (User.full_name.ilike(like)) | (User.username.ilike(like))
                )
            query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
            users = session.execute(query).scalars().all()
            return [self._user_to_dict(u) for u in users]

    def count_users(self) -> int:
        with get_session() as session:
            return session.execute(select(func.count()).select_from(User)).scalar_one()

    def set_user_active(self, target_user_id: int, is_active: bool) -> None:
        with get_session() as session:
            user = session.get(User, target_user_id)
            if user is None:
                raise ValidationError(f"User {target_user_id} not found", user_message="User not found.")
            user.is_active = is_active
            session.add(ActivityLog(user_id=target_user_id, action="account_enabled" if is_active else "account_disabled"))
        logger.info("User %s set is_active=%s by admin action", target_user_id, is_active)

    def set_user_role(self, target_user_id: int, role: str) -> None:
        if role not in Roles.ALL:
            raise ValidationError(f"Invalid role: {role}", user_message="Invalid role.")
        with get_session() as session:
            user = session.get(User, target_user_id)
            if user is None:
                raise ValidationError(f"User {target_user_id} not found", user_message="User not found.")
            user.role = role
            session.add(ActivityLog(user_id=target_user_id, action=f"role_changed_to_{role}"))
        logger.info("User %s role changed to %s by admin action", target_user_id, role)

    def delete_user(self, target_user_id: int) -> None:
        with get_session() as session:
            user = session.get(User, target_user_id)
            if user is None:
                raise ValidationError(f"User {target_user_id} not found", user_message="User not found.")
            session.delete(user)
        logger.warning("User %s deleted by admin action", target_user_id)

    # ------------------------------------------------------------
    # System-wide statistics
    # ------------------------------------------------------------

    def system_overview(self) -> dict:
        with get_session() as session:
            total_users = session.execute(select(func.count()).select_from(User)).scalar_one()
            active_users = session.execute(
                select(func.count()).select_from(User).where(User.is_active.is_(True))
            ).scalar_one()
            disabled_users = total_users - active_users
            total_translations = session.execute(
                select(func.count()).select_from(TranslationHistory)
            ).scalar_one()

            today = dt.datetime.utcnow().date()
            translations_today = session.execute(
                select(func.count()).select_from(TranslationHistory).where(
                    func.date(TranslationHistory.created_at) == today
                )
            ).scalar_one()

            return {
                "total_users": total_users,
                "active_users": active_users,
                "disabled_users": disabled_users,
                "total_translations": total_translations,
                "translations_today": translations_today,
            }

    # ------------------------------------------------------------
    # Activity / audit logs
    # ------------------------------------------------------------

    def list_activity_logs(
        self,
        user_id: int | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        with get_session() as session:
            query = select(ActivityLog)
            if user_id is not None:
                query = query.where(ActivityLog.user_id == user_id)
            if action:
                query = query.where(ActivityLog.action == action)
            query = query.order_by(ActivityLog.created_at.desc()).limit(limit).offset(offset)
            logs = session.execute(query).scalars().all()
            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at,
                }
                for log in logs
            ]

    @staticmethod
    def _user_to_dict(user: User) -> dict:
        return {
            "id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
        }
