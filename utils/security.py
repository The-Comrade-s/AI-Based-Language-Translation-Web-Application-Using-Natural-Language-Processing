"""
utils/security.py
==================
Low-level security primitives: password hashing/verification, secure
token generation, and input validation helpers. Business logic (login
flow, lockout policy, etc.) belongs in `auth/service.py`, not here.
"""

from __future__ import annotations

import re
import secrets
import hashlib

import bcrypt

from config import settings

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{3,50}$")


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt (salted automatically)."""
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash (e.g. legacy/corrupt data) — never crash on this path.
        return False


def password_strength_errors(password: str) -> list[str]:
    """Return a list of human-readable reasons the password is too weak.
    An empty list means the password passes all rules."""
    errors: list[str] = []

    if len(password) < settings.password_min_length:
        errors.append(f"Password must be at least {settings.password_min_length} characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must include at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must include at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must include at least one digit.")
    if not re.search(r"[^\w\s]", password):
        errors.append("Password must include at least one special character.")

    return errors


# --------------------------------------------------------------------------
# Secure tokens (password reset, session identifiers)
# --------------------------------------------------------------------------

def generate_secure_token(num_bytes: int = 32) -> str:
    """Generate a URL-safe random token, e.g. for password reset links."""
    return secrets.token_urlsafe(num_bytes)


def hash_token(token: str) -> str:
    """Hash a token before persisting it, so the raw token (sent to the
    user) is never recoverable from the database alone."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Input validation & normalization
# --------------------------------------------------------------------------

def normalize_email(email: str) -> str:
    """Trim and lowercase an email address for consistent storage/lookup."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def is_valid_username(username: str) -> bool:
    return bool(_USERNAME_RE.match(username.strip()))


def sanitize_text_input(value: str, max_length: int = 500) -> str:
    """Strip whitespace and control characters, and cap length, for any
    free-text field before it touches the database or is rendered."""
    cleaned = "".join(ch for ch in value if ch.isprintable() or ch in "\n\t")
    return cleaned.strip()[:max_length]
