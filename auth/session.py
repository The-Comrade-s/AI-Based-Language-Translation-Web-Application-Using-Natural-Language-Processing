"""
auth/session.py
================
Streamlit session-state wrappers for the current user and role-based
access control helpers. This is the only module that should read/write
`st.session_state.user` directly — everything else should call these
functions instead.
"""

from __future__ import annotations

import datetime as dt
from functools import wraps
from typing import Callable, TypeVar

import streamlit as st

from config import settings, Roles
from utils.exceptions import PermissionDeniedError
from utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., object])


def set_current_user(user: dict) -> None:
    """Store the authenticated user's public fields in session state and
    stamp the session start time for timeout tracking."""
    st.session_state.user = user
    st.session_state.session_started_at = dt.datetime.utcnow()


def clear_current_user() -> None:
    st.session_state.user = None
    st.session_state.session_started_at = None


def get_current_user() -> dict | None:
    """Return the current user dict, or None if not logged in or the
    session has timed out (in which case it is also cleared)."""
    user = st.session_state.get("user")
    if user is None:
        return None

    started_at = st.session_state.get("session_started_at")
    if started_at is not None:
        elapsed = dt.datetime.utcnow() - started_at
        if elapsed > dt.timedelta(minutes=settings.session_timeout_minutes):
            logger.info("Session timed out for user id=%s", user.get("id"))
            clear_current_user()
            return None

    return user


def is_authenticated() -> bool:
    return get_current_user() is not None


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and user.get("role") == Roles.ADMIN)


def require_login(page_render_fn: F) -> F:
    """Decorator for a Streamlit page-render function that requires the
    user to be logged in. Shows a warning and stops rendering otherwise."""

    @wraps(page_render_fn)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this page.")
            st.stop()
        return page_render_fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def require_admin(page_render_fn: F) -> F:
    """Decorator for a Streamlit page-render function restricted to
    administrators. Raises PermissionDeniedError (logged) and halts
    rendering for non-admins."""

    @wraps(page_render_fn)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("Please log in to access this page.")
            st.stop()
        if not is_admin():
            user = get_current_user()
            logger.warning("Permission denied: user id=%s attempted admin page", user.get("id") if user else None)
            st.error("You do not have permission to view this page.")
            st.stop()
        return page_render_fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def check_permission(required_role: str) -> None:
    """Imperative permission check for use inside services, not just pages.
    Raises PermissionDeniedError rather than touching Streamlit directly,
    so it can be used outside a page-render context too."""
    user = get_current_user()
    if user is None:
        raise PermissionDeniedError("Not authenticated", user_message="Please log in.")
    if required_role == Roles.ADMIN and user.get("role") != Roles.ADMIN:
        raise PermissionDeniedError(
            f"User id={user.get('id')} lacks admin role", user_message="Administrator access required."
        )
