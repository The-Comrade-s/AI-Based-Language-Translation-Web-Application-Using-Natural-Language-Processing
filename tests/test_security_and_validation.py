"""tests/test_security_and_validation.py"""

from __future__ import annotations

import pytest

from utils.security import (
    hash_password, verify_password, password_strength_errors,
    normalize_email, is_valid_email, sanitize_text_input,
)
from utils.file_validation import validate_file, sanitize_filename
from utils.exceptions import FileValidationError
from utils.rate_limiter import RateLimiter


def test_password_hash_roundtrip():
    hashed = hash_password("Str0ng!Pass")
    assert verify_password("Str0ng!Pass", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_password_hash_is_salted_differently_each_time():
    h1 = hash_password("Str0ng!Pass")
    h2 = hash_password("Str0ng!Pass")
    assert h1 != h2  # different salts


def test_password_strength_rules():
    assert password_strength_errors("Str0ng!Pass") == []
    assert len(password_strength_errors("weak")) > 0
    assert len(password_strength_errors("alllowercase1!")) > 0  # no uppercase
    assert len(password_strength_errors("NOLOWERCASE1!")) > 0  # no lowercase
    assert len(password_strength_errors("NoDigitsHere!")) > 0  # no digit
    assert len(password_strength_errors("NoSpecial123")) > 0  # no special char


def test_email_normalization_and_validation():
    assert normalize_email("  Test@EXAMPLE.com  ") == "test@example.com"
    assert is_valid_email("test@example.com") is True
    assert is_valid_email("not-an-email") is False


def test_sanitize_text_input_strips_and_truncates():
    assert sanitize_text_input("  hello  ") == "hello"
    assert len(sanitize_text_input("x" * 1000, max_length=10)) == 10


def test_file_validation_rejects_bad_extension():
    with pytest.raises(FileValidationError):
        validate_file("virus.exe", 100, (".txt", ".pdf"))


def test_file_validation_rejects_oversized():
    with pytest.raises(FileValidationError):
        validate_file("big.txt", 999_999_999_999, (".txt",))


def test_file_validation_rejects_empty():
    with pytest.raises(FileValidationError):
        validate_file("empty.txt", 0, (".txt",))


def test_sanitize_filename_strips_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("normal file!.txt") == "normal_file_.txt"


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    key = "test-user"
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is False  # 4th call within window rejected


def test_rate_limiter_keys_are_independent():
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    assert limiter.is_allowed("user-a") is True
    assert limiter.is_allowed("user-b") is True  # different key, independent limit
    assert limiter.is_allowed("user-a") is False
