# SR-01 Changes

## File: src/launch/workers/w6_seo_optimizer/seo_metadata.py

### Change 1: Add `is_section_index` kwarg to `optimize_seo_metadata()`

**Before:**
```python
def optimize_seo_metadata(
    content: str,
    page: Dict[str, Any],
    keywords: List[str],
    product_name: str,
    platform: str,
    section: str = "docs",
    family: str = "",
    *,
    llm_client: Optional[Any] = None,
) -> str:
    """...
    - robots: "index, follow" (noindex for _index)
    """
```

**After:**
```python
def optimize_seo_metadata(
    content: str,
    page: Dict[str, Any],
    keywords: List[str],
    product_name: str,
    platform: str,
    section: str = "docs",
    family: str = "",
    *,
    is_section_index: bool = False,
    llm_client: Optional[Any] = None,
) -> str:
    """...
    - robots: "noindex, follow" for Hugo _index.md section indices; "index, follow" otherwise
    """
```

### Change 2: Fix robots determination logic

**Before (line 64):**
```python
robots = "noindex, follow" if slug in ("_index", "index") else "index, follow"
```

**After:**
```python
robots = "noindex, follow" if is_section_index else "index, follow"
```

---

## File: src/launch/workers/w6_seo_optimizer/worker.py

### Change 3: Pass `is_section_index` in `_optimize_one_page()`

**Before:**
```python
content = optimize_seo_metadata(
    content, page, all_keywords,
    product_name, platform,
    section=section, family=product_family,
)
```

**After:**
```python
content = optimize_seo_metadata(
    content, page, all_keywords,
    product_name, platform,
    section=section, family=product_family,
    is_section_index=(md_file.name == "_index.md"),
)
```

---

## File: tests/unit/workers/test_w6_seo_hardening.py

### Change 4: Strengthen `test_index_md_uses_parent_folder_name`

**Before:**
```python
assert "getting-started" in content
```

**After:**
```python
canonical = _get_frontmatter_field(content, "canonical")
assert canonical == "https://docs.aspose.org/3d/python/getting-started/"
robots = _get_frontmatter_field(content, "robots")
assert robots == "index, follow"
```

### Change 5: Strengthen `test_underscore_index_md_uses_parent_folder_name`

**Before:**
```python
assert "canonical:" in content
```

**After:**
```python
canonical = _get_frontmatter_field(content, "canonical")
assert canonical == "https://kb.aspose.org/3d/python/kb/"
robots = _get_frontmatter_field(content, "robots")
assert robots == "noindex, follow"
```

### Change 6: Add `test_regular_index_md_gets_index_robots`

New test asserting `index.md` (non-section-index) gets `robots: "index, follow"`.

### Change 7: Add `test_underscore_index_md_gets_noindex_robots`

New test asserting `_index.md` (Hugo section index) gets `robots: "noindex, follow"`.

---

## File: tests/unit/workers/test_w6_seo_optimizer.py

### Change 8: Update `test_index_page_gets_noindex`

Added `is_section_index=True` to the `optimize_seo_metadata()` call to match new API.

**Before:**
```python
result = optimize_seo_metadata(content, page, [], "Product", "python")
```

**After:**
```python
result = optimize_seo_metadata(content, page, [], "Product", "python", is_section_index=True)
```
