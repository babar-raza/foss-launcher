"""Passive circuit breaker for LLM endpoint health monitoring.

Monitors primary LLM endpoint health across calls (latency, error rate,
consecutive failures) and proactively routes to the configured fallback when the
primary is detected as flaky.

Binding contract:
- specs/25_frameworks_and_dependencies.md (LLM provider integration)
- specs/28_coordination_and_handoffs.md (resilience and retry policy)

NO background threads.  State advances only on call results.
Thread-safe via threading.RLock (supports re-entry from same thread).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, Dict, NamedTuple, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    """Circuit breaker state machine states."""

    CLOSED = "closed"       # Normal: calls go to primary endpoint
    OPEN = "open"           # Flaky detected: calls go to fallback directly
    HALF_OPEN = "half_open"  # Recovery probe: one call to primary to test


class CallRecord(NamedTuple):
    """Immutable record of a single LLM call result."""

    success: bool
    latency_s: float
    timestamp: float  # time.time()


@dataclass
class CircuitBreakerConfig:
    """Configuration for the circuit breaker.

    All thresholds are calibrated for LLM workloads where:
    - Calls are expensive (10-120s each)
    - Failures cluster (endpoint goes down for minutes, not seconds)
    - Latency > 30s is genuinely unacceptable (blocks pipeline)
    """

    enabled: bool = True
    failure_threshold: int = 3          # consecutive failures to trip -> OPEN
    error_rate_threshold: float = 0.5   # >50% error rate in window -> OPEN
    window_size: int = 10               # rolling window for error rate
    latency_threshold_s: float = 30.0   # avg latency above this -> OPEN
    recovery_timeout_s: float = 60.0    # seconds in OPEN before HALF_OPEN probe
    probe_timeout_s: float = 15.0       # shorter timeout for HALF_OPEN probe calls
    recovery_backoff_factor: float = 2.0   # multiplier for recovery interval after failed probe
    recovery_max_timeout_s: float = 600.0  # cap on backoff (10 minutes)

    def __post_init__(self) -> None:
        """Validate config values at construction time."""
        if self.failure_threshold < 1:
            raise ValueError(
                f"failure_threshold must be >= 1, got {self.failure_threshold}"
            )
        if self.window_size < 1:
            raise ValueError(
                f"window_size must be >= 1, got {self.window_size}"
            )
        if not (0.0 < self.error_rate_threshold <= 1.0):
            raise ValueError(
                f"error_rate_threshold must be in (0, 1], got {self.error_rate_threshold}"
            )
        if self.latency_threshold_s <= 0:
            raise ValueError(
                f"latency_threshold_s must be > 0, got {self.latency_threshold_s}"
            )
        if self.recovery_timeout_s <= 0:
            raise ValueError(
                f"recovery_timeout_s must be > 0, got {self.recovery_timeout_s}"
            )
        if self.probe_timeout_s <= 0:
            raise ValueError(
                f"probe_timeout_s must be > 0, got {self.probe_timeout_s}"
            )
        if self.recovery_backoff_factor < 1.0:
            raise ValueError(
                f"recovery_backoff_factor must be >= 1.0, got {self.recovery_backoff_factor}"
            )
        if self.recovery_max_timeout_s < self.recovery_timeout_s:
            raise ValueError(
                f"recovery_max_timeout_s ({self.recovery_max_timeout_s}) must be >= "
                f"recovery_timeout_s ({self.recovery_timeout_s})"
            )


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Passive circuit breaker for a single LLM endpoint pair.

    Usage pattern::

        if cb.should_use_fallback():
            # route to fallback directly
        else:
            try:
                result = call_primary()
                cb.record_success(latency_s)
            except TransientError:
                cb.record_failure(latency_s)
                # existing reactive fallback follows

    Thread-safe: all state mutations are under ``self._lock`` (RLock).
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._open_since: Optional[float] = None
        self._window: Deque[CallRecord] = deque(maxlen=config.window_size)
        self._probe_failures: int = 0
        self._current_recovery_timeout: float = config.recovery_timeout_s
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_use_fallback(self) -> bool:
        """Return True if calls should be routed to fallback instead of primary.

        Called BEFORE each primary attempt.  Thread-safe.
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check recovery timeout
                if (
                    self._open_since is not None
                    and (time.time() - self._open_since)
                    >= self._current_recovery_timeout
                ):
                    self._transition_to(CircuitState.HALF_OPEN)
                    return False  # let the probe call through to primary
                return True  # still OPEN -- use fallback

            if self._state == CircuitState.HALF_OPEN:
                return False  # probe call goes to primary

            return False  # CLOSED -- normal routing

    @property
    def is_probing(self) -> bool:
        """Return True if the circuit is in HALF_OPEN (current call is a probe)."""
        with self._lock:
            return self._state == CircuitState.HALF_OPEN

    @property
    def probe_timeout_s(self) -> float:
        """Return the configured probe timeout for HALF_OPEN calls."""
        return self._config.probe_timeout_s

    def record_success(self, latency_s: float) -> None:
        """Record a successful primary endpoint call.

        Also handles HALF_OPEN -> CLOSED transition.
        """
        with self._lock:
            record = CallRecord(
                success=True, latency_s=latency_s, timestamp=time.time()
            )
            self._window.append(record)
            self._consecutive_failures = 0

            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "circuit_breaker_probe_succeeded "
                    "probe_failures_before_recovery=%d "
                    "time_on_fallback_s=%.1f",
                    self._probe_failures,
                    time.time() - self._open_since
                    if self._open_since is not None
                    else 0.0,
                )
                self._transition_to(CircuitState.CLOSED)

    def record_failure(self, latency_s: float) -> None:
        """Record a failed primary endpoint call (transient failures only).

        Permanent failures (4xx) MUST NOT be passed here.
        Handles HALF_OPEN -> OPEN transition and CLOSED -> OPEN evaluation.
        """
        with self._lock:
            record = CallRecord(
                success=False, latency_s=latency_s, timestamp=time.time()
            )
            self._window.append(record)
            self._consecutive_failures += 1

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed -> back to OPEN with exponential backoff
                self._probe_failures += 1
                self._current_recovery_timeout = min(
                    self._config.recovery_timeout_s
                    * (self._config.recovery_backoff_factor ** self._probe_failures),
                    self._config.recovery_max_timeout_s,
                )
                self._transition_to(CircuitState.OPEN)
                logger.warning(
                    "circuit_breaker_probe_failed probe_failures=%d "
                    "next_recovery_s=%.1f",
                    self._probe_failures,
                    self._current_recovery_timeout,
                )
                return

            # CLOSED: evaluate thresholds
            self._evaluate()

    def get_status(self) -> Dict:
        """Return a snapshot of current circuit breaker state for logging/evidence."""
        with self._lock:
            window_list = list(self._window)
            return {
                "state": self._state.value,
                "consecutive_failures": self._consecutive_failures,
                "window_size": len(window_list),
                "window_capacity": self._config.window_size,
                "open_since": self._open_since,
                "error_rate": self._error_rate(window_list),
                "avg_latency_s": self._avg_latency(window_list),
                "probe_failures": self._probe_failures,
                "current_recovery_timeout_s": self._current_recovery_timeout,
            }

    # ------------------------------------------------------------------
    # Internal helpers (called under lock)
    # ------------------------------------------------------------------

    def _evaluate(self) -> None:
        """Evaluate thresholds and transition to OPEN if breached.

        Called under ``self._lock``.  Only transitions CLOSED -> OPEN.
        """
        cfg = self._config
        window_list = list(self._window)

        # Threshold 1: consecutive failures
        if self._consecutive_failures >= cfg.failure_threshold:
            self._transition_to(CircuitState.OPEN)
            return

        # Threshold 2: error rate (require at least half the window filled)
        min_data = max(2, cfg.window_size // 2)
        if len(window_list) >= min_data:
            error_rate = self._error_rate(window_list)
            if error_rate > cfg.error_rate_threshold:
                self._transition_to(CircuitState.OPEN)
                return

        # Threshold 3: average latency (require at least 2 data points)
        if len(window_list) >= 2:
            avg_lat = self._avg_latency(window_list)
            if avg_lat > cfg.latency_threshold_s:
                self._transition_to(CircuitState.OPEN)
                return

    def _transition_to(self, new_state: CircuitState) -> None:
        """Execute state transition with logging.  Called under lock."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._open_since = time.time()
        elif new_state == CircuitState.CLOSED:
            self._open_since = None
            self._consecutive_failures = 0
            self._probe_failures = 0
            self._current_recovery_timeout = self._config.recovery_timeout_s
            self._window.clear()
        # HALF_OPEN: keep _open_since for duration tracking

        logger.info(
            "circuit_breaker_state_transition old_state=%s new_state=%s "
            "consecutive_failures=%d",
            old_state.value,
            new_state.value,
            self._consecutive_failures,
        )

    @staticmethod
    def _error_rate(window: list) -> float:
        """Compute error rate from a window snapshot.  Pure function."""
        if not window:
            return 0.0
        failures = sum(1 for r in window if not r.success)
        return failures / len(window)

    @staticmethod
    def _avg_latency(window: list) -> float:
        """Compute average latency from a window snapshot.  Pure function."""
        if not window:
            return 0.0
        return sum(r.latency_s for r in window) / len(window)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_circuit_breaker_from_config(
    cb_cfg: dict,
    has_fallback: bool,
) -> Optional[CircuitBreaker]:
    """Construct a CircuitBreaker from the ``llm.circuit_breaker`` config section.

    Args:
        cb_cfg: The ``circuit_breaker`` sub-dict from ``run_config["llm"]``
                (may be empty ``{}``).
        has_fallback: True if a fallback endpoint is configured.

    Returns:
        ``CircuitBreaker`` instance if enabled, ``None`` otherwise.
    """
    # Default: enabled only when fallback is configured
    default_enabled = has_fallback
    enabled = cb_cfg.get("enabled", default_enabled)

    if not enabled:
        return None

    config = CircuitBreakerConfig(
        enabled=True,
        failure_threshold=cb_cfg.get("failure_threshold", 3),
        error_rate_threshold=cb_cfg.get("error_rate_threshold", 0.5),
        window_size=cb_cfg.get("window_size", 10),
        latency_threshold_s=cb_cfg.get("latency_threshold_s", 30.0),
        recovery_timeout_s=cb_cfg.get("recovery_timeout_s", 60.0),
        probe_timeout_s=cb_cfg.get("probe_timeout_s", 15.0),
        recovery_backoff_factor=cb_cfg.get("recovery_backoff_factor", 2.0),
        recovery_max_timeout_s=cb_cfg.get("recovery_max_timeout_s", 600.0),
    )
    return CircuitBreaker(config)
