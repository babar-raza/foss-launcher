"""Token-bucket rate limiter with exponential backoff.

Used by all external API calls in the SEO module (Google Trends,
Google Suggest, Gemini) to respect free-tier rate limits.

TC-3806: Created for v2 SEO module.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """Token-bucket rate limiter with exponential backoff on errors.

    Parameters
    ----------
    requests_per_minute:
        Maximum sustained request rate.
    min_interval_seconds:
        Minimum gap between consecutive requests.
    max_retries:
        Maximum retry attempts on 429/5xx before giving up.
    base_backoff_seconds:
        Initial backoff duration after a rate-limit or server error.
    max_backoff_seconds:
        Maximum backoff cap (exponential growth stops here).
    name:
        Human-readable name for logging (e.g. ``"gemini"``, ``"trends"``).
    """

    def __init__(
        self,
        requests_per_minute: int = 15,
        min_interval_seconds: float = 1.0,
        max_retries: int = 3,
        base_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 60.0,
        name: str = "api",
    ) -> None:
        self._rpm = max(requests_per_minute, 1)
        self._min_interval = min_interval_seconds
        self._max_retries = max_retries
        self._base_backoff = base_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._name = name

        self._lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._consecutive_errors: int = 0

        # Token bucket: refill rate = RPM / 60 tokens per second.
        self._tokens: float = float(self._rpm)
        self._max_tokens: float = float(self._rpm)
        self._refill_rate: float = self._rpm / 60.0
        self._last_refill_time: float = time.monotonic()

    @property
    def max_retries(self) -> int:
        """Maximum retry attempts on 429/5xx."""
        return self._max_retries

    @property
    def consecutive_errors(self) -> int:
        """Current count of consecutive errors (for testing)."""
        with self._lock:
            return self._consecutive_errors

    def acquire(self) -> None:
        """Block until a request slot is available.

        Enforces both token-bucket rate and minimum interval.
        """
        while True:
            with self._lock:
                self._refill_tokens()

                # Check minimum interval.
                now = time.monotonic()
                since_last = now - self._last_request_time
                if since_last < self._min_interval:
                    wait_interval = self._min_interval - since_last
                else:
                    wait_interval = 0.0

                # Check token availability.
                if self._tokens >= 1.0 and wait_interval <= 0:
                    self._tokens -= 1.0
                    self._last_request_time = time.monotonic()
                    return

                # Compute how long to wait for a token.
                if self._tokens < 1.0:
                    wait_token = (1.0 - self._tokens) / self._refill_rate
                else:
                    wait_token = 0.0

                wait = max(wait_interval, wait_token)

            # Sleep outside the lock.
            time.sleep(wait)

    def record_error(self, status_code: int) -> float:
        """Record an error response and return the backoff duration.

        Parameters
        ----------
        status_code:
            HTTP status code of the failed response.

        Returns
        -------
        float
            Recommended backoff duration in seconds.  Zero for non-retryable errors.
        """
        with self._lock:
            if status_code in (429, 500, 502, 503, 504):
                self._consecutive_errors += 1
                backoff = min(
                    self._base_backoff * (2 ** (self._consecutive_errors - 1)),
                    self._max_backoff,
                )
                logger.warning(
                    "[%s] Error %d (attempt %d/%d), backoff %.1fs",
                    self._name, status_code,
                    self._consecutive_errors, self._max_retries,
                    backoff,
                )
                return backoff
            else:
                logger.warning(
                    "[%s] Non-retryable error %d", self._name, status_code,
                )
                return 0.0

    def record_success(self) -> None:
        """Reset consecutive error count after a successful request."""
        with self._lock:
            if self._consecutive_errors > 0:
                logger.debug(
                    "[%s] Success after %d consecutive errors, resetting backoff",
                    self._name, self._consecutive_errors,
                )
            self._consecutive_errors = 0

    def should_retry(self, status_code: int) -> bool:
        """Return whether a request with this status code should be retried.

        Parameters
        ----------
        status_code:
            HTTP status code.

        Returns
        -------
        bool
            True if retryable AND under max_retries.
        """
        with self._lock:
            if status_code not in (429, 500, 502, 503, 504):
                return False
            return self._consecutive_errors < self._max_retries

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time.  Must hold ``_lock``."""
        now = time.monotonic()
        elapsed = now - self._last_refill_time
        self._tokens = min(
            self._max_tokens,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill_time = now


# ------------------------------------------------------------------
# Pre-configured rate limiters for known APIs
# ------------------------------------------------------------------


def create_trends_limiter() -> APIRateLimiter:
    """Rate limiter for Google Trends (PyTrends) API."""
    return APIRateLimiter(
        requests_per_minute=10,
        min_interval_seconds=1.5,
        max_retries=3,
        base_backoff_seconds=2.0,
        max_backoff_seconds=60.0,
        name="trends",
    )


def create_suggest_limiter() -> APIRateLimiter:
    """Rate limiter for Google Suggest API."""
    return APIRateLimiter(
        requests_per_minute=30,
        min_interval_seconds=0.5,
        max_retries=3,
        base_backoff_seconds=1.0,
        max_backoff_seconds=60.0,
        name="suggest",
    )


def create_gemini_limiter() -> APIRateLimiter:
    """Rate limiter for Google Gemini free tier."""
    return APIRateLimiter(
        requests_per_minute=15,
        min_interval_seconds=1.0,
        max_retries=3,
        base_backoff_seconds=2.0,
        max_backoff_seconds=60.0,
        name="gemini",
    )
