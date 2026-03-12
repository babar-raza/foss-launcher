# CB-02 — Circuit Breaker Config Validation

## Status: Done

## Checklist
- [x] __post_init__ added to CircuitBreakerConfig
- [x] probe_timeout_s <= 0 raises ValueError
- [x] recovery_backoff_factor < 1.0 raises ValueError
- [x] recovery_max_timeout_s < recovery_timeout_s raises ValueError
- [x] failure_threshold, window_size, error_rate_threshold, latency_threshold_s, recovery_timeout_s validated
- [x] Default config passes validation
- [x] All existing tests updated (no more recovery_timeout_s=0.0)

## Gap Linkage
- **CB-G2**: `CircuitBreakerConfig` accepts any float values without validation. `probe_timeout_s=0` makes probes impossible, `recovery_backoff_factor=0` makes backoff formula return 0 forever, `recovery_max_timeout_s < recovery_timeout_s` makes the cap lower than the base (backoff starts at cap immediately).

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Add `__post_init__` validation to `CircuitBreakerConfig` that raises `ValueError` for nonsensical configurations:
1. `probe_timeout_s > 0` — must be positive
2. `recovery_backoff_factor >= 1.0` — factor < 1 would shrink intervals (nonsensical)
3. `recovery_max_timeout_s >= recovery_timeout_s` — cap must be >= base
4. Existing fields: `failure_threshold >= 1`, `window_size >= 1`, `recovery_timeout_s > 0`, `latency_threshold_s > 0`, `error_rate_threshold` in (0, 1]

Add corresponding tests for each validation rule (both valid and invalid inputs).

### Allowed paths
- `src/launcher/resilience/circuit_breaker.py`
- `tests/unit/resilience/test_circuit_breaker.py`

### Forbidden
- Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v` — all tests pass

### Tests
- [ ] Test: `probe_timeout_s=0` raises `ValueError`
- [ ] Test: `probe_timeout_s=-1` raises `ValueError`
- [ ] Test: `recovery_backoff_factor=0.5` raises `ValueError`
- [ ] Test: `recovery_max_timeout_s < recovery_timeout_s` raises `ValueError`
- [ ] Test: valid config with all new fields does NOT raise
- [ ] Test: default config does NOT raise

### Config respected end-to-end
- [ ] Factory `build_circuit_breaker_from_config` propagates validation errors (no silent swallowing)

### No mock data in production paths
- [ ] Validation is pure Python — no mocks needed

## Deliverables
- Updated `src/launcher/resilience/circuit_breaker.py`: Add `__post_init__` to `CircuitBreakerConfig`
- Updated `tests/unit/resilience/test_circuit_breaker.py`: Add `TestConfigValidation` class with 6+ tests

## Hard Rules
- Keep public signatures unchanged — `CircuitBreakerConfig` is still a `@dataclass`
- `__post_init__` must validate ALL fields, not just the new ones (opportunity to harden existing fields)
- Error messages must include the actual value and the constraint
- No new deps
- Keep code/docs/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Every config field with a numeric constraint is validated |
| Correctness | Boundary values tested (e.g., `probe_timeout_s=0.001` is valid, `0` is not) |
| Robustness | `ValueError` messages are clear enough to debug without reading source |
| Testability | Each validation rule has at least one positive and one negative test |
| Minimality | Only `__post_init__` added — no other structural changes |
| Production grading | Bad config fails fast at init, not silently at runtime |

## Now (Runbook)

```bash
# 1. Read current CircuitBreakerConfig
# (already known — lines 48-66 of circuit_breaker.py)

# 2. Add __post_init__ method to CircuitBreakerConfig
# (edit src/launcher/resilience/circuit_breaker.py)

# 3. Add TestConfigValidation class
# (edit tests/unit/resilience/test_circuit_breaker.py)

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v

# 5. Check that factory still works with default and custom configs
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
