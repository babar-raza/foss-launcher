# BT-05: Unit Tests for Enriched `_extract_api_surface()`

**Status**: Done
**Gap linkage**: BT-00 → BT-05
**Role**: Engineer
**Severity**: HIGH — new data collection path with zero dedicated tests

## Problem

`_extract_api_surface()` in `extract.py` was modified to collect `api_identifiers` (class names + method names + property names) from AST analysis results. This new collection logic has zero dedicated tests. If the upstream `analyze_file_safe()` return format changes, the harvesting silently produces an empty list.

## Scope

**In scope**: Unit tests for the `api_identifiers` collection in `_extract_api_surface()`.
**Out of scope**: Tests for `analyze_file_safe()` itself, integration tests.

## Test Cases (minimum 5)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Class with methods and properties | `api_identifiers` contains class name + method names + property names |
| 2 | Private methods (`_init`, `_helper`) | Excluded from `api_identifiers` |
| 3 | Empty file list | `api_identifiers` is empty list |
| 4 | More than 500 identifiers | Capped at 500, sorted alphabetically |
| 5 | Old checkpoint without `api_identifiers` field | Deserializes with empty list default |
| 6 | Duplicate identifiers across files | Deduplicated in output |

## Acceptance Checks

- [ ] All 6 test cases pass
- [ ] Backward compatibility verified: `ApiSurface(**old_data)` works when `api_identifiers` is missing
- [ ] Cap at 500 verified
- [ ] Private name exclusion verified
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` passes

## Deliverables

- New or extended: `tests/test_extract.py` or `tests/workers/understand/test_extract.py`

## Hard Rules

- Mock `analyze_file_safe()` to return controlled data — do NOT rely on real file analysis
- Test the `ApiSurface` model directly for backward compat (test 5)
- Do NOT modify production code

## Review Dimensions

1. Mock data matches the actual return format of `analyze_file_safe()`
2. All filtering rules tested (private names, dedup, cap)
3. Backward compat test uses raw dict without `api_identifiers` key

## Now (Runbook)

1. Read `extract.py:_extract_api_surface()` to confirm the harvesting logic
2. Read `code_analyzer.py:analyze_file_safe()` to confirm the return format
3. Find existing test files for the understand worker
4. Create test class `TestExtractApiSurfaceIdentifiers`
5. Implement all 6 test cases
6. Run test suite
