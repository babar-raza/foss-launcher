---
id: TM-03
title: "Telemetry API: Expand test coverage to >=90% endpoint behavior"
status: Done
priority: High
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, testing]
depends_on: [TM-01, TM-02]
allowed_paths:
  - plans/healing/TM-03-test-coverage-expansion.md
  - tests/unit/telemetry_api/test_server.py
  - tests/unit/telemetry_api/test_database.py
evidence_required:
  - reports/healing/TM-03/evidence.md
---

# Taskcard TM-03 — Expand Test Coverage to >=90% Endpoint Behavior

## Status: Done

## Gap linkage
- **G-TM-06**: No test for `batch-transactional` endpoint
- **G-TM-07**: No test for `list_runs` filter params (status, job_type, product, parent_run_id)
- **G-TM-08**: No test for pagination (limit/offset)
- **G-TM-09**: No test for event storage/retrieval roundtrip via database
- **G-TM-10**: No test for metadata cache invalidation behavior
- **G-TM-11**: No negative tests for malformed JSON bodies or missing required fields
- **G-TM-12**: No test for `get_server_config_from_env()`

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
Add the following test classes/methods to `test_server.py` and optionally a new `test_database.py`:

1. **Batch-transactional**: create, idempotent, rollback on failure
2. **List filters**: filter by status, job_type, product, parent_run_id individually and combined
3. **Pagination**: limit=1 with offset=0 then offset=1; verify total stays constant
4. **Event roundtrip**: insert event via database.add_event(), retrieve via GET /runs/{run_id}/events
5. **Metadata cache**: create run, get metadata (cache miss), get again (cache hit), invalidate, get again (cache miss)
6. **Negative tests**: POST /api/v1/runs with missing required fields (event_id, run_id, agent_name, job_type, start_time) returns 422; POST with invalid JSON returns 422
7. **Config from env**: set TELEMETRY_API_HOST, TELEMETRY_API_PORT, TELEMETRY_DB_PATH env vars, call get_server_config_from_env(), assert values

### Allowed paths:
- `plans/healing/TM-03-test-coverage-expansion.md`
- `tests/unit/telemetry_api/test_server.py`
- `tests/unit/telemetry_api/test_database.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/ -v` all pass

### UI/Web/API:
- Every endpoint behavior path has at least one test

### Tests:
- Minimum 40 total tests (current 22 + 18 new minimum)
- Happy path + at least one failure/edge case per endpoint
- All tests run in <10 seconds total
- No network calls (SQLite only, in-memory or tmp_path)

### Config respected end-to-end:
- Env var config test uses `monkeypatch` (no global state leakage)

### No mock data in production paths:
- Test fixtures use `_make_run_payload()` helper with realistic values

## Deliverables
- Updated `tests/unit/telemetry_api/test_server.py` with new test classes
- Optional `tests/unit/telemetry_api/test_database.py` for direct database layer tests
- Full file replacements (no stubs, no TODOs)
- New/updated tests covering happy path + at least one regression/failure path per gap

## Hard rules
- No network in offline tests
- Deterministic — PYTHONHASHSEED=0
- No new deps without explicit justification (pytest, httpx already available)
- Keep code/docs/tests in sync
- Tests must be independent (no ordering dependency between test classes)

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All 7 gaps have dedicated tests; every endpoint has happy + failure |
| Consistency | Test helper `_make_run_payload` reused; fixture pattern uniform |
| Production grading | Coverage sufficient to catch regressions in CI |
| Systematic approach | One test class per gap; clear naming convention |
| Correctness & spec alignment | Filter tests verify actual filtering (not just 200 status) |
| Scope & constraints | Only test files touched |
| Maintainability | Tests are self-documenting; clear assert messages |
| Testability | Meta: the tests themselves are deterministic and isolated |
| Robustness | Negative tests prove validation rejects bad input |
| Performance | All tests run in <10s; no sleeps or timeouts |
| Integration | Event roundtrip test proves database->API->response chain |
| Observability | N/A for test files |
| Minimality | Only new tests added; existing tests untouched unless TM-01/TM-02 require |

## Now (runbook)

```bash
# 1. Read current test file to understand existing coverage
cat tests/unit/telemetry_api/test_server.py | head -20

# 2. Add TestBatchTransactional class
#    - test_batch_transactional_create (3 runs, all created)
#    - test_batch_transactional_idempotent (existing run in batch)

# 3. Add TestListRunsFilters class
#    - test_filter_by_status
#    - test_filter_by_job_type
#    - test_filter_by_product
#    - test_filter_by_parent_run_id
#    - test_combined_filters

# 4. Add TestPagination class
#    - test_limit_offset
#    - test_total_unchanged_with_pagination

# 5. Add TestEventRoundtrip class
#    - test_event_storage_and_retrieval (via database.add_event + GET endpoint)

# 6. Add TestMetadataCache class
#    - test_cache_miss_then_hit

# 7. Add TestNegativeInputs class
#    - test_missing_required_field_returns_422
#    - test_invalid_json_returns_422

# 8. Add TestServerConfig class
#    - test_config_from_env (monkeypatch)

# 9. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/ -v

# 10. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
