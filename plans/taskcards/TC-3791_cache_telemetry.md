---
id: TC-3791
title: "Cache Telemetry Implementation"
status: Done
priority: High
owner: "agent-E"
updated: "2026-03-07"
tags: [telemetry, observability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3791_cache_telemetry.md
  - src/launcher/shared/cache_telemetry.py
  - tests/unit/shared/test_cache_telemetry.py
evidence_required:
  - reports/agents/telemetry/TC-3791/evidence.md
---

# Taskcard TC-3791 — Cache Telemetry Implementation

## Objective

Replace the no-op stub in `src/launcher/shared/cache_telemetry.py` with the full v1 implementation, providing structured cache event emission with thread-safe counters for LLM disk cache observability.

## Required spec references

- `specs/toolchain_ci_telemetry.md` (Section: Telemetry Events — cache_hit_rate metric)
- `specs/10_determinism_and_caching.md` (Section: LLM Disk Cache)

## Scope

### In scope
- Replace no-op `emit_cache_event()` with full implementation from v1
- Port CacheEvent dataclass, CACHE_OUTCOMES/CACHE_REASONS constants
- Port thread-safe in-memory counters (_COUNTERS, _COUNTER_LOCK)
- Port get_cache_stats() and reset_cache_stats() functions
- Write unit tests

### Out of scope
- Modifying llm_provider.py (already calls emit_cache_event correctly)
- Adding new cache event call sites
- Wiring into orchestrator (TC-3792)

## Inputs

- v1 source: `git show main:src/launch/workers/_shared/cache_telemetry.py`
- v2 stub: `src/launcher/shared/cache_telemetry.py`

## Outputs

- Fully implemented `src/launcher/shared/cache_telemetry.py` (~120 lines)
- Unit tests at `tests/unit/shared/test_cache_telemetry.py`

## Allowed paths

- plans/taskcards/TC-3791_cache_telemetry.md
- src/launcher/shared/cache_telemetry.py
- tests/unit/shared/test_cache_telemetry.py

### Allowed paths rationale
- cache_telemetry.py: the target file being implemented
- test file: required unit tests for verification

## Implementation steps

### Step 1: Replace cache_telemetry.py stub

Replace the 9-line no-op with the full implementation adapted from v1:
- CacheEvent dataclass with outcome, reason, model, key_prefix, call_id, duration_ms, extra
- Constants: CACHE_OUTCOMES (hit/miss/bypass/saved), CACHE_REASONS (ok/not_found/corrupt/nondet/fallback/disabled)
- Thread-safe counters with _COUNTER_LOCK
- emit_cache_event(): increment counter + structured DEBUG log (non-fatal)
- get_cache_stats(): thread-safe snapshot of counters
- reset_cache_stats(): zero all counters

### Step 2: Write unit tests

- Test emit_cache_event increments correct counter
- Test get_cache_stats returns snapshot
- Test reset_cache_stats zeros all
- Test thread safety (concurrent emit calls)
- Test non-fatal behavior (bad logger doesn't crash)
- Test function signature compatibility with llm_provider.py call sites

## Failure modes

### Failure mode 1: Import signature mismatch
**Detection**: `from ..shared.cache_telemetry import emit_cache_event` fails in llm_provider.py
**Resolution**: Verify emit_cache_event signature matches: `(logger, outcome, reason, *, model="", key_prefix="", call_id="", duration_ms=0, **extra)`
**Gate**: Import test in unit tests

### Failure mode 2: Thread safety regression
**Detection**: Race condition in counter updates under concurrent LLM calls
**Resolution**: Ensure _COUNTER_LOCK guards all _COUNTERS reads/writes
**Gate**: Concurrent test with threading

### Failure mode 3: Non-fatal violation
**Detection**: Exception from emit_cache_event propagates to caller
**Resolution**: Wrap entire function body in try/except with pass
**Gate**: Test with broken logger object

## Task-specific review checklist

1. [ ] emit_cache_event signature matches v1 exactly (positional: logger, outcome, reason; keyword-only: model, key_prefix, call_id, duration_ms, **extra)
2. [ ] All exceptions swallowed (non-fatal by design)
3. [ ] Thread-safe counters with lock
4. [ ] CacheEvent dataclass matches v1 fields
5. [ ] get_cache_stats returns dict copy (not reference)
6. [ ] reset_cache_stats zeros all outcome keys

## Deliverables

1. `src/launcher/shared/cache_telemetry.py` — full implementation
2. `tests/unit/shared/test_cache_telemetry.py` — unit tests
3. `reports/agents/telemetry/TC-3791/evidence.md` — test output

## Acceptance checks

1. [ ] `emit_cache_event` increments counters correctly
2. [ ] `get_cache_stats` returns thread-safe snapshot
3. [ ] `reset_cache_stats` zeros all counters
4. [ ] All existing tests pass (PYTHONHASHSEED=0)
5. [ ] No import errors in llm_provider.py

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] No import breakage
- [ ] Evidence captured: reports/agents/telemetry/TC-3791/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_cache_telemetry.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```

**Expected results**:
- All cache telemetry tests pass
- No regressions in existing test suite

## Integration boundary proven

**Upstream**: `src/launcher/clients/llm_provider.py` calls `emit_cache_event()` at cache hit/miss/bypass/saved sites
**Downstream**: Counter data available via `get_cache_stats()` for metrics calculation (TC-3794)
**Contract**: Function signature `emit_cache_event(logger, outcome, reason, *, model="", key_prefix="", call_id="", duration_ms=0, **extra) -> None`
