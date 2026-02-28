"""Tests for circuit_breaker.py — passive circuit breaker for LLM endpoints.

TC-3590: Verifies the CircuitBreaker state machine (CLOSED → OPEN → HALF_OPEN → CLOSED),
flakiness detection triggers (consecutive failures, error rate, latency), thread safety,
config factory, and integration with LLMProviderClient.

All tests are self-contained (no network calls, no disk I/O beyond tmp_path).
"""

from __future__ import annotations

import threading
import time
from unittest.mock import Mock, patch

import pytest

from launch.resilience.circuit_breaker import (
    CallRecord,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    build_circuit_breaker_from_config,
)
from launch.clients.llm_provider import LLMError, LLMProviderClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MESSAGES = [{"role": "user", "content": "test prompt"}]


def _make_config(**kwargs) -> CircuitBreakerConfig:
    """Build a CircuitBreakerConfig with overrideable defaults."""
    defaults = dict(
        enabled=True,
        failure_threshold=3,
        error_rate_threshold=0.5,
        window_size=10,
        latency_threshold_s=30.0,
        recovery_timeout_s=60.0,
    )
    defaults.update(kwargs)
    return CircuitBreakerConfig(**defaults)


def _make_cb(**kwargs) -> CircuitBreaker:
    """Build a CircuitBreaker with overrideable config defaults."""
    return CircuitBreaker(_make_config(**kwargs))


def _make_success_response(
    content: str = "Hello world. This is a valid response from the LLM endpoint.",
) -> Mock:
    """Create a mock successful HTTP response that passes L1 validation."""
    # Pad short content to pass the L1 minimum-length check (50 chars).
    padded = content if len(content.rstrip()) >= 50 else content.rstrip() + " (padding)" * 5
    padded = padded[:200]
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"content": padded},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }
    return response


# ---------------------------------------------------------------------------
# Class 1: State Transitions — CLOSED → OPEN
# ---------------------------------------------------------------------------


class TestClosedToOpen:
    """Verify triggers that move from CLOSED → OPEN."""

    def test_consecutive_failures_open_circuit(self):
        """CLOSED → OPEN after failure_threshold consecutive failures."""
        cb = _make_cb(failure_threshold=3)
        assert cb._state == CircuitState.CLOSED

        cb.record_failure(1.0)
        cb.record_failure(1.0)
        assert cb._state == CircuitState.CLOSED  # not yet

        cb.record_failure(1.0)
        assert cb._state == CircuitState.OPEN

    def test_error_rate_threshold_opens_circuit(self):
        """CLOSED → OPEN when error rate exceeds threshold in window."""
        cb = _make_cb(
            failure_threshold=100,  # disable consecutive threshold
            error_rate_threshold=0.5,
            window_size=6,
        )
        # 4 failures out of 6 calls = 67% > 50%
        cb.record_success(1.0)
        cb.record_success(1.0)
        cb.record_failure(1.0)
        cb.record_failure(1.0)
        cb.record_failure(1.0)
        # window has 5 items (3 failures / 5 = 60% > 50%), min_data = max(2, 3) = 3
        cb.record_failure(1.0)  # 4/6 = 67%
        assert cb._state == CircuitState.OPEN

    def test_latency_threshold_opens_circuit(self):
        """CLOSED → OPEN when average latency exceeds threshold."""
        cb = _make_cb(
            failure_threshold=100,  # disable
            error_rate_threshold=1.0,  # disable
            latency_threshold_s=10.0,
            window_size=4,
        )
        # Two high-latency failures → avg = 17.5s > 10s
        cb.record_failure(15.0)
        cb.record_failure(20.0)
        assert cb._state == CircuitState.OPEN

    def test_success_resets_consecutive_failures(self):
        """A success resets consecutive_failures, preventing premature OPEN."""
        cb = _make_cb(
            failure_threshold=3,
            error_rate_threshold=1.0,  # disable error rate (test consecutive only)
            latency_threshold_s=9999.0,  # disable latency
        )
        cb.record_failure(1.0)
        cb.record_failure(1.0)
        cb.record_success(1.0)  # reset
        cb.record_failure(1.0)
        cb.record_failure(1.0)
        assert cb._state == CircuitState.CLOSED  # only 2 consecutive after reset

    def test_closed_should_use_fallback_is_false(self):
        """In CLOSED state, should_use_fallback returns False."""
        cb = _make_cb()
        assert cb.should_use_fallback() is False


# ---------------------------------------------------------------------------
# Class 2: State Transitions — OPEN → HALF_OPEN → CLOSED/OPEN
# ---------------------------------------------------------------------------


class TestOpenRecovery:
    """Verify recovery transitions: OPEN → HALF_OPEN → CLOSED/OPEN."""

    def test_open_to_half_open_after_timeout(self):
        """OPEN → HALF_OPEN after recovery_timeout_s elapses."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=0.01)
        cb.record_failure(1.0)
        assert cb._state == CircuitState.OPEN

        time.sleep(0.02)  # wait out timeout
        result = cb.should_use_fallback()
        assert cb._state == CircuitState.HALF_OPEN
        assert result is False  # probe call goes to primary

    def test_open_stays_open_before_timeout(self):
        """OPEN remains OPEN before recovery_timeout_s elapses."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=9999.0)
        cb.record_failure(1.0)
        assert cb._state == CircuitState.OPEN

        result = cb.should_use_fallback()
        assert cb._state == CircuitState.OPEN
        assert result is True

    def test_half_open_success_closes_circuit(self):
        """HALF_OPEN + success → CLOSED (window cleared, counters reset)."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=0.01)
        cb.record_failure(1.0)
        time.sleep(0.02)
        cb.should_use_fallback()  # triggers HALF_OPEN
        assert cb._state == CircuitState.HALF_OPEN

        cb.record_success(1.0)  # probe succeeds
        assert cb._state == CircuitState.CLOSED
        assert cb._consecutive_failures == 0
        assert len(cb._window) == 0  # window cleared on CLOSED

    def test_half_open_failure_reopens_circuit(self):
        """HALF_OPEN + failure → OPEN (timer reset)."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=0.01)
        cb.record_failure(1.0)
        time.sleep(0.02)
        cb.should_use_fallback()  # triggers HALF_OPEN
        assert cb._state == CircuitState.HALF_OPEN

        open_since_before = cb._open_since
        time.sleep(0.01)
        cb.record_failure(1.0)  # probe fails
        assert cb._state == CircuitState.OPEN
        assert cb._open_since > open_since_before  # timer reset


# ---------------------------------------------------------------------------
# Class 3: Metrics — Error Rate and Latency Calculations
# ---------------------------------------------------------------------------


class TestMetrics:
    """Verify pure metric computations."""

    def test_error_rate_empty_window(self):
        assert CircuitBreaker._error_rate([]) == 0.0

    def test_avg_latency_empty_window(self):
        assert CircuitBreaker._avg_latency([]) == 0.0

    def test_error_rate_all_success(self):
        window = [CallRecord(success=True, latency_s=1.0, timestamp=0.0)] * 5
        assert CircuitBreaker._error_rate(window) == 0.0

    def test_error_rate_all_failures(self):
        window = [CallRecord(success=False, latency_s=1.0, timestamp=0.0)] * 5
        assert CircuitBreaker._error_rate(window) == 1.0

    def test_avg_latency_calculation(self):
        window = [
            CallRecord(success=True, latency_s=10.0, timestamp=0.0),
            CallRecord(success=True, latency_s=20.0, timestamp=0.0),
            CallRecord(success=True, latency_s=30.0, timestamp=0.0),
        ]
        assert CircuitBreaker._avg_latency(window) == pytest.approx(20.0)

    def test_window_size_enforced(self):
        """Rolling window does not exceed configured window_size."""
        cb = _make_cb(window_size=5, failure_threshold=100)
        for _ in range(20):
            cb.record_success(1.0)
        assert len(cb._window) == 5

    def test_get_status_returns_snapshot(self):
        """get_status returns a dict with all expected keys."""
        cb = _make_cb(failure_threshold=100)
        cb.record_success(2.0)
        cb.record_failure(5.0)
        status = cb.get_status()
        assert status["state"] == "closed"
        assert status["consecutive_failures"] == 1
        assert status["window_size"] == 2
        assert status["window_capacity"] == 10
        assert status["open_since"] is None
        assert status["error_rate"] == pytest.approx(0.5)
        assert status["avg_latency_s"] == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Class 4: Thread Safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Verify concurrent access does not corrupt state."""

    def test_concurrent_record_calls_do_not_race(self):
        """Multiple threads recording results simultaneously do not corrupt state."""
        cb = _make_cb(failure_threshold=1000, window_size=100)
        errors = []

        def worker(success: bool):
            try:
                for _ in range(50):
                    if success:
                        cb.record_success(0.5)
                    else:
                        cb.record_failure(0.5)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i % 2 == 0,))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(cb._window) <= 100

    def test_concurrent_should_use_fallback_is_safe(self):
        """should_use_fallback() is safe under concurrent access."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=9999.0)
        cb.record_failure(1.0)  # OPEN

        results = []
        errors = []

        def check():
            try:
                results.append(cb.should_use_fallback())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(r is True for r in results)  # all see OPEN


# ---------------------------------------------------------------------------
# Class 5: Configuration and Factory
# ---------------------------------------------------------------------------


class TestBuildFromConfig:
    """Verify build_circuit_breaker_from_config factory."""

    def test_disabled_when_no_fallback(self):
        """Circuit breaker is None when has_fallback=False and no explicit config."""
        cb = build_circuit_breaker_from_config({}, has_fallback=False)
        assert cb is None

    def test_enabled_when_fallback_configured(self):
        """Circuit breaker created automatically when has_fallback=True."""
        cb = build_circuit_breaker_from_config({}, has_fallback=True)
        assert cb is not None
        assert cb._state == CircuitState.CLOSED

    def test_explicit_disable_overrides_fallback(self):
        """enabled=false in config overrides has_fallback=True."""
        cb = build_circuit_breaker_from_config({"enabled": False}, has_fallback=True)
        assert cb is None

    def test_explicit_enable_without_fallback(self):
        """enabled=true in config overrides has_fallback=False."""
        cb = build_circuit_breaker_from_config({"enabled": True}, has_fallback=False)
        assert cb is not None

    def test_config_values_propagate(self):
        """Custom thresholds are applied from config dict."""
        cb = build_circuit_breaker_from_config(
            {
                "failure_threshold": 7,
                "error_rate_threshold": 0.3,
                "latency_threshold_s": 45.0,
                "recovery_timeout_s": 120.0,
                "window_size": 20,
            },
            has_fallback=True,
        )
        assert cb._config.failure_threshold == 7
        assert cb._config.error_rate_threshold == pytest.approx(0.3)
        assert cb._config.latency_threshold_s == pytest.approx(45.0)
        assert cb._config.recovery_timeout_s == pytest.approx(120.0)
        assert cb._config.window_size == 20


# ---------------------------------------------------------------------------
# Class 6: Integration with LLMProviderClient
# ---------------------------------------------------------------------------


class TestLLMProviderClientIntegration:
    """Verify circuit breaker wiring inside LLMProviderClient."""

    @patch("launch.clients.llm_provider.http_post")
    def test_open_circuit_skips_primary_uses_fallback(self, mock_http_post, tmp_path):
        """When circuit is OPEN, primary is never called; fallback is used directly."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=9999.0)
        cb.record_failure(5.0)  # force OPEN
        assert cb._state == CircuitState.OPEN

        mock_http_post.return_value = _make_success_response(
            "fallback content from local ollama model response okay"
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
            circuit_breaker=cb,
        )

        result = client.chat_completion(MESSAGES, call_id="test_cb_open")
        assert result["endpoint_used"] == "fallback"

        # Primary URL must NOT have been called
        for call in mock_http_post.call_args_list:
            url = call[0][0]
            assert "primary.example.com" not in url, (
                f"Primary was called when circuit OPEN: {url}"
            )

    @patch("launch.clients.llm_provider.http_post")
    def test_closed_circuit_uses_primary(self, mock_http_post, tmp_path):
        """When circuit is CLOSED, primary is used normally."""
        cb = _make_cb(failure_threshold=100)
        mock_http_post.return_value = _make_success_response(
            "primary content from the remote LLM endpoint response okay"
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
            circuit_breaker=cb,
        )

        result = client.chat_completion(MESSAGES, call_id="test_cb_closed")
        assert result["endpoint_used"] == "primary"

        # Primary URL was called
        primary_calls = [
            c
            for c in mock_http_post.call_args_list
            if "primary.example.com" in c[0][0]
        ]
        assert len(primary_calls) == 1

    @patch("launch.clients.llm_provider.http_post")
    def test_no_circuit_breaker_preserves_behavior(self, mock_http_post, tmp_path):
        """circuit_breaker=None preserves original reactive fallback behavior."""
        mock_http_post.side_effect = [
            ConnectionError("Primary down"),
            _make_success_response(
                "fallback ok response from the local ollama model response okay"
            ),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
            circuit_breaker=None,
        )

        result = client.chat_completion(MESSAGES, call_id="test_no_cb")
        assert result["endpoint_used"] == "fallback"
        assert mock_http_post.call_count == 2  # primary + fallback

    @patch("launch.clients.llm_provider.http_post")
    def test_primary_failure_recorded_trips_circuit(self, mock_http_post, tmp_path):
        """Transient primary failures are recorded; circuit opens after threshold."""
        cb = _make_cb(failure_threshold=2, recovery_timeout_s=9999.0)

        mock_http_post.side_effect = [
            # Call 1: primary fails, fallback ok
            ConnectionError("primary fail 1"),
            _make_success_response(
                "fallback 1 response from the local ollama model output okay"
            ),
            # Call 2: primary fails, fallback ok
            ConnectionError("primary fail 2"),
            _make_success_response(
                "fallback 2 response from the local ollama model output okay"
            ),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
            circuit_breaker=cb,
        )

        client.chat_completion(MESSAGES, call_id="test_rec_1")
        assert cb._state == CircuitState.CLOSED  # 1 failure, threshold=2

        client.chat_completion(MESSAGES, call_id="test_rec_2")
        assert cb._state == CircuitState.OPEN  # 2 failures → OPEN

    @patch("launch.clients.llm_provider.http_post")
    def test_open_circuit_no_fallback_tries_primary(self, mock_http_post, tmp_path):
        """When circuit OPEN but no fallback configured: warn and try primary."""
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=9999.0)
        cb.record_failure(5.0)  # force OPEN

        mock_http_post.return_value = _make_success_response(
            "primary response even though circuit is open no fallback ok"
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url=None,  # no fallback
            circuit_breaker=cb,
        )

        result = client.chat_completion(MESSAGES, call_id="test_no_fb_cb_open")
        # Circuit OPEN but no fallback → must still try primary
        assert result["endpoint_used"] == "primary"
