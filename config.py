"""
config.py
=========
Central configuration for the ALT (AI Language Translator) application.

All environment-dependent and application-wide constants are defined here.
No other module should hard-code paths, secrets, or tunables — import from
this module instead, so behavior can be changed in exactly one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Load variables from a local .env file if present (e.g. ALT_SECRET_KEY,
# ALT_DATABASE_URL for production). Safe no-op if no .env file exists.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# --------------------------------------------------------------------------
# Base paths
# --------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = BASE_DIR / "assets"
DATA_DIR: Path = BASE_DIR / "data"
EXPORTS_DIR: Path = BASE_DIR / "exports"
LOGS_DIR: Path = BASE_DIR / "logs"
MODELS_CACHE_DIR: Path = DATA_DIR / "model_cache"
TEMP_DIR: Path = DATA_DIR / "temp"

for _dir in (DATA_DIR, EXPORTS_DIR, LOGS_DIR, MODELS_CACHE_DIR, TEMP_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean environment variable safely."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Parse an integer environment variable safely, falling back on error."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass(frozen=True)
class AppConfig:
    """Application-wide configuration, sourced from environment variables
    with sensible development defaults."""

    # --- General ---
    app_name: str = "ALT — AI Language Translator"
    app_short_name: str = "ALT"
    environment: str = field(default_factory=lambda: os.getenv("ALT_ENV", "development"))
    debug: bool = field(default_factory=lambda: _env_bool("ALT_DEBUG", True))
    secret_key: str = field(default_factory=lambda: os.getenv("ALT_SECRET_KEY", "dev-secret-change-me"))

    # --- Database ---
    database_path: Path = field(default_factory=lambda: BASE_DIR / "database.db")
    database_url: str = field(default_factory=lambda: os.getenv(
        "ALT_DATABASE_URL", f"sqlite:///{(BASE_DIR / 'database.db').as_posix()}"
    ))

    # --- Session / Security ---
    session_timeout_minutes: int = field(default_factory=lambda: _env_int("ALT_SESSION_TIMEOUT_MIN", 60))
    max_failed_login_attempts: int = field(default_factory=lambda: _env_int("ALT_MAX_FAILED_LOGINS", 5))
    account_lockout_minutes: int = field(default_factory=lambda: _env_int("ALT_LOCKOUT_MIN", 15))
    password_min_length: int = 8
    bcrypt_rounds: int = field(default_factory=lambda: _env_int("ALT_BCRYPT_ROUNDS", 12))

    # --- AI Translation ---
    primary_model_name: str = field(default_factory=lambda: os.getenv(
        "ALT_PRIMARY_MODEL", "facebook/nllb-200-distilled-600M"
    ))
    fallback_model_name: str = field(default_factory=lambda: os.getenv(
        "ALT_FALLBACK_MODEL", "Helsinki-NLP/opus-mt-{src}-{tgt}"
    ))
    max_translation_chars: int = field(default_factory=lambda: _env_int("ALT_MAX_TRANSLATION_CHARS", 5000))
    translation_timeout_seconds: int = field(default_factory=lambda: _env_int("ALT_TRANSLATION_TIMEOUT", 30))
    force_cpu: bool = field(default_factory=lambda: _env_bool("ALT_FORCE_CPU", False))

    # --- File uploads ---
    max_upload_size_mb: int = field(default_factory=lambda: _env_int("ALT_MAX_UPLOAD_MB", 20))
    allowed_document_extensions: tuple = (".txt", ".docx", ".pdf", ".rtf", ".csv", ".json", ".md")
    allowed_image_extensions: tuple = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
    allowed_audio_extensions: tuple = (".wav", ".mp3", ".ogg", ".flac", ".m4a")

    # --- Logging ---
    log_level: str = field(default_factory=lambda: os.getenv("ALT_LOG_LEVEL", "INFO"))
    log_file: Path = field(default_factory=lambda: LOGS_DIR / "alt.log")
    log_max_bytes: int = 5 * 1024 * 1024  # 5 MB
    log_backup_count: int = 5


# Singleton instance imported throughout the app
settings = AppConfig()


# --------------------------------------------------------------------------
# Roles & constants shared across modules
# --------------------------------------------------------------------------

class Roles:
    """User role constants — avoids magic strings scattered across modules."""
    USER = "user"
    ADMIN = "admin"

    ALL = (USER, ADMIN)


class MandatoryLanguages:
    """Nigerian languages that must always be present in the language registry."""
    YORUBA = "yo"
    HAUSA = "ha"
    IGBO = "ig"
