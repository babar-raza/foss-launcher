"""Structured telemetry helper for LLM disk cache observability.

Provides structured event emission, in-process counters, and reason codes for
LLM cache outcomes (hit / miss / bypass / saved).  The module is **standalone**
-- it intentionally does NOT import ``llm_provider`` or ``llm_cache`` to prevent
circular dependencies.  The caller (``llm_provider.py``) passes its own logger
and invokes :func:`emit_cache_event` at the appropriate call sites.

Outcome codes
-------------
hit     -- Response found in cache; network call was skipped entirely.
miss    -- No usable cache entry found; a network call will follow.
bypass  -- Cache check or save intentionally skipped (not a miss).
saved   -- Network response successfully persisted to the cache.

Reason codes
------------
ok          -- Normal hit or save; no special condition.
not_found   -- Cache file does not exist (miss).
corrupt     -- Cache file exists but could not be parsed / validated (miss).
nondet      -- Request uses temperature > 0 and ALLOW_NONDET is not set (bypass).
fallback    -- Response came from the fallback endpoint and CACHE_FALLBACK is not
               set, so it was not persisted (bypass at save time).
disabled    -- Cache is globally disabled; emitted only when explicitly requested.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict

# -- Constants ---------------------------------------------------------------

CACHE_OUTCOMES: frozenset[str] = frozenset({"hit", "miss", "bypass", "saved"})
"""Valid values for the *outcome* argument of :func:`emit_cache_event`."""

CACHE_REASONS: frozenset[str] = frozenset(
    {"ok", "not_found", "corrupt", "nondet", "fallback", "disabled"}
)
"""Valid values for the *reason* argument of :func:`emit_cache_event`."""

# -- In-memory counters ------------------------------------------------------

_COUNTERS: Dict[str, int] = {o: 0 for o in sorted(CACHE_OUTCOMES)}
_COUNTER_LOCK = threading.Lock()


def get_cache_stats() -> Dict[str, int]:
    """Return a thread-safe snapshot of all outcome counters."""
    with _COUNTER_LOCK:
        return dict(_COUNTERS)


def reset_cache_stats() -> None:
    """Reset all outcome counters to zero."""
    with _COUNTER_LOCK:
        for key in _COUNTERS:
            _COUNTERS[key] = 0


# -- Event dataclass ---------------------------------------------------------


@dataclass
class CacheEvent:
    """Structured representation of a single cache telemetry event."""

    outcome: str
    reason: str
    model: str = ""
    key_prefix: str = ""
    call_id: str = ""
    duration_ms: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


# -- Main helper -------------------------------------------------------------


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
        reason: Reason code -- see :data:`CACHE_REASONS`.
        model: Optional LLM model name for log correlation.
        key_prefix: Optional first 8 chars of the SHA-256 key.
        call_id: Optional call ID for log correlation.
        duration_ms: Optional lookup duration in milliseconds.
        **extra: Any additional key-value pairs appended to the log line.
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

    except Exception:  # noqa: BLE001 -- non-fatal by design
        pass
