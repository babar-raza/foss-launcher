---
id: TM-02
title: "Telemetry API: SQL field allowlist and private API elimination"
status: Done
priority: High
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, security, robustness]
depends_on: []
allowed_paths:
  - plans/healing/TM-02-sql-safety-and-robustness.md
  - src/launcher/telemetry_api/routes/database.py
  - src/launcher/telemetry_api/routes/batch.py
  - tests/unit/telemetry_api/test_server.py
evidence_required:
  - reports/healing/TM-02/evidence.md
---

# Taskcard TM-02 — SQL Field Allowlist and Private API Elimination

## Status: Done

## Gap linkage
- **G-TM-03**: `update_run()` in `database.py` builds SQL column names with f-string `f"{field} = ?"` — field names from Pydantic model but no explicit allowlist validation (defense-in-depth violation)
- **G-TM-04**: `batch-transactional` endpoint in `batch.py` calls `db._get_connection()` (private method) — fragile coupling, breaks encapsulation
- **G-TM-05**: No input length validation on string fields

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
1. Add `_UPDATABLE_FIELDS` frozenset to `database.py` containing the exact column names that `update_run()` is allowed to SET. Skip any field not in the set.
2. Add a public `get_connection()` method (or a public `batch_create_runs()` method) to `TelemetryDatabase` so `batch.py` doesn't access `_get_connection()` directly
3. Add `MAX_STRING_LENGTH = 1000` constant and truncate/validate string inputs in `create_run()` and `update_run()` to prevent unbounded storage

### Allowed paths:
- `plans/healing/TM-02-sql-safety-and-robustness.md`
- `src/launcher/telemetry_api/routes/database.py`
- `src/launcher/telemetry_api/routes/batch.py`
- `tests/unit/telemetry_api/test_server.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v` passes

### UI/Web/API:
- `PATCH /api/v1/runs/{event_id}` with an unknown field in body is silently ignored (not injected into SQL)
- Batch-transactional endpoint still works without accessing private APIs

### Tests:
- New test: PATCH with unknown field name does not crash or inject into SQL
- New test: batch-transactional creates runs correctly (moved from TM-03 dependency)
- New test: overlong string field is handled (truncated or rejected)
- All existing 22 tests still pass

### Config respected end-to-end:
- N/A

### No mock data in production paths:
- N/A

## Deliverables
- Modified `src/launcher/telemetry_api/routes/database.py` with:
  - `_UPDATABLE_FIELDS` frozenset
  - Field name validation in `update_run()`
  - Public `batch_create_runs()` or `transactional_batch()` method
  - String length guard
- Modified `src/launcher/telemetry_api/routes/batch.py` using public API only
- Updated `tests/unit/telemetry_api/test_server.py` with new test cases
- Full file replacements (no stubs, no TODOs)

## Hard rules
- Keep public signatures for existing methods (`create_run`, `update_run`, `list_runs`, etc.)
- `batch-transactional` must retain atomic semantics (all-or-nothing)
- No network in offline tests
- No new deps
- Deterministic — PYTHONHASHSEED=0

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All three gaps closed; no dynamic SQL without allowlist |
| Consistency | Allowlist covers exactly the columns in UpdateRunRequest model |
| Production grading | No SQL column injection possible even with compromised Pydantic |
| Systematic approach | Enumerate all dynamic SQL sites; add allowlist; remove private access; test |
| Correctness & spec alignment | update_run semantics unchanged; batch-transactional semantics unchanged |
| Scope & constraints | Only allowed files touched |
| Maintainability | Allowlist is a single frozenset; easy to extend |
| Testability | Unknown-field test proves the allowlist works |
| Robustness | Overlong strings handled; unknown fields skipped |
| Performance | Frozenset lookup is O(1); no regression |
| Integration | batch.py uses only public database API |
| Observability | Log warning when unknown field is skipped |
| Minimality | ~20 lines added to database.py; ~10 lines changed in batch.py |

## Now (runbook)

```bash
# 1. Read database.py to identify all dynamic SQL
grep -n "f\"" src/launcher/telemetry_api/routes/database.py

# 2. List UpdateRunRequest fields (the allowlist source)
grep "Optional\[" src/launcher/telemetry_api/routes/models.py | head -20

# 3. Add _UPDATABLE_FIELDS frozenset before update_run()
# 4. Add field validation: skip fields not in _UPDATABLE_FIELDS
# 5. Add public batch method to TelemetryDatabase
# 6. Update batch.py to use public API

# 7. Read batch.py to find _get_connection usage
grep -n "_get_connection" src/launcher/telemetry_api/routes/batch.py

# 8. Add tests
# 9. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v

# 10. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
