"""Structured telemetry helper for LLM disk cache observability.

Write-fence owner: TC-2410 (OBS_AGENT).

Purpose
-------
Provides structured event emission, in-process counters, and reason codes for
LLM cache outcomes (hit / miss / bypass / saved).  The module is **standalone**
— it intentionally does NOT import ``llm_provider`` or ``llm_cache`` to prevent
circular dependencies.  The caller (``llm_provider.py``) passes its own logger
and invokes :func:`emit_cache_event` at the appropriate call sites.

Outcome codes
-------------
hit     — Response found in cache; network call was skipped entirely.
miss    — No usable cache entry found; a network call will follow.
bypass  — Cache check or save intentionally skipped (not a miss).
saved   — Network response successfully persisted to the cache.

Reason codes
------------
ok          — Normal hit or save; no special condition.
not_found   — Cache file does not exist (miss).
corrupt     — Cache file exists but could not be parsed / validated (miss).
nondet      — Request uses temperature > 0 and ALLOW_NONDET is not set (bypass).
fallback    — Response came from the fallback endpoint and CACHE_FALLBACK is not
              set, so it was not persisted (bypass at save time).
disabled    — Cache is globally disabled; emitted only when explicitly requested.

Usage
-----
::

    from launch.workers._shared.cache_telemetry import (
        emit_cache_event,
        get_cache_stats,
        reset_cache_stats,
    )

    # In LLMProviderClient (llm_provider.py) — # LLM_CACHE_TELEMETRY_HOOK
    emit_cache_event(
        logger, "hit", "ok",
        key_prefix=key[:8], call_id=call_id, model=self.model,
    )

Spec: docs/reference/config.md — LLM Disk Cache / Diagnosing cache behavior
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# ── Constants ──────────────────────────────────────────────────────────────────

CACHE_OUTCOMES: frozenset = frozenset({"hit", "miss", "bypass", "saved"})
"""Valid values for the *outcome* argument of :func:`emit_cache_event`."""

CACHE_REASONS: frozenset = frozenset(
    {"ok", "not_found", "corrupt", "nondet", "fallback", "disabled"}
)
"""Valid values for the *reason* argument of :func:`emit_cache_event`."""

# ── In-memory counters ─────────────────────────────────────────────────────────

_COUNTERS: Dict[str, int] = {o: 0 for o in CACHE_OUTCOMES}
_COUNTER_LOCK = threading.Lock()


def get_cache_stats() -> Dict[str, int]:
    """Return a thread-safe snapshot of all outcome counters.

    Returns:
        Dict with keys ``hit``, ``miss``, ``bypass``, ``saved`` and integer
        values reflecting totals since process start (or last
        :func:`reset_cache_stats` call).

    Example::

        >>> stats = get_cache_stats()
        >>> print(stats)
        {'hit': 3, 'miss': 12, 'bypass': 2, 'saved': 12}
    """
    with _COUNTER_LOCK:
        return dict(_COUNTERS)


def reset_cache_stats() -> None:
    """Reset all outcome counters to zero.

    Intended for use between test cases to ensure counter isolation.
    """
    with _COUNTER_LOCK:
        for key in _COUNTERS:
            _COUNTERS[key] = 0


# ── Event dataclass ────────────────────────────────────────────────────────────

@dataclass
class CacheEvent:
    """Structured representation of a single cache telemetry event.

    Attributes:
        outcome: One of :data:`CACHE_OUTCOMES`.
        reason: One of :data:`CACHE_REASONS`.
        model: LLM model name (e.g. ``"gemma3:12b"``).
        key_prefix: First 8 chars of the SHA-256 cache key (for log correlation).
        call_id: LLM call ID from ``LLMProviderClient`` (for log correlation).
        duration_ms: Time from cache lookup start to result (0 for non-timed events).
        extra: Catch-all for any additional fields passed via **kwargs.
    """

    outcome: str
    reason: str
    model: str = ""
    key_prefix: str = ""
    call_id: str = ""
    duration_ms: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


# ── Main helper ────────────────────────────────────────────────────────────────

def emit_cache_event(
    logger: Any,
    outcome: str,
    reason: str,
    *,
    model: str = "",
    key_prefix: str = "",
    call_id: str = "",
    duration_ms: int = 0,
    **extra: Any,
) -> None:
    """Emit a structured DEBUG log line and increment the outcome counter.

    This function is **non-fatal**: any exception during logging or counter
    updates is silently swallowed so it can never crash the pipeline.

    Args:
        logger: The structlog (or standard) logger from the calling module.
        outcome: One of ``"hit"``, ``"miss"``, ``"bypass"``, ``"saved"``.
        reason: Reason code — see :data:`CACHE_REASONS`.
        model: Optional LLM model name for log correlation.
        key_prefix: Optional first 8 chars of the SHA-256 key.
        call_id: Optional call ID for log correlation.
        duration_ms: Optional lookup duration in milliseconds.
        **extra: Any additional key-value pairs appended to the log line.

    Side effects:
        - Calls ``logger.debug(...)`` with all relevant fields.
        - Increments ``_COUNTERS[outcome]`` in a thread-safe manner.

    Example log output (structlog JSON format)::

        {"level": "debug", "event": "llm_cache_hit",
         "outcome": "hit", "reason": "ok",
         "key_prefix": "a1b2c3d4", "call_id": "sect_write_001",
         "model": "gemma3:12b", "duration_ms": 2}
    """
    try:
        # Increment counter
        with _COUNTER_LOCK:
            if outcome in _COUNTERS:
                _COUNTERS[outcome] += 1

        # Build log kwargs
        log_kwargs: Dict[str, Any] = {
            "outcome": outcome,
            "reason": reason,
        }
        if model:
            log_kwargs["model"] = model
        if key_prefix:
            log_kwargs["key_prefix"] = key_prefix
        if call_id:
            log_kwargs["call_id"] = call_id
        if duration_ms:
            log_kwargs["duration_ms"] = duration_ms
        log_kwargs.update(extra)

        event_name = f"llm_cache_{outcome}"
        logger.debug(event_name, **log_kwargs)

    except Exception:  # noqa: BLE001 — non-fatal by design
        pass
