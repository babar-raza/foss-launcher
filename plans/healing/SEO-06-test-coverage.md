# SEO-06: Test Coverage Expansion

## Status: Done

## Gap Linkage
- **G-10**: Missing tests: keyword_bundle integration, canonical variants,
  description==seoTitle, Phase 1.5 worker integration

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Add targeted tests that cover the identified gaps:

1. **`test_optimize_with_keyword_bundle`** — pass a real
   `KeywordResearchBundle` (not None) to `optimize_seo_metadata`. Verify
   keywords are enhanced from the bundle's `primary_keywords`.

2. **`test_canonical_all_subdomain_variants`** — test `_generate_canonical`
   with URLs starting with `reference/`, `kb/`, `blog/`, `products/`, and a
   bare path. Verify correct subdomain in each case.

3. **`test_description_equals_seo_title_cleared`** — set description equal to
   seoTitle. Verify `_enforce_metadata_quality` clears the description.

4. **`test_description_equals_title_cleared`** — set description equal to
   title. Verify `_enforce_metadata_quality` clears the description.

5. **`test_sanitize_title_none_input`** — pass `None` as title to
   `_sanitize_title` (defensive). Verify no crash (returns empty or None).

6. **`test_enhance_keywords_string_input`** — pass keywords as a
   comma-separated string (e.g. `"python, excel"`). Verify
   `optimize_seo_metadata` handles the string-to-list conversion.

7. **`test_canonical_reference_object_page`** — verify `reference_object_page`
   role also maps to `reference.aspose.org`.

8. **`test_generate_description_all_fallbacks_exhausted`** — no Gemini, no
   purpose, no content, no claims. Verify template fallback produces a
   valid-length description.

### Allowed paths
- `tests/unit/workers/test_seo_metadata.py`
- `tests/unit/workers/test_seo_check.py`
- `plans/healing/SEO-06-test-coverage.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- All 8 new tests pass
- No existing tests broken

### Config respected end-to-end
- N/A

### No mock data in production paths
- Test data only in test files

## Deliverables
- 8 new test functions across `test_seo_metadata.py`

## Hard Rules
- No production code changes
- No network in tests
- Deterministic
- No new deps

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Testability | Every identified gap has a dedicated test |
| Thoroughness | Happy paths AND failure/edge cases covered |
| Correctness | Tests assert specific expected behavior, not just "no crash" |
| Minimality | Only tests added, no production code changes |

## Runbook

```bash
# 1. Add 8 test functions to test_seo_metadata.py
# 2. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py -x -v
# 3. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 4. Mark Done
```
