# RID-02: Run ID Test Coverage

## Status: Done

## Gap Linkage
- G-RID-03: No unit test for `generate_run_id()` format, length, or uniqueness

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Create `tests/unit/util/test_run_id.py` with comprehensive tests for `generate_run_id()`:
1. **Format test**: output matches `r_\d{6}_[0-9a-f]{6}` (after RID-01 applies hex6)
2. **Length test**: exactly 15 chars
3. **Date component test**: freeze time with `unittest.mock.patch`, verify YYMMDD segment matches
4. **Uniqueness test**: generate 1000 IDs, assert all unique
5. **Deterministic date test**: two calls within same UTC day share the date prefix

### Allowed paths
- `tests/unit/util/test_run_id.py` (new file)
- `tests/unit/util/__init__.py` (create if missing, empty)

### Forbidden
- Any other file/path

## Acceptance Checks

### Tests
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py -v` — all pass
- At least 5 test functions covering format, length, date, uniqueness, prefix consistency

### No mock data in production paths
- Tests use `unittest.mock.patch` for time freezing, no production code changes

## Deliverables
- `tests/unit/util/__init__.py` (empty, if not exists)
- `tests/unit/util/test_run_id.py` with ≥5 test functions

## Hard Rules
- No network in offline tests
- Deterministic via `PYTHONHASHSEED=0`
- No new deps (use stdlib `unittest.mock`)
- Tests must pass with both hex4 (current) and hex6 (after RID-01) — use regex `[0-9a-f]{4,6}` if RID-01 hasn't landed yet, or coordinate with RID-01

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | 5 test cases covering format, length, date, uniqueness, prefix |
| Consistency | Test naming follows existing `tests/unit/` conventions |
| Production grading | Tests catch any future format regression immediately |
| Testability | Each test is independent, fast (<1s), deterministic |
| Robustness | Uniqueness test catches collision regressions |
| Minimality | 1-2 new files, no production code changes |

## Now (Runbook)

```bash
# 1. Create tests/unit/util/__init__.py if missing
# 2. Create tests/unit/util/test_run_id.py
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py -v
# 4. Confirm full suite still green
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
