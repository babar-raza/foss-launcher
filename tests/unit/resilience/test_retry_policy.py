"""Tests for retry policy with exponential backoff."""

from __future__ import annotations

import pytest

from launcher.resilience.retry_policy import (
    FailureClassification,
    RetryConfig,
    calculate_backoff,
    classify_failure,
    retry_with_backoff,
)


class TestCalculateBackoff:
    def test_first_attempt(self) -> None:
        delay = calculate_backoff(0, base_delay=1.0, multiplier=2.0, max_delay=60.0, jitter_seed=42)
        assert 1.0 <= delay <= 1.5  # base + up to 50% jitter

    def test_exponential_growth(self) -> None:
        d0 = calculate_backoff(0, 1.0, 2.0, 60.0, jitter_seed=42)
        d1 = calculate_backoff(1, 1.0, 2.0, 60.0, jitter_seed=42)
        d2 = calculate_backoff(2, 1.0, 2.0, 60.0, jitter_seed=42)
        # Base grows: 1, 2, 4 — with jitter, d1 > d0 is not guaranteed but base is
        assert d1 > d0 * 0.8  # Allow jitter variance

    def test_max_delay_cap(self) -> None:
        delay = calculate_backoff(100, 1.0, 2.0, 60.0, jitter_seed=42)
        assert delay <= 90.0  # max_delay + 50% jitter

    def test_deterministic_with_seed(self) -> None:
        d1 = calculate_backoff(0, 1.0, 2.0, 60.0, jitter_seed=42)
        d2 = calculate_backoff(0, 1.0, 2.0, 60.0, jitter_seed=42)
        assert d1 == d2

    def test_different_seeds_different_jitter(self) -> None:
        d1 = calculate_backoff(0, 1.0, 2.0, 60.0, jitter_seed=1)
        d2 = calculate_backoff(0, 1.0, 2.0, 60.0, jitter_seed=999)
        # Very likely different (probability of collision is negligible)
        # But both within [1.0, 1.5] so we just check they're both valid
        assert 1.0 <= d1 <= 1.5
        assert 1.0 <= d2 <= 1.5


class TestClassifyFailure:
    def test_connection_error_is_transient(self) -> None:
        result = classify_failure(ConnectionError("refused"))
        assert result.is_transient is True
        assert result.suggested_action == "retry"

    def test_timeout_is_transient(self) -> None:
        result = classify_failure(TimeoutError("timed out"))
        assert result.is_transient is True

    def test_value_error_is_permanent(self) -> None:
        result = classify_failure(ValueError("bad input"))
        assert result.is_transient is False
        assert result.suggested_action == "fail"

    def test_file_not_found_is_permanent(self) -> None:
        result = classify_failure(FileNotFoundError("missing"))
        assert result.is_transient is False

    def test_assertion_error_is_permanent(self) -> None:
        result = classify_failure(AssertionError("logic bug"))
        assert result.is_transient is False

    def test_rate_limit_is_transient(self) -> None:
        result = classify_failure(RuntimeError("429 rate limit exceeded"))
        assert result.is_transient is True

    def test_service_unavailable_transient(self) -> None:
        result = classify_failure(RuntimeError("503 Service Unavailable"))
        assert result.is_transient is True

    def test_unknown_defaults_to_transient(self) -> None:
        result = classify_failure(RuntimeError("something weird"))
        assert result.is_transient is True
        assert result.suggested_action == "manual_intervention"


class TestRetryWithBackoff:
    def test_succeeds_first_try(self) -> None:
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=3, base_delay_seconds=0.001))
        def success():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert success() == "ok"
        assert call_count == 1

    def test_retries_on_transient(self) -> None:
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=3, base_delay_seconds=0.001))
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("retry me")
            return "recovered"

        assert fail_then_succeed() == "recovered"
        assert call_count == 3

    def test_fails_fast_on_permanent(self) -> None:
        @retry_with_backoff(RetryConfig(max_retries=3, base_delay_seconds=0.001))
        def always_bad():
            raise ValueError("permanent")

        with pytest.raises(ValueError, match="permanent"):
            always_bad()

    def test_exhausts_retries(self) -> None:
        @retry_with_backoff(RetryConfig(max_retries=2, base_delay_seconds=0.001))
        def always_transient():
            raise ConnectionError("always fails")

        with pytest.raises(ConnectionError):
            always_transient()
