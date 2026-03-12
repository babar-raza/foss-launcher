# CB-04 — Test Quality + Redundant Reset Cleanup

## Status: Done

## Checklist
- [x] Redundant `_probe_failures=0` and `_current_recovery_timeout=...` removed from `record_success()`
- [x] Reset happens only in `_transition_to(CLOSED)` (single responsibility)
- [x] No `cb._current_recovery_timeout` or `cb._probe_failures` access in tests (only `cb._config` in factory tests)
- [x] All 37 targeted tests still pass
- [x] Full suite 2038 passed

## Gap Linkage
- **CB-G5**: Backoff state (`_probe_failures`, `_current_recovery_timeout`) is reset in both `record_success()` (lines 151-152) AND `_transition_to(CLOSED)` (lines 246-247). This is redundant — the reset should happen in one place only.
- **CB-G6**: Tests assert against private attributes (`cb._current_recovery_timeout`, `cb._probe_failures`). This is fragile — if internals are renamed, tests break even though behavior is correct. Tests should assert via the public `get_status()` API instead.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Remove the explicit `_probe_failures = 0` and `_current_recovery_timeout = ...` reset from `record_success()`. Keep the reset only in `_transition_to(CLOSED)` which is already called by `record_success()`. This is the single-responsibility fix.
2. Refactor all test assertions that access `cb._current_recovery_timeout` or `cb._probe_failures` to use `cb.get_status()["current_recovery_timeout_s"]` and `cb.get_status()["probe_failures"]` instead.

### Allowed paths
- `src/launcher/resilience/circuit_breaker.py`
- `tests/unit/resilience/test_circuit_breaker.py`

### Forbidden
- Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v` — all tests pass

### Tests
- [ ] No test references `cb._current_recovery_timeout` (grep verification)
- [ ] No test references `cb._probe_failures` (grep verification)
- [ ] All backoff assertions use `cb.get_status()` public API
- [ ] `record_success()` no longer contains explicit backoff reset lines
- [ ] `_transition_to(CLOSED)` still contains the backoff reset
- [ ] All existing test behaviors unchanged (same pass/fail outcomes)

### Config respected end-to-end
- N/A (refactoring only)

### No mock data in production paths
- N/A (test-only changes to assertions)

## Deliverables
- Updated `src/launcher/resilience/circuit_breaker.py`: Remove 2 lines from `record_success()`
- Updated `tests/unit/resilience/test_circuit_breaker.py`: Replace all private attribute access with `get_status()` calls

## Hard Rules
- Keep public signatures unchanged
- `get_status()` return dict keys must not change
- No new deps
- Keep code/docs/tests in sync
- Deterministic runs (PYTHONHASHSEED=0)

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Maintainability | Zero private attribute access in tests; all assertions via public API |
| Correctness | Behavior identical before and after — verified by same test outcomes |
| Minimality | Only 2 lines removed from source, test assertions rewritten to use public API |
| Consistency | Single reset location for backoff state (`_transition_to`) |
| Testability | Tests are resilient to internal renaming |

## Now (Runbook)

```bash
# 1. Remove redundant reset from record_success()
# (edit src/launcher/resilience/circuit_breaker.py — remove 2 lines)

# 2. Replace private attribute assertions in tests
# (edit tests/unit/resilience/test_circuit_breaker.py)

# 3. Verify no private attribute access remains
grep -n "_current_recovery_timeout\|_probe_failures" tests/unit/resilience/test_circuit_breaker.py
# Expected: only in _make_cb or comments, not in assertions

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
