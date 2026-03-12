---
id: TC-3815
title: "Circuit breaker intelligent recovery (probe timeout + exponential backoff)"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [resilience, circuit-breaker, fallback]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3815_circuit_breaker_intelligent_recovery.md
  - src/launcher/resilience/circuit_breaker.py
  - src/launcher/clients/llm_provider.py
  - tests/unit/resilience/test_circuit_breaker.py
evidence_required:
  - reports/TC-3815/evidence.md
---

# Taskcard TC-3815 — Circuit breaker intelligent recovery

## Objective

Fix the circuit breaker so it actually recovers back to the primary LLM endpoint after a transient outage, instead of permanently staying on the local fallback. The root cause is that HALF_OPEN probes use the full 120s request timeout and the recovery interval never increases.

## Required spec references

- `specs/25_frameworks_and_dependencies.md` (LLM provider integration)
- `specs/28_coordination_and_handoffs.md` (resilience and retry policy)

## Scope

### In scope
- Add shorter probe timeout for HALF_OPEN calls (default 15s)
- Add exponential backoff on recovery interval after failed probes (60s → 120s → 240s → ... → 600s cap)
- Reset backoff state on successful probe
- Expose backoff state in get_status() for observability
- Update factory to parse new config fields
- Use probe timeout in llm_provider.py for HALF_OPEN calls

### Out of scope
- Background health check threads (architecture explicitly forbids them)
- Gradual traffic ramp-up after recovery (unnecessary complexity for single-endpoint)
- Changes to retry_policy.py (not affected)

## Inputs

- `src/launcher/resilience/circuit_breaker.py` (current implementation)
- `src/launcher/clients/llm_provider.py` (current LLM call orchestration)

## Outputs

- Updated `circuit_breaker.py` with probe timeout + exponential backoff
- Updated `llm_provider.py` with probe-aware timeout selection
- New `tests/unit/resilience/test_circuit_breaker.py` with unit tests

## Allowed paths

- plans/taskcards/TC-3815_circuit_breaker_intelligent_recovery.md
- src/launcher/resilience/circuit_breaker.py
- src/launcher/clients/llm_provider.py
- tests/unit/resilience/test_circuit_breaker.py

### Allowed paths rationale
- circuit_breaker.py: Core fix — add backoff state, probe timeout config, dynamic recovery
- llm_provider.py: Consumer fix — use shorter timeout for HALF_OPEN probes
- tests/unit/resilience/test_circuit_breaker.py: Verify all new behavior

## Implementation steps

### Step 1: Add config fields to CircuitBreakerConfig

Add `probe_timeout_s`, `recovery_backoff_factor`, `recovery_max_timeout_s` with backwards-compatible defaults.

### Step 2: Add backoff state to CircuitBreaker.__init__

Add `_probe_failures` counter and `_current_recovery_timeout` dynamic value.

### Step 3: Add is_probing property and probe_timeout_s property

Expose HALF_OPEN state and configured probe timeout to consumers.

### Step 4: Use dynamic recovery timeout in should_use_fallback()

Replace fixed `recovery_timeout_s` with `_current_recovery_timeout`.

### Step 5: Apply exponential backoff in record_failure()

On HALF_OPEN probe failure: increment probe failures, compute backoff.

### Step 6: Reset backoff in record_success() and _transition_to(CLOSED)

On successful probe: reset all backoff state.

### Step 7: Update get_status() and factory

Expose new fields in status dict; parse new config keys in factory.

### Step 8: Update llm_provider.py

Use `circuit_breaker.is_probing` + `probe_timeout_s` for HALF_OPEN calls.

### Step 9: Add unit tests

Test backoff progression, cap, reset, factory, and is_probing.

## Failure modes

### Failure mode 1: Probe timeout too aggressive

**Detection**: Primary recovers but probes keep failing (15s not enough for cold start)
**Resolution**: Increase `probe_timeout_s` in config (e.g., 30s)
**Gate**: N/A — runtime config, not a gate

### Failure mode 2: Backoff too long, primary recovered but not re-checked

**Detection**: Logs show `current_recovery_timeout_s` at 600s while primary is healthy
**Resolution**: Reduce `recovery_max_timeout_s` or `recovery_backoff_factor` in config
**Gate**: N/A — operational tuning

### Failure mode 3: TOCTOU between should_use_fallback() and is_probing

**Detection**: Probe call uses wrong timeout in multi-threaded scenario
**Resolution**: Harmless — worst case uses normal timeout instead of probe timeout. State only changes via record_success/record_failure which haven't been called yet.
**Gate**: Thread safety documented in circuit_breaker.py docstring

## Task-specific review checklist

1. [ ] `CircuitBreakerConfig` has 3 new fields with correct defaults
2. [ ] `_probe_failures` and `_current_recovery_timeout` initialized correctly
3. [ ] `should_use_fallback()` uses `_current_recovery_timeout` not fixed value
4. [ ] `record_failure()` applies backoff formula correctly with cap
5. [ ] `record_success()` and `_transition_to(CLOSED)` reset all backoff state
6. [ ] `llm_provider.py` uses `probe_timeout_s` only when `is_probing` is True

## Deliverables

1. Updated `src/launcher/resilience/circuit_breaker.py`
2. Updated `src/launcher/clients/llm_provider.py`
3. New `tests/unit/resilience/test_circuit_breaker.py`

## Acceptance checks

1. [ ] All existing tests pass
2. [ ] New circuit breaker tests pass
3. [ ] Backoff progression matches plan: 60→120→240→480→600(cap)
4. [ ] Successful probe resets backoff to base 60s
5. [ ] is_probing returns True only in HALF_OPEN state
6. [ ] Factory parses new config keys and uses defaults for missing keys

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3815/

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v
.venv/Scripts/python.exe -m pytest tests/ -x --timeout=120
```

**Expected results**:
- All circuit breaker tests pass
- No regressions in existing tests

## Integration boundary proven

**Upstream**: `llm_provider.py` calls `should_use_fallback()`, `is_probing`, `probe_timeout_s`, `record_success()`, `record_failure()`
**Downstream**: Circuit breaker state drives endpoint selection and timeout in LLM provider
**Contract**: `should_use_fallback() -> bool`, `is_probing -> bool`, `probe_timeout_s -> float`, `record_success(float)`, `record_failure(float)` — all thread-safe
