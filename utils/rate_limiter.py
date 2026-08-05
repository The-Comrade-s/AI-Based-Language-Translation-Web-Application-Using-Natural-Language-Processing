"""
utils/rate_limiter.py
======================
A minimal in-process sliding-window rate limiter. Suitable for a
single-instance Streamlit deployment (ALT's target deployment per
ALT-001); a multi-instance deployment would need a shared store (e.g.
Redis) instead, which is a straightforward swap behind the same
`is_allowed()` interface.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Tracks call timestamps per key and rejects calls once the
    configured limit is exceeded within the given time window."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Return True and record the call if `key` is under its limit,
        False (without recording) if the limit has been reached."""
        now = time.monotonic()
        with self._lock:
            timestamps = self._calls[key]
            cutoff = now - self.window_seconds
            # Drop timestamps outside the current window.
            self._calls[key] = [t for t in timestamps if t > cutoff]

            if len(self._calls[key]) >= self.max_calls:
                return False

            self._calls[key].append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._calls.pop(key, None)


# Shared limiters for common abuse-prone actions.
translation_rate_limiter = RateLimiter(max_calls=30, window_seconds=60)
login_rate_limiter = RateLimiter(max_calls=10, window_seconds=60)
upload_rate_limiter = RateLimiter(max_calls=20, window_seconds=60)
