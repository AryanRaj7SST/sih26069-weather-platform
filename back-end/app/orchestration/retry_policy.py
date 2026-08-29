"""Retry policy, backoff calculation, and failure classification for intelligence orchestration.

Guarantees:
- Transient network/database errors receive bounded exponential backoff with jitter.
- Schema/logical errors transition immediately to permanent failure (no endless loops).
- Maximum attempts are strictly capped per policy configuration.
"""

from __future__ import annotations

import random
from typing import Tuple, Type

import httpx
from pydantic import ValidationError

from app.orchestration.events import FailureClass

# Known transient error types
TRANSIENT_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    ConnectionError,
    TimeoutError,
)

# Known permanent error types
PERMANENT_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ValidationError,
    ValueError,
    KeyError,
    TypeError,
)


class RetryPolicy:
    """Configurable retry manager for asynchronous orchestration jobs."""

    def __init__(
        self,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 60.0,
        max_attempts: int = 3,
        jitter_factor: float = 0.20,
    ) -> None:
        self.base_delay = base_delay_seconds
        self.max_delay = max_delay_seconds
        self.max_attempts = max_attempts
        self.jitter_factor = jitter_factor

    def classify_error(self, exc: Exception) -> FailureClass:
        """Categorize an exception into TRANSIENT or PERMANENT failure."""
        if isinstance(exc, TRANSIENT_EXCEPTIONS):
            return FailureClass.TRANSIENT

        # Check for HTTP 5xx responses (transient server errors)
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code >= 500:
                return FailureClass.TRANSIENT
            return FailureClass.PERMANENT

        if isinstance(exc, PERMANENT_EXCEPTIONS):
            return FailureClass.PERMANENT

        # Database connection operational errors are transient
        exc_str = str(exc).lower()
        if any(term in exc_str for term in ["connection refused", "timeout", "deadlock", "closed"]):
            return FailureClass.TRANSIENT

        # Fallback default: classify unknown exceptions as transient for retry up to max_attempts
        return FailureClass.TRANSIENT

    def calculate_backoff_seconds(self, attempt: int) -> float:
        """Calculate exponential backoff with bounded jitter."""
        clamped_attempt = max(1, attempt)
        raw_backoff = self.base_delay * (2 ** (clamped_attempt - 1))
        capped_backoff = min(self.max_delay, raw_backoff)

        # Apply ± jitter
        jitter_range = capped_backoff * self.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)

        return max(0.5, round(capped_backoff + jitter, 2))

    def should_retry(self, attempt: int, exc: Exception) -> bool:
        """Determine if job should be retried based on attempt count and failure class."""
        if attempt >= self.max_attempts:
            return False
        return self.classify_error(exc) == FailureClass.TRANSIENT


retry_policy = RetryPolicy()
