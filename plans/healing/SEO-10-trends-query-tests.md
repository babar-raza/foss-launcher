# SEO-10: Family-Specific Trends Query Tests

## Status: Done

## Gap Linkage
- **G-SR2**: No tests for `_FAMILY_TREND_TERMS` mapping or the fallback
  behavior when a family is not in the map. The fix that broadened PyTrends
  queries (e.g. `"python excel"` instead of `"cells python"`) is untested.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Add targeted tests to `tests/unit/shared/test_keyword_research.py`:

1. **`test_trends_uses_family_terms_for_known_family`** — Mock PyTrends for
   `family="cells"`. Verify queries sent are from `_FAMILY_TREND_TERMS["cells"]`
   (i.e. `"python excel"`, `"openpyxl"`, `"python spreadsheet"`), NOT
   `"cells python"`.

2. **`test_trends_falls_back_for_unknown_family`** — Use `family="unknown"`.
   Verify fallback queries are `"{platform} unknown"` and
   `"{platform} unknown library"`.

3. **`test_trends_empty_results_logged`** — Mock PyTrends returning empty
   DataFrames. Verify empty list returned and no crash.

4. **`test_trends_capped_at_3_queries`** — Family with >3 terms in map.
   Verify only first 3 queries are sent (rate-limit protection).

### Allowed paths
- `tests/unit/shared/test_keyword_research.py`
- `plans/healing/SEO-10-trends-query-tests.md`

### Forbidden
Any production code.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_keyword_research.py -x -v` — all pass

### Tests
- All 4 new tests pass
- No existing tests broken

### No mock data in production paths
- Test data only in test files

## Deliverables
- 4 new test functions in `test_keyword_research.py`

## Hard Rules
- No production code changes
- No network in tests (mock PyTrends)
- Deterministic
- No new deps

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Testability | Family-specific queries and fallback both tested |
| Correctness | Assert actual query strings, not just result counts |
| Minimality | Only tests added |

## Runbook

```bash
# 1. Add 4 test functions
# 2. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_keyword_research.py -x -v
# 3. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 4. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-10
title: Family-Specific Trends Query Tests
status: Not Started
priority: P1
gaps: [G-SR2]
allowed_paths:
  - tests/unit/shared/test_keyword_research.py
depends_on: []
```
