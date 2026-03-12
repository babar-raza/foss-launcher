"""Tests for launcher.shared.api_rate_limiter."""

from __future__ import annotations

import time

import pytest

from launcher.shared.api_rate_limiter import (
    APIRateLimiter,
    create_gemini_limiter,
    create_suggest_limiter,
    create_trends_limiter,
)


@pytest.fixture()
def limiter() -> APIRateLimiter:
    return APIRateLimiter(
        requests_per_minute=60,  # 1 per second for easy testing
        min_interval_seconds=0.05,
        max_retries=3,
        base_backoff_seconds=0.1,
        max_backoff_seconds=1.0,
        name="test",
    )


# ------------------------------------------------------------------
# Basic acquire
# ------------------------------------------------------------------


class TestAcquire:
    def test_first_acquire_succeeds(self, limiter: APIRateLimiter) -> None:
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        # Should be near-instant.
        assert elapsed < 0.5

    def test_multiple_acquires_respect_min_interval(self) -> None:
        lim = APIRateLimiter(
            requests_per_minute=600,
            min_interval_seconds=0.1,
            name="interval_test",
        )
        lim.acquire()
        start = time.monotonic()
        lim.acquire()
        elapsed = time.monotonic() - start
        # Should wait at least min_interval.
        assert elapsed >= 0.08  # Allow small timing margin

    def test_burst_within_bucket(self) -> None:
        lim = APIRateLimiter(
            requests_per_minute=60,
            min_interval_seconds=0.0,  # No min interval
            name="burst_test",
        )
        # Should be able to acquire up to bucket size without blocking.
        start = time.monotonic()
        for _ in range(5):
            lim.acquire()
        elapsed = time.monotonic() - start
        # All within the token bucket; should be very fast.
        assert elapsed < 1.0


# ------------------------------------------------------------------
# Error recording and backoff
# ------------------------------------------------------------------


class TestErrorRecording:
    def test_429_triggers_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(429)
        assert backoff > 0
        assert limiter.consecutive_errors == 1

    def test_500_triggers_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(500)
        assert backoff > 0

    def test_502_triggers_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(502)
        assert backoff > 0

    def test_503_triggers_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(503)
        assert backoff > 0

    def test_504_triggers_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(504)
        assert backoff > 0

    def test_400_no_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(400)
        assert backoff == 0.0

    def test_404_no_backoff(self, limiter: APIRateLimiter) -> None:
        backoff = limiter.record_error(404)
        assert backoff == 0.0

    def test_exponential_growth(self, limiter: APIRateLimiter) -> None:
        b1 = limiter.record_error(429)
        b2 = limiter.record_error(429)
        b3 = limiter.record_error(429)
        # Each should be double the previous (0.1, 0.2, 0.4).
        assert b2 > b1
        assert b3 > b2

    def test_backoff_capped(self, limiter: APIRateLimiter) -> None:
        for _ in range(20):
            backoff = limiter.record_error(429)
        assert backoff <= limiter._max_backoff


# ------------------------------------------------------------------
# Success recording
# ------------------------------------------------------------------


class TestSuccessRecording:
    def test_resets_consecutive_errors(self, limiter: APIRateLimiter) -> None:
        limiter.record_error(429)
        limiter.record_error(429)
        assert limiter.consecutive_errors == 2

        limiter.record_success()
        assert limiter.consecutive_errors == 0

    def test_success_without_errors(self, limiter: APIRateLimiter) -> None:
        # Should not crash.
        limiter.record_success()
        assert limiter.consecutive_errors == 0

    def test_backoff_resets_after_success(self, limiter: APIRateLimiter) -> None:
        limiter.record_error(429)
        limiter.record_error(429)
        limiter.record_success()

        # Next error should start from base backoff.
        backoff = limiter.record_error(429)
        assert backoff == limiter._base_backoff


# ------------------------------------------------------------------
# should_retry
# ------------------------------------------------------------------


class TestShouldRetry:
    def test_retryable_status_codes(self, limiter: APIRateLimiter) -> None:
        for code in (429, 500, 502, 503, 504):
            assert limiter.should_retry(code) is True

    def test_non_retryable_status_codes(self, limiter: APIRateLimiter) -> None:
        for code in (400, 401, 403, 404, 422):
            assert limiter.should_retry(code) is False

    def test_exceeds_max_retries(self, limiter: APIRateLimiter) -> None:
        for _ in range(limiter.max_retries):
            limiter.record_error(429)
        assert limiter.should_retry(429) is False

    def test_under_max_retries(self, limiter: APIRateLimiter) -> None:
        limiter.record_error(429)
        assert limiter.should_retry(429) is True


# ------------------------------------------------------------------
# Factory functions
# ------------------------------------------------------------------


class TestFactories:
    def test_trends_limiter(self) -> None:
        lim = create_trends_limiter()
        assert lim._rpm == 10
        assert lim._min_interval == 1.5
        assert lim._name == "trends"

    def test_suggest_limiter(self) -> None:
        lim = create_suggest_limiter()
        assert lim._rpm == 30
        assert lim._min_interval == 0.5
        assert lim._name == "suggest"

    def test_gemini_limiter(self) -> None:
        lim = create_gemini_limiter()
        assert lim._rpm == 15
        assert lim._min_interval == 1.0
        assert lim._name == "gemini"


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestProperties:
    def test_max_retries_property(self, limiter: APIRateLimiter) -> None:
        assert limiter.max_retries == 3

    def test_consecutive_errors_property(self, limiter: APIRateLimiter) -> None:
        assert limiter.consecutive_errors == 0
        limiter.record_error(429)
        assert limiter.consecutive_errors == 1
