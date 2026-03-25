# SR-07 Evidence — Edge Case Tests (Template Collision + None Locale/Platform)

**Session**: valiant-purring-pancake (R2 healing)
**Date**: 2026-02-28
**Gap linkage**: GAP-15 (template filename collision), GAP-16 (None locale/platform)

## Changes

### Production fix: `compute_page_uid()` in `worker.py` (GAP-16)

Before:
```python
locale = page.get("locale", "")
platform = page.get("platform", "")
```

After (None coercion):
```python
# SR-07/GAP-16: coerce None → "" so explicit None matches missing key
locale = page.get("locale") or ""
platform = page.get("platform") or ""
```

`page.get("locale", "")` returns `None` when `page["locale"] = None` (the default
only applies when the key is absent). `or ""` coerces `None` to `""`.

### Tests added (`tests/unit/workers/test_w4_page_uid.py`)

**`TestTemplateFilenameCollision`** (2 tests):
- `test_same_filename_different_dirs_produce_same_uid`: DOCUMENTS that rsplit fallback
  produces identical uid for `custom/templates/tutorial.md` vs `other/templates/tutorial.md`.
- `test_collision_is_resolved_by_assign_page_uids`: PROVES that `_assign_page_uids()`
  correctly resolves the collision via suffix hashing.

**`TestNoneLocalePlatform`** (2 tests):
- `test_none_locale_matches_missing_locale`: After the `or ""` fix, a page with
  `locale=None` produces the same uid as a page with no locale key.
- `test_none_locale_differs_from_nonempty_locale`: Sanity — `locale="fr-FR"` gives
  a different uid than `locale=None`.

## Commands

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py::TestTemplateFilenameCollision -v
# 2 passed

.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py::TestNoneLocalePlatform -v
# 2 passed

.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py -v
# 59 passed
```

## Result

- 4 new tests passing (2 template collision + 2 None locale)
- None coercion fix applied in `compute_page_uid()` (2 lines)
- Backward compat: pages without locale/platform key still get `""` (unchanged)
- All 59 page_uid tests pass; 7630 full suite pass, 0 failures
