# CB-03 — Recovery Observability (Logs on Success + Severity Fix)

## Status: Done

## Checklist
- [x] circuit_breaker_probe_succeeded log added in record_success() for HALF_OPEN
- [x] Log includes probe_failures_before_recovery and time_on_fallback_s
- [x] circuit_breaker_probe_failed changed from logger.info to logger.warning
- [x] Normal CLOSED success does NOT emit probe log
- [x] 5 observability tests added to TestRecoveryObservability

## Gap Linkage
- **CB-G3**: When a HALF_OPEN probe succeeds and the circuit recovers to CLOSED, there is no log message. Recovery is silent — an operator watching logs sees probe failures but never the recovery event.
- **CB-G4**: The `circuit_breaker_probe_failed` log uses `logger.info()` but a probe failure that increases backoff is operationally significant and should be `logger.warning()`.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Add a `logger.info()` call in `record_success()` when transitioning from HALF_OPEN to CLOSED, logging:
   - `probe_failures_before_recovery` (how many probes failed before this one succeeded)
   - `time_on_fallback_s` (elapsed time since circuit first opened, computed from `_open_since`)
   - `recovery_timeout_at_recovery_s` (what the backoff had grown to before success)
2. Change `circuit_breaker_probe_failed` from `logger.info()` to `logger.warning()`.

### Allowed paths
- `src/launcher/resilience/circuit_breaker.py`
- `tests/unit/resilience/test_circuit_breaker.py`

### Forbidden
- Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v` — all tests pass

### Tests
- [ ] Test: successful probe emits log with `circuit_breaker_probe_succeeded` message (use `caplog`)
- [ ] Test: log includes `probe_failures_before_recovery` field
- [ ] Test: log includes `time_on_fallback_s` field (> 0)
- [ ] Test: failed probe emits WARNING-level log (not INFO)
- [ ] Test: normal CLOSED→CLOSED success does NOT emit probe recovery log

### Config respected end-to-end
- N/A (logging changes only)

### No mock data in production paths
- [ ] Tests use `pytest.caplog` — no HTTP calls

## Deliverables
- Updated `src/launcher/resilience/circuit_breaker.py`: 2 log changes (1 new info log, 1 severity change)
- Updated `tests/unit/resilience/test_circuit_breaker.py`: Add `TestRecoveryObservability` class with 5 tests

## Hard Rules
- Keep public signatures unchanged
- Log format must match existing structured-log conventions in the file (key=value pairs)
- Recovery log MUST be emitted BEFORE `_transition_to(CLOSED)` (so `_open_since` is still available)
- No new deps
- Keep code/docs/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Observability | Every state transition (open, probe fail, probe succeed, close) has a log at appropriate severity |
| Correctness | `time_on_fallback_s` accurately reflects wall-clock time on fallback |
| Minimality | Only 2 log statements changed — no structural changes |
| Testability | All log assertions use `caplog` fixture, no fragile string matching beyond key names |
| Production grading | An operator can reconstruct the full circuit breaker lifecycle from logs alone |

## Now (Runbook)

```bash
# 1. Add recovery success log in record_success() BEFORE _transition_to(CLOSED)
# (edit src/launcher/resilience/circuit_breaker.py)

# 2. Change logger.info to logger.warning for probe failure
# (edit src/launcher/resilience/circuit_breaker.py)

# 3. Add TestRecoveryObservability tests with caplog
# (edit tests/unit/resilience/test_circuit_breaker.py)

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_circuit_breaker.py -v

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
