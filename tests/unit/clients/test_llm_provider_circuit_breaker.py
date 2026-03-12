"""Integration tests: LLMProviderClient + CircuitBreaker probe timeout (CB-01).

Validates that the LLM provider uses the shorter probe timeout when the
circuit breaker is in HALF_OPEN state, and the normal timeout otherwise.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.clients.llm_provider import LLMProviderClient, LLMError
from launcher.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
)


def _make_provider(tmp_path: Path, cb: CircuitBreaker | None = None) -> LLMProviderClient:
    """Create a minimal LLMProviderClient with optional circuit breaker."""
    return LLMProviderClient(
        api_base_url="http://test-primary:8000/v1",
        model="test-model",
        run_dir=tmp_path,
        api_key="test-key",
        timeout=120,
        fallback_api_base_url="http://test-fallback:8000/v1",
        fallback_model="test-fallback-model",
        fallback_api_key="test-fb-key",
        fallback_timeout=120,
        circuit_breaker=cb,
    )


def _ok_response(content: str = "ok") -> dict:
    """Minimal valid OpenAI-compatible response."""
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


def _make_cb(**overrides) -> CircuitBreaker:
    defaults = dict(
        enabled=True,
        failure_threshold=1,
        error_rate_threshold=0.5,
        window_size=10,
        latency_threshold_s=30.0,
        recovery_timeout_s=60.0,
        probe_timeout_s=15.0,
        recovery_backoff_factor=2.0,
        recovery_max_timeout_s=600.0,
    )
    defaults.update(overrides)
    return CircuitBreaker(CircuitBreakerConfig(**defaults))


def _force_half_open(cb: CircuitBreaker) -> None:
    """Advance a circuit in OPEN state to HALF_OPEN via time mock."""
    timeout = cb.get_status()["current_recovery_timeout_s"]
    with patch("time.time", return_value=time.time() + timeout + 1):
        cb.should_use_fallback()


class TestProbeTimeoutUsed:
    """Verify _call_api receives probe_timeout_s when circuit is HALF_OPEN."""

    def test_half_open_uses_probe_timeout(self, tmp_path: Path) -> None:
        cb = _make_cb()
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)
        assert cb.is_probing is True

        provider = _make_provider(tmp_path, cb=cb)

        with (
            patch.object(provider, "_call_api", return_value=_ok_response()) as mock_api,
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val,
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "probe"}])

        mock_api.assert_called_once()
        actual_timeout = mock_api.call_args.kwargs["timeout"]
        assert actual_timeout == 15.0, f"Expected probe timeout 15.0, got {actual_timeout}"

    def test_closed_uses_normal_timeout(self, tmp_path: Path) -> None:
        cb = _make_cb()
        assert cb.is_probing is False

        provider = _make_provider(tmp_path, cb=cb)

        with (
            patch.object(provider, "_call_api", return_value=_ok_response()) as mock_api,
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val,
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "normal"}])

        actual_timeout = mock_api.call_args.kwargs["timeout"]
        assert actual_timeout == 120, f"Expected normal timeout 120, got {actual_timeout}"

    def test_no_circuit_breaker_uses_normal_timeout(self, tmp_path: Path) -> None:
        provider = _make_provider(tmp_path, cb=None)

        with (
            patch.object(provider, "_call_api", return_value=_ok_response()) as mock_api,
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val,
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "no cb"}])

        actual_timeout = mock_api.call_args.kwargs["timeout"]
        assert actual_timeout == 120, f"Expected normal timeout 120, got {actual_timeout}"


class TestProbeRecoveryLifecycle:
    """Full lifecycle: CLOSED -> OPEN -> HALF_OPEN (probe) -> CLOSED."""

    def test_successful_probe_recovers_circuit(self, tmp_path: Path) -> None:
        cb = _make_cb()
        provider = _make_provider(tmp_path, cb=cb)

        # Step 1: Trip to OPEN via failure
        cb.record_failure(1.0)
        assert cb.get_status()["state"] == "open"

        # Step 2: Advance past recovery timeout -> HALF_OPEN
        _force_half_open(cb)
        assert cb.is_probing is True

        # Step 3: Probe succeeds
        with (
            patch.object(provider, "_call_api", return_value=_ok_response()) as mock_api,
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val,
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "probe"}])

        # Circuit should be CLOSED now
        assert cb.get_status()["state"] == "closed"
        assert cb.get_status()["probe_failures"] == 0

        # Step 4: Next call uses normal timeout
        with (
            patch.object(provider, "_call_api", return_value=_ok_response()) as mock_api2,
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val2,
        ):
            mock_val2.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "after recovery"}])

        actual_timeout = mock_api2.call_args.kwargs["timeout"]
        assert actual_timeout == 120

    def test_failed_probe_increases_backoff(self, tmp_path: Path) -> None:
        cb = _make_cb()
        provider = _make_provider(tmp_path, cb=cb)

        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)
        assert cb.is_probing is True

        # Probe fails (primary throws timeout)
        with (
            patch.object(
                provider, "_call_api", side_effect=ConnectionError("timeout")
            ),
            patch.object(
                provider, "_call_endpoint", return_value=_ok_response()
            ),
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val,
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "probe fail"}])

        # Circuit should be OPEN with increased backoff
        status = cb.get_status()
        assert status["state"] == "open"
        assert status["probe_failures"] == 1
        assert status["current_recovery_timeout_s"] == 120.0  # 60 * 2^1


class TestCustomProbeTimeout:
    """Verify custom probe_timeout_s flows through config -> provider."""

    def test_custom_probe_timeout_value(self, tmp_path: Path) -> None:
        cb = _make_cb(probe_timeout_s=25.0)
        cb.record_failure(1.0)
        _force_half_open(cb)
        provider = _make_provider(tmp_path, cb=cb)

        with (
            patch.object(provider, "_call_api", return_value=_ok_response()) as mock_api,
            patch("launcher.clients.llm_provider.validate_llm_response") as mock_val,
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            provider.chat_completion([{"role": "user", "content": "custom"}])

        actual_timeout = mock_api.call_args.kwargs["timeout"]
        assert actual_timeout == 25.0
