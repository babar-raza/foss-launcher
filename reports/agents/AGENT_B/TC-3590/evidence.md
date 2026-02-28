# Evidence — TC-3590: LLM Circuit Breaker

**Date**: 2026-02-28
**Agent**: agent_b
**Session**: toasty-floating-spring

## Implementation Summary

Passive circuit breaker for the `LLMProviderClient` that monitors primary LLM endpoint
health across calls (latency, error rate, consecutive failures) and proactively routes
to the local Ollama fallback when the primary is detected as flaky.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/launch/resilience/circuit_breaker.py` | ~240 | `CircuitState`, `CircuitBreakerConfig`, `CallRecord`, `CircuitBreaker`, `build_circuit_breaker_from_config()` |
| `tests/unit/clients/test_circuit_breaker.py` | ~330 | 28 tests across 6 classes |
| `plans/taskcards/TC-3590_llm_circuit_breaker.md` | ~130 | Governance taskcard |

## Files Modified

| File | Change | Lines Added |
|------|--------|-------------|
| `src/launch/resilience/__init__.py` | Export circuit breaker symbols | +11 |
| `src/launch/clients/llm_provider.py` | Import, `__init__` param, L1 loop routing, factory | +55 |
| `specs/schemas/run_config.schema.json` | Optional `circuit_breaker` object in `llm` section | +38 |
| `configs/pilots/_template.pinned.run_config.yaml` | Commented-out config example | +9 |

## State Machine

```
CLOSED (normal) ──[consecutive_failures >= threshold]──► OPEN (flaky)
     │                    OR [error_rate > threshold]         │
     │                    OR [avg_latency > threshold]        │
     ◄──[probe success]── HALF_OPEN ◄──[recovery_timeout]────┘
                            │
                            └──[probe failure]──► OPEN
```

## Test Results

```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_circuit_breaker.py -v
28 passed, 0 failed

$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no -p no:warnings
7762 passed, 13 skipped, 3 xfailed, 0 failed  (baseline: 7734)
```

**+28 net new tests**, 0 regressions.

## Test Coverage (28 tests in 6 classes)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestClosedToOpen | 5 | consecutive failures, error rate, latency, success resets, closed returns false |
| TestOpenRecovery | 4 | timeout→half_open, stays open, success→closed, failure→re-open |
| TestMetrics | 8 | empty/all_success/all_fail error_rate, empty/calc avg_latency, window_size, get_status |
| TestThreadSafety | 2 | concurrent record_calls, concurrent should_use_fallback |
| TestBuildFromConfig | 5 | no_fallback, with_fallback, explicit_disable, explicit_enable, values_propagate |
| TestLLMProviderIntegration | 5 | open_skips_primary, closed_uses_primary, no_cb_preserves, failure_trips, no_fallback_tries_primary |

## Key Design Decisions

1. **Passive (no background threads)**: Each call's result is the health signal.
   Reason: no event loop in the codebase; budget system already prevents runaway.

2. **RLock (not Lock)**: `_evaluate()` is called from `record_failure()` which holds
   the lock. RLock allows re-entry from the same thread without deadlock.

3. **Only transient failures recorded**: `classify_failure()` from `retry_policy.py`
   guards against permanent errors (4xx) inflating the error rate.

4. **Auto-enabled when fallback configured**: `build_circuit_breaker_from_config({})`
   with `has_fallback=True` returns a CircuitBreaker with defaults. No operator config
   change needed.

5. **Graceful degradation**: When circuit is OPEN but no fallback configured, logs
   a warning and tries primary anyway (better than hard failure).

## Backward Compatibility

- `circuit_breaker=None` (default) changes nothing — all existing behavior preserved
- `create_llm_client_from_config()` only creates CB when fallback is configured
- Existing `_try_fallback()` reactive path preserved as second safety net
- Schema `circuit_breaker` is optional — existing configs validate without it
