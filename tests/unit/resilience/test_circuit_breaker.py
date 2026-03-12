"""Tests for circuit breaker with intelligent recovery (TC-3815, CB-01..CB-04)."""

from __future__ import annotations

import logging
import time
from unittest.mock import patch

import pytest

from launcher.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    build_circuit_breaker_from_config,
)


def _make_cb(**overrides) -> CircuitBreaker:
    """Create a CircuitBreaker with test-friendly defaults."""
    defaults = dict(
        enabled=True,
        failure_threshold=3,
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
    status = cb.get_status()
    timeout = status["current_recovery_timeout_s"]
    with patch("time.time", return_value=time.time() + timeout + 1):
        cb.should_use_fallback()


class TestIsProbing:
    def test_false_when_closed(self) -> None:
        cb = _make_cb()
        assert cb.is_probing is False

    def test_false_when_open(self) -> None:
        cb = _make_cb(failure_threshold=1)
        cb.record_failure(1.0)
        assert cb.is_probing is False

    def test_true_when_half_open(self) -> None:
        cb = _make_cb(failure_threshold=1)
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)
        assert cb.is_probing is True


class TestProbeTimeout:
    def test_default_value(self) -> None:
        cb = _make_cb()
        assert cb.probe_timeout_s == 15.0

    def test_custom_value(self) -> None:
        cb = _make_cb(probe_timeout_s=25.0)
        assert cb.probe_timeout_s == 25.0


class TestBackoffProgression:
    def test_first_probe_failure_doubles_recovery(self) -> None:
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=60.0)
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)
        cb.record_failure(1.0)  # probe fails -> OPEN
        status = cb.get_status()
        assert status["current_recovery_timeout_s"] == 120.0
        assert status["probe_failures"] == 1

    def test_backoff_progression(self) -> None:
        cb = _make_cb(
            failure_threshold=1,
            recovery_timeout_s=60.0,
            recovery_backoff_factor=2.0,
            recovery_max_timeout_s=600.0,
        )
        expected = [120.0, 240.0, 480.0, 600.0, 600.0]
        cb.record_failure(1.0)  # -> OPEN

        for i, expected_timeout in enumerate(expected):
            _force_half_open(cb)
            cb.record_failure(1.0)  # probe fails -> OPEN
            status = cb.get_status()
            assert status["current_recovery_timeout_s"] == expected_timeout, (
                f"Probe failure {i + 1}: expected {expected_timeout}, "
                f"got {status['current_recovery_timeout_s']}"
            )

    def test_backoff_cap(self) -> None:
        cb = _make_cb(
            failure_threshold=1,
            recovery_timeout_s=60.0,
            recovery_backoff_factor=10.0,
            recovery_max_timeout_s=300.0,
        )
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)
        cb.record_failure(1.0)  # probe fails
        # 60 * 10^1 = 600 -> capped at 300
        status = cb.get_status()
        assert status["current_recovery_timeout_s"] == 300.0


class TestBackoffReset:
    def test_reset_on_successful_probe(self) -> None:
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=60.0)
        cb.record_failure(1.0)  # -> OPEN

        # Fail 2 probes to build up backoff
        for _ in range(2):
            _force_half_open(cb)
            cb.record_failure(1.0)

        status = cb.get_status()
        assert status["current_recovery_timeout_s"] > 60.0
        assert status["probe_failures"] == 2

        # Now succeed
        _force_half_open(cb)
        cb.record_success(1.0)  # probe succeeds -> CLOSED

        status = cb.get_status()
        assert status["state"] == "closed"
        assert status["probe_failures"] == 0
        assert status["current_recovery_timeout_s"] == 60.0


class TestGetStatus:
    def test_includes_backoff_fields(self) -> None:
        cb = _make_cb()
        status = cb.get_status()
        assert "probe_failures" in status
        assert "current_recovery_timeout_s" in status
        assert status["probe_failures"] == 0
        assert status["current_recovery_timeout_s"] == 60.0


class TestFactory:
    def test_parses_new_config_fields(self) -> None:
        cb = build_circuit_breaker_from_config(
            {
                "probe_timeout_s": 20.0,
                "recovery_backoff_factor": 3.0,
                "recovery_max_timeout_s": 900.0,
            },
            has_fallback=True,
        )
        assert cb is not None
        assert cb.probe_timeout_s == 20.0
        assert cb._config.recovery_backoff_factor == 3.0
        assert cb._config.recovery_max_timeout_s == 900.0

    def test_defaults_when_fields_missing(self) -> None:
        cb = build_circuit_breaker_from_config({}, has_fallback=True)
        assert cb is not None
        assert cb.probe_timeout_s == 15.0
        assert cb._config.recovery_backoff_factor == 2.0
        assert cb._config.recovery_max_timeout_s == 600.0

    def test_disabled_when_no_fallback(self) -> None:
        cb = build_circuit_breaker_from_config({}, has_fallback=False)
        assert cb is None


class TestConfigValidation:
    """CB-02: CircuitBreakerConfig.__post_init__ validation."""

    def test_default_config_is_valid(self) -> None:
        CircuitBreakerConfig()  # should not raise

    def test_valid_custom_config(self) -> None:
        CircuitBreakerConfig(
            probe_timeout_s=0.001,
            recovery_backoff_factor=1.0,
            recovery_max_timeout_s=60.0,
        )  # should not raise

    def test_probe_timeout_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="probe_timeout_s must be > 0"):
            CircuitBreakerConfig(probe_timeout_s=0.0)

    def test_probe_timeout_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="probe_timeout_s must be > 0"):
            CircuitBreakerConfig(probe_timeout_s=-1.0)

    def test_backoff_factor_below_one_raises(self) -> None:
        with pytest.raises(ValueError, match="recovery_backoff_factor must be >= 1.0"):
            CircuitBreakerConfig(recovery_backoff_factor=0.5)

    def test_max_timeout_below_base_raises(self) -> None:
        with pytest.raises(ValueError, match="recovery_max_timeout_s.*must be >="):
            CircuitBreakerConfig(recovery_timeout_s=120.0, recovery_max_timeout_s=60.0)

    def test_failure_threshold_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="failure_threshold must be >= 1"):
            CircuitBreakerConfig(failure_threshold=0)

    def test_window_size_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="window_size must be >= 1"):
            CircuitBreakerConfig(window_size=0)

    def test_error_rate_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="error_rate_threshold must be in"):
            CircuitBreakerConfig(error_rate_threshold=0.0)

    def test_error_rate_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="error_rate_threshold must be in"):
            CircuitBreakerConfig(error_rate_threshold=1.5)

    def test_latency_threshold_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="latency_threshold_s must be > 0"):
            CircuitBreakerConfig(latency_threshold_s=0.0)

    def test_recovery_timeout_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="recovery_timeout_s must be > 0"):
            CircuitBreakerConfig(recovery_timeout_s=0.0)


class TestFullLifecycle:
    """Full CLOSED -> OPEN -> HALF_OPEN(fail) -> OPEN(backoff) -> HALF_OPEN(succeed) -> CLOSED."""

    def test_complete_lifecycle(self) -> None:
        cb = _make_cb(failure_threshold=1, recovery_timeout_s=60.0)

        # 1. Start CLOSED
        assert cb.get_status()["state"] == "closed"

        # 2. Trip to OPEN
        cb.record_failure(1.0)
        assert cb.get_status()["state"] == "open"

        # 3. First probe fails -> OPEN with backoff
        _force_half_open(cb)
        assert cb.is_probing is True
        cb.record_failure(1.0)
        status = cb.get_status()
        assert status["state"] == "open"
        assert status["probe_failures"] == 1
        assert status["current_recovery_timeout_s"] == 120.0

        # 4. Second probe succeeds -> CLOSED, backoff reset
        _force_half_open(cb)
        assert cb.is_probing is True
        cb.record_success(0.5)
        status = cb.get_status()
        assert status["state"] == "closed"
        assert status["probe_failures"] == 0
        assert status["current_recovery_timeout_s"] == 60.0


class TestRecoveryObservability:
    """CB-03: Verify log messages on probe success and failure."""

    def test_probe_success_emits_log(self, caplog) -> None:
        cb = _make_cb(failure_threshold=1)
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)

        with caplog.at_level(logging.INFO, logger="launcher.resilience.circuit_breaker"):
            cb.record_success(0.5)

        assert any(
            "circuit_breaker_probe_succeeded" in msg for msg in caplog.messages
        ), f"Expected probe_succeeded log, got: {caplog.messages}"

    def test_probe_success_log_includes_probe_failures(self, caplog) -> None:
        cb = _make_cb(failure_threshold=1)
        cb.record_failure(1.0)  # -> OPEN

        # Fail 2 probes first
        _force_half_open(cb)
        cb.record_failure(1.0)
        _force_half_open(cb)
        cb.record_failure(1.0)

        _force_half_open(cb)
        with caplog.at_level(logging.INFO, logger="launcher.resilience.circuit_breaker"):
            cb.record_success(0.5)

        succeeded_msgs = [m for m in caplog.messages if "probe_succeeded" in m]
        assert len(succeeded_msgs) == 1
        assert "probe_failures_before_recovery=2" in succeeded_msgs[0]

    def test_probe_success_log_includes_time_on_fallback(self, caplog) -> None:
        cb = _make_cb(failure_threshold=1)
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)

        with caplog.at_level(logging.INFO, logger="launcher.resilience.circuit_breaker"):
            cb.record_success(0.5)

        succeeded_msgs = [m for m in caplog.messages if "probe_succeeded" in m]
        assert len(succeeded_msgs) == 1
        assert "time_on_fallback_s=" in succeeded_msgs[0]

    def test_probe_failure_emits_warning(self, caplog) -> None:
        cb = _make_cb(failure_threshold=1)
        cb.record_failure(1.0)  # -> OPEN
        _force_half_open(cb)

        with caplog.at_level(logging.WARNING, logger="launcher.resilience.circuit_breaker"):
            cb.record_failure(1.0)  # probe fails

        warning_msgs = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "probe_failed" in r.message
        ]
        assert len(warning_msgs) >= 1, (
            f"Expected WARNING-level probe_failed log, got: {caplog.messages}"
        )

    def test_normal_success_does_not_emit_probe_log(self, caplog) -> None:
        cb = _make_cb()

        with caplog.at_level(logging.INFO, logger="launcher.resilience.circuit_breaker"):
            cb.record_success(0.5)

        assert not any(
            "probe_succeeded" in msg for msg in caplog.messages
        ), "Should not emit probe_succeeded when circuit is CLOSED"
