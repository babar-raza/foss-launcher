# CB-01 — LLM Provider Integration Test for Probe Timeout

## Status: Done

## Checklist
- [x] test_half_open_uses_probe_timeout — verifies 15s probe timeout passed to _call_api
- [x] test_closed_uses_normal_timeout — verifies 120s normal timeout
- [x] test_no_circuit_breaker_uses_normal_timeout — verifies None CB path
- [x] test_successful_probe_recovers_circuit — full lifecycle with timeout verification
- [x] test_failed_probe_increases_backoff — probe failure increases backoff
- [x] test_custom_probe_timeout_value — custom 25s flows through

## Gap Linkage
- **CB-G1**: The 4-line change in `llm_provider.py` (probe timeout for HALF_OPEN calls) has zero test coverage. The circuit breaker unit tests only cover the state machine in isolation; no test validates that the LLM provider actually uses the shorter timeout when the circuit breaker is probing.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Add integration-level tests that verify:
1. When the circuit breaker enters HALF_OPEN, the LLM provider uses `probe_timeout_s` (15s) instead of the full `effective_timeout` (120s) for the primary call.
2. When a probe succeeds within the shorter timeout, the circuit recovers to CLOSED and subsequent calls use the normal timeout.
3. When a probe times out at the shorter timeout, the circuit goes back to OPEN with increased backoff.
4. The full lifecycle: CLOSED → OPEN (3 failures) → HALF_OPEN (probe with short timeout) → CLOSED (recovery).

### Allowed paths
- `tests/unit/clients/test_llm_provider_circuit_breaker.py` (new file)
- `tests/unit/resilience/test_circuit_breaker.py` (add full-cycle integration test)

### Forbidden
- Any other file/path. No changes to source code.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_llm_provider_circuit_breaker.py -v` — all tests pass

### Tests
- [ ] Test: probe call uses `probe_timeout_s` not `effective_timeout` — verified via mock assertion on `_call_api` timeout arg
- [ ] Test: successful probe within short timeout → circuit CLOSED → next call uses normal timeout
- [ ] Test: probe timeout at 15s → circuit OPEN → backoff increased
- [ ] Test: full lifecycle CLOSED → OPEN → HALF_OPEN → CLOSED in one test
- [ ] At least one failure path: circuit breaker is None (disabled) → normal timeout always used

### Config respected end-to-end
- [ ] `probe_timeout_s` from config flows through factory → CircuitBreaker → LLMProvider call

### No mock data in production paths
- [ ] Tests use `unittest.mock` to mock `_call_api` / `_call_endpoint` — no real HTTP calls

## Deliverables
- `tests/unit/clients/test_llm_provider_circuit_breaker.py`: Full file with 5+ tests
- Updated `tests/unit/resilience/test_circuit_breaker.py`: Add `TestFullLifecycle` class with one comprehensive test

## Hard Rules
- Keep public signatures unchanged
- No network in offline tests — mock all HTTP calls
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Tests must not depend on real time passing — use `unittest.mock.patch` for `time.time`

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All 4 scenarios above tested, plus disabled-circuit-breaker path |
| Consistency | Test style matches existing `tests/unit/clients/` patterns |
| Production grading | Tests would catch a regression if probe timeout logic is accidentally removed |
| Correctness | Assertions verify actual timeout values passed to `_call_api`, not just success/failure |
| Testability | Tests are self-contained, no shared state between tests |
| Robustness | At least one negative test (circuit breaker disabled) |
| Integration fit | Tests import from `launcher.clients.llm_provider` and `launcher.resilience.circuit_breaker` |
| Observability | N/A (test file) |
| Minimality | No unnecessary test infrastructure; reuse existing test helpers if available |

## Now (Runbook)

```bash
# 1. Check existing LLM provider test patterns
ls tests/unit/clients/

# 2. Read an existing LLM provider test for style reference
cat tests/unit/clients/test_llm_provider.py | head -60

# 3. Create the integration test file
# (write tests/unit/clients/test_llm_provider_circuit_breaker.py)

# 4. Add full-cycle test to existing circuit breaker tests
# (edit tests/unit/resilience/test_circuit_breaker.py)

# 5. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_llm_provider_circuit_breaker.py -v

# 6. Run full suite to check for regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
