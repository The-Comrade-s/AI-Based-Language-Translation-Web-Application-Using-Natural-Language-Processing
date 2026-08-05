"""tests/test_auth.py — registration, login, lockout, password reset."""

from __future__ import annotations

import pytest

from auth.service import (
    register_user, login_user, change_password,
    request_password_reset, reset_password,
)
from utils.exceptions import ValidationError, AuthenticationError, AccountLockedError


def test_register_and_login():
    u = register_user("Test User", "test@example.com", "Str0ng!Pass", "Str0ng!Pass")
    assert u.email == "test@example.com"

    session_user = login_user("test@example.com", "Str0ng!Pass")
    assert session_user["email"] == "test@example.com"
    assert session_user["role"] == "user"


def test_duplicate_email_rejected():
    register_user("First", "dup@example.com", "Str0ng!Pass", "Str0ng!Pass")
    with pytest.raises(ValidationError):
        register_user("Second", "dup@example.com", "Str0ng!Pass", "Str0ng!Pass")


def test_weak_password_rejected():
    with pytest.raises(ValidationError):
        register_user("Weak", "weak@example.com", "weak", "weak")


def test_password_mismatch_rejected():
    with pytest.raises(ValidationError):
        register_user("Mismatch", "mismatch@example.com", "Str0ng!Pass", "Different!Pass")


def test_wrong_password_rejected():
    register_user("User", "wrongpw@example.com", "Str0ng!Pass", "Str0ng!Pass")
    with pytest.raises(AuthenticationError):
        login_user("wrongpw@example.com", "WrongPassword1!")


def test_account_lockout_after_repeated_failures():
    register_user("Lockout", "lockout@example.com", "Str0ng!Pass", "Str0ng!Pass")
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            login_user("lockout@example.com", "WrongPassword1!")

    with pytest.raises(AccountLockedError):
        login_user("lockout@example.com", "Str0ng!Pass")


def test_change_password_flow():
    u = register_user("Changer", "changer@example.com", "Str0ng!Pass", "Str0ng!Pass")
    change_password(u.id, "Str0ng!Pass", "N3wStr0ng!Pass", "N3wStr0ng!Pass")
    session_user = login_user("changer@example.com", "N3wStr0ng!Pass")
    assert session_user["email"] == "changer@example.com"


def test_password_reset_flow():
    register_user("Resetter", "resetter@example.com", "Str0ng!Pass", "Str0ng!Pass")
    token = request_password_reset("resetter@example.com")
    assert token is not None

    reset_password(token, "Res3t!Password", "Res3t!Password")
    session_user = login_user("resetter@example.com", "Res3t!Password")
    assert session_user["email"] == "resetter@example.com"


def test_password_reset_unknown_email_returns_none():
    assert request_password_reset("nobody@example.com") is None


def test_reset_with_invalid_token_rejected():
    with pytest.raises(ValidationError):
        reset_password("not-a-real-token", "Res3t!Password", "Res3t!Password")
