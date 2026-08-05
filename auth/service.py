"""
auth/service.py
================
Business logic for registration, login, logout, password reset, and
password change. Streamlit pages call into this service; they should
never touch the database or password hashes directly.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings, Roles
from database.base import get_session
from models.user import User, UserSettings, ActivityLog, PasswordResetToken
from utils.exceptions import AuthenticationError, AccountLockedError, ValidationError
from utils.logger import get_logger
from utils.security import (
    hash_password,
    verify_password,
    password_strength_errors,
    normalize_email,
    is_valid_email,
    is_valid_username,
    generate_secure_token,
    hash_token,
)

logger = get_logger(__name__)


def _log_activity(session: Session, user_id: int | None, action: str, ip: str | None = None) -> None:
    session.add(ActivityLog(user_id=user_id, action=action, ip_address=ip))


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------

def register_user(
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
    username: str | None = None,
    phone: str | None = None,
) -> SimpleNamespace:
    """Validate and create a new user account with the default role.

    Raises ValidationError if any field fails validation, including
    duplicate email/username and password mismatch.

    Returns a detached, read-only snapshot of the created user's public
    fields (not the live ORM object, which would be unusable once the
    database session in this function closes).
    """
    errors: list[str] = []

    full_name = full_name.strip()
    email = normalize_email(email)
    username = username.strip() if username else None
    phone = phone.strip() if phone else None

    if not full_name:
        errors.append("Full name is required.")
    if not email or not is_valid_email(email):
        errors.append("A valid email address is required.")
    if username and not is_valid_username(username):
        errors.append("Username must be 3-50 characters (letters, numbers, '.', '_').")
    if password != confirm_password:
        errors.append("Password and confirmation do not match.")

    errors.extend(password_strength_errors(password))

    if errors:
        raise ValidationError("; ".join(errors), user_message=" ".join(errors))

    with get_session() as session:
        existing_email = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing_email is not None:
            raise ValidationError(
                f"Email already registered: {email}",
                user_message="An account with this email already exists.",
            )

        if username:
            existing_username = session.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()
            if existing_username is not None:
                raise ValidationError(
                    f"Username already taken: {username}",
                    user_message="That username is already taken.",
                )

        user = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            role=Roles.USER,
            is_active=True,
        )
        session.add(user)
        session.flush()  # populate user.id before creating dependent rows

        session.add(UserSettings(user_id=user.id))
        _log_activity(session, user.id, "registration")

        session.flush()
        logger.info("New user registered: %s", email)

        # Return a plain, detached snapshot — the ORM `user` object becomes
        # unusable once this session closes at the end of the `with` block.
        return SimpleNamespace(
            id=user.id,
            full_name=user.full_name,
            username=user.username,
            email=user.email,
            role=user.role,
        )


# --------------------------------------------------------------------------
# Login / Logout
# --------------------------------------------------------------------------

def login_user(email: str, password: str, ip: str | None = None) -> dict:
    """Authenticate a user by email and password.

    Returns a plain dict of the authenticated user's public fields on
    success (not the live ORM object, since the session is closed by
    the time this returns). Raises AuthenticationError or
    AccountLockedError on failure.
    """
    email = normalize_email(email)

    # NOTE: get_session() rolls back the *entire* transaction if an
    # exception propagates out of the `with` block. Since failed-attempt
    # and lockout bookkeeping must survive even when we go on to raise an
    # AuthenticationError, we compute the outcome first, let the `with`
    # block exit normally (so those writes commit), and raise afterwards.
    pending_error: AuthenticationError | AccountLockedError | None = None
    result: dict | None = None

    with get_session() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()

        if user is None:
            pending_error = AuthenticationError(
                "No account with that email.", user_message="Invalid email or password."
            )
        elif user.account_locked_until and user.account_locked_until > dt.datetime.utcnow():
            remaining = (user.account_locked_until - dt.datetime.utcnow()).seconds // 60 + 1
            pending_error = AccountLockedError(
                f"Account locked for user {user.id}",
                user_message=f"Account temporarily locked. Try again in about {remaining} minute(s).",
            )
        elif not user.is_active:
            pending_error = AuthenticationError(
                f"Inactive account login attempt: {email}",
                user_message="This account has been disabled. Contact an administrator.",
            )
        elif not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.account_locked_until = dt.datetime.utcnow() + dt.timedelta(
                    minutes=settings.account_lockout_minutes
                )
                _log_activity(session, user.id, "account_locked", ip)
                logger.warning("Account locked after repeated failures: %s", email)
            _log_activity(session, user.id, "failed_login", ip)
            pending_error = AuthenticationError("Incorrect password.", user_message="Invalid email or password.")
        else:
            # Successful login — reset lockout state.
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_login = dt.datetime.utcnow()
            _log_activity(session, user.id, "login", ip)
            logger.info("User logged in: %s", email)

            result = {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "profile_image": user.profile_image,
            }

    if pending_error is not None:
        raise pending_error
    assert result is not None
    return result


def logout_user(user_id: int | None, ip: str | None = None) -> None:
    """Record a logout event. Session/state clearing itself happens in
    the Streamlit layer (auth/session.py)."""
    if user_id is None:
        return
    with get_session() as session:
        _log_activity(session, user_id, "logout", ip)
    logger.info("User logged out: id=%s", user_id)


# --------------------------------------------------------------------------
# Password reset
# --------------------------------------------------------------------------

def request_password_reset(email: str) -> str | None:
    """Create a reset token for the given email if an account exists.

    Returns the raw token (to be delivered to the user, e.g. via email —
    email delivery itself is out of scope here and can be wired in later
    without changing this function's contract). Returns None silently if
    no account matches, so callers can't use this to enumerate accounts.
    """
    email = normalize_email(email)
    with get_session() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            logger.info("Password reset requested for unknown email: %s", email)
            return None

        raw_token = generate_secure_token()
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=dt.datetime.utcnow() + dt.timedelta(hours=1),
        )
        session.add(token)
        _log_activity(session, user.id, "password_reset_requested")
        logger.info("Password reset token issued for: %s", email)
        return raw_token


def reset_password(raw_token: str, new_password: str, confirm_password: str) -> None:
    """Complete a password reset given a raw token from request_password_reset."""
    if new_password != confirm_password:
        raise ValidationError("Passwords do not match.", user_message="Passwords do not match.")

    errors = password_strength_errors(new_password)
    if errors:
        raise ValidationError("; ".join(errors), user_message=" ".join(errors))

    token_hash = hash_token(raw_token)

    with get_session() as session:
        token = session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        ).scalar_one_or_none()

        if token is None or token.used or token.expires_at < dt.datetime.utcnow():
            raise ValidationError(
                "Invalid or expired reset token.",
                user_message="This reset link is invalid or has expired. Please request a new one.",
            )

        user = session.get(User, token.user_id)
        if user is None:
            raise ValidationError("User no longer exists.", user_message="This account no longer exists.")

        user.password_hash = hash_password(new_password)
        token.used = True
        _log_activity(session, user.id, "password_reset_completed")
        logger.info("Password reset completed for user id=%s", user.id)


def change_password(user_id: int, current_password: str, new_password: str, confirm_password: str) -> None:
    """Change the password for an already-authenticated user."""
    if new_password != confirm_password:
        raise ValidationError("Passwords do not match.", user_message="New passwords do not match.")

    errors = password_strength_errors(new_password)
    if errors:
        raise ValidationError("; ".join(errors), user_message=" ".join(errors))

    with get_session() as session:
        user = session.get(User, user_id)
        if user is None:
            raise AuthenticationError("User not found.", user_message="Account not found.")

        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password incorrect.", user_message="Current password is incorrect.")

        if verify_password(new_password, user.password_hash):
            raise ValidationError(
                "New password matches current password.",
                user_message="New password must be different from your current password.",
            )

        user.password_hash = hash_password(new_password)
        _log_activity(session, user.id, "password_changed")
        logger.info("Password changed for user id=%s", user_id)
