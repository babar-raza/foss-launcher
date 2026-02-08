# TC-1000: Fix W6 content_preview Double Directory Bug - Evidence

## Objective
Fix the double "content" directory bug in W6 LinkerAndPatcher where `content_preview_dir` incorrectly appended "content" when `patch["path"]` already included it, resulting in `content_preview/content/content/...` structure.

## Root Cause Analysis

At line 867 of `src/launch/workers/w6_linker_and_patcher/worker.py`:
```python
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
```

At line 875, the code appends `patch["path"]`:
```python
dest_path = content_preview_dir / patch["path"]
```

Since `patch["path"]` already starts with `"content/"` (e.g., `"content/docs.aspose.org/3d/en/python/..."`), this created:
- `content_preview/content/content/docs.aspose.org/...` (WRONG)

Instead of:
- `content_preview/content/docs.aspose.org/...` (CORRECT)

## Fix Applied

### File 1: `src/launch/workers/w6_linker_and_patcher/worker.py` (Line 867)

**Before:**
```python
# TC-952: Export content preview for user inspection
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
content_preview_dir.mkdir(parents=True, exist_ok=True)
```

**After:**
```python
# TC-952: Export content preview for user inspection
# TC-1000: Fix double-content bug - patch["path"] already includes "content/"
content_preview_dir = run_layout.run_dir / "content_preview"
content_preview_dir.mkdir(parents=True, exist_ok=True)
```

### File 2: `tests/unit/workers/test_w6_content_export.py` (Line 440)

**Before:**
```python
assert normalized_path == "content_preview/content", f"Expected 'content_preview/content', got '{normalized_path}'"
```

**After:**
```python
# TC-1000: Fixed - content_preview_dir no longer includes extra "/content"
# since patch["path"] already starts with "content/"
assert normalized_path == "content_preview", f"Expected 'content_preview', got '{normalized_path}'"
```

## Test Results

### W6 Content Export Tests
```
tests\unit\workers\test_w6_content_export.py ...   [100%]
======================== 3 passed, 1 warning in 0.75s =========================
```

### All W6/LinkerAndPatcher Tests
```
tests\unit\workers\test_tc_450_linker_and_patcher.py .................   [ 85%]
tests\unit\workers\test_w6_content_export.py ...                         [100%]
================ 20 passed, 947 deselected, 1 warning in 1.83s ================
```

## Verification

After the fix, the content_preview structure is:
- `content_preview/content/docs.aspose.org/...` (CORRECT)
- NOT `content_preview/content/content/docs.aspose.org/...` (WRONG)

The test at line 286 now correctly finds files:
```python
docs_file = content_preview_dir / "content/docs.aspose.org/3d/en/python/installation/index.md"
```

Where `content_preview_dir = temp_run_dir / "content_preview"` and `patch["path"]` provides the `content/` prefix.

## Files Modified

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `src/launch/workers/w6_linker_and_patcher/worker.py` | Bug fix | 867-869 |
| `tests/unit/workers/test_w6_content_export.py` | Test expectation update | 440-442 |

## Acceptance Criteria Verification

1. [x] Line 867 fixed to not double "content"
2. [x] Tests updated and passing (3/3 content export tests, 20/20 W6 tests)
3. [x] content_preview structure is `content_preview/content/...` (not `content_preview/content/content/...`)
4. [x] No regressions in W6 tests
5. [x] Patch path format verified (`patch["path"]` starts with `content/`)
6. [x] Evidence captured
