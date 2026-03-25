# TC-3212 Evidence — Placeholder Page Frontmatter Injection

**Date:** 2026-02-28
**Agent:** orchestrator / Agent B2
**Taskcard:** TC-3212_placeholder_page_frontmatter.md
**Status:** Done

---

## Summary

Extended `fix_frontmatter_missing()` in `src/launch/workers/w10_fixer/worker.py` to:

1. Inject `layout` and `permalink` into all pages (placeholder and non-placeholder) when frontmatter is missing.
2. Handle the `GATE_FRONTMATTER_REQUIRED_FIELD_MISSING` variant: parse existing partial frontmatter, add missing fields, rewrite without duplicating `---` markers.
3. Derive `layout` from the content path (`kb-howto` for KB paths, `post` for blog paths, `page` default).
4. Derive `permalink` from the path relative to `work/site/content/` (stripping subdomain component such as `kb.aspose.org`).

---

## New Helper Functions Added

Inserted between `write_frontmatter()` (line 287) and `compute_file_hash()` (formerly line 289) in `src/launch/workers/w10_fixer/worker.py`:

### `_extract_permalink_from_path(file_path, run_dir) -> str`

```python
def _extract_permalink_from_path(file_path: Path, run_dir: Path) -> str:
    """Derive a Hugo permalink from a content file path."""
    try:
        content_root = run_dir / "work" / "site" / "content"
        rel = file_path.relative_to(content_root)
        parts = rel.parts
        if parts and "." in parts[0]:  # strip subdomain e.g. "kb.aspose.org"
            rel = Path(*parts[1:])
        permalink = "/" + str(rel.with_suffix("")).replace("\\", "/") + "/"
        return permalink
    except ValueError:
        return f"/{file_path.stem}/"
```

### `_infer_layout_from_path(file_path) -> str`

```python
def _infer_layout_from_path(file_path: Path) -> str:
    """Infer Hugo layout from content file path."""
    path_str = str(file_path).replace("\\", "/").lower()
    if "/kb/" in path_str or "kb.aspose.org" in path_str:
        return "kb-howto"
    if "/blog/" in path_str or "blog.aspose.org" in path_str:
        return "post"
    return "page"
```

### `_infer_frontmatter_for_placeholder(file_path, run_dir) -> Dict[str, str]`

```python
def _infer_frontmatter_for_placeholder(file_path: Path, run_dir: Path) -> Dict[str, str]:
    """Infer layout and permalink for a placeholder page."""
    slug = file_path.stem.lower()
    if "placeholder" not in slug:
        return {}
    return {
        "layout": _infer_layout_from_path(file_path),
        "permalink": _extract_permalink_from_path(file_path, run_dir),
    }
```

---

## Updated `fix_frontmatter_missing()` — Key Changes

**Old behavior:** Always built `{"title": ..., "type": "docs"}` and prepended as new frontmatter. Never checked for existing frontmatter.

**New behavior:**
1. Calls `_infer_frontmatter_for_placeholder()` to detect placeholder pages.
2. Calls `parse_frontmatter(content)` to detect whether frontmatter already exists.
3. **Case 1 (`GATE_FRONTMATTER_REQUIRED_FIELD_MISSING` + existing frontmatter):** Merges placeholder fields and generic `layout`/`permalink` into existing dict, then rewrites — no duplicate `---` markers.
4. **Case 2 (all other cases):** Builds minimal frontmatter, merges placeholder fields, always adds `layout` and `permalink`, then writes.

---

## Test Results

```
tests/unit/workers/test_w10_scaffold_fix.py -v -k "placeholder or Placeholder"

collected 58 items / 54 deselected / 4 selected

tests\unit\workers\test_w10_scaffold_fix.py ....                         [100%]

4 passed, 54 deselected, 1 warning in 1.00s
```

Full file:
```
tests/unit/workers/test_w10_scaffold_fix.py

58 passed, 1 warning in 1.37s
```

(Up from 54 tests before this taskcard — 4 new tests added.)

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w10_fixer/worker.py` | Added 3 helpers (`_extract_permalink_from_path`, `_infer_layout_from_path`, `_infer_frontmatter_for_placeholder`); replaced `fix_frontmatter_missing()` with TC-3212 implementation |
| `tests/unit/workers/test_w10_scaffold_fix.py` | Added `fix_frontmatter_missing` + `parse_frontmatter` imports; appended `TestPlaceholderFrontmatter` class (4 tests) |

---

## TC-3450 Preservation Confirmed

The `EVENT_FIXER_STALE_PATH_DETECTED` constant (line ~96) and stale path guard block in `apply_fix()` (lines ~1555-1576) were not modified. All pre-existing tests continue to pass.
