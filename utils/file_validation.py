"""
utils/file_validation.py
=========================
Validates uploaded files (documents, images, audio) before they are
processed: extension allow-listing, size limits, and filename
sanitization. Used by the document, OCR, and voice services in ALT-005.
"""

from __future__ import annotations

import re
from pathlib import Path

from config import settings
from utils.exceptions import FileValidationError

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(filename: str) -> str:
    """Strip path components and replace unsafe characters, so a
    filename can never be used for path traversal or command injection."""
    name = Path(filename).name  # drop any directory components
    name = _SAFE_FILENAME_RE.sub("_", name)
    return name[:255] or "file"


def validate_file(filename: str, size_bytes: int, allowed_extensions: tuple[str, ...]) -> str:
    """Validate a file's extension and size. Returns the sanitized
    filename on success. Raises FileValidationError otherwise."""
    if not filename:
        raise FileValidationError("No filename provided.", user_message="Please choose a file to upload.")

    safe_name = sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()

    if extension not in allowed_extensions:
        raise FileValidationError(
            f"Unsupported extension: {extension}",
            user_message=f"Unsupported file type '{extension}'. Allowed: {', '.join(allowed_extensions)}",
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileValidationError(
            f"File too large: {size_bytes} bytes (limit {max_bytes})",
            user_message=f"File is too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )

    if size_bytes == 0:
        raise FileValidationError("Empty file.", user_message="The uploaded file is empty.")

    return safe_name
