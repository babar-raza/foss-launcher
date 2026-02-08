# TC-999 Evidence: Fix Stale Test Fixture url_path in test_tc_450

## Task Summary

Fixed stale `url_path` value in `tests/unit/workers/test_tc_450_linker_and_patcher.py` that incorrectly included section name "docs" in the URL path.

## Change Applied

**File:** `tests/unit/workers/test_tc_450_linker_and_patcher.py`
**Line:** 78

**Before:**
```python
"url_path": "/test-product/python/docs/getting-started/",
```

**After:**
```python
"url_path": "/test-product/python/getting-started/",
```

## Verification

### 1. Search for remaining stale url_path values

```bash
grep -E '"url_path".*/(docs|kb|blog|reference|products)/' tests/unit/workers/test_tc_450_linker_and_patcher.py
```

**Result:** No matches found (expected)

### 2. Test execution

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_450_linker_and_patcher.py -v
```

**Result:** All 17 tests passed

```
tests\unit\workers\test_tc_450_linker_and_patcher.py .................   [100%]
======================== 17 passed, 1 warning in 0.73s ========================
```

## Spec Reference

Per `specs/33_public_url_mapping.md` lines 344-350, section names belong in subdomains (e.g., `docs.aspose.org`), not in URL paths. The correct URL format is:

```
/<family>/<platform>/<slug>/
```

NOT:

```
/<family>/<platform>/<section>/<slug>/
```

## Artifacts Changed

| File | Change |
|------|--------|
| `tests/unit/workers/test_tc_450_linker_and_patcher.py` | Removed `/docs/` from `url_path` fixture value |

## Acceptance Criteria Met

- [x] url_path does not contain section name
- [x] Test passes (17/17)
- [x] No regressions
- [x] Format matches `/<family>/<platform>/<slug>/`

## Date

2026-02-06
