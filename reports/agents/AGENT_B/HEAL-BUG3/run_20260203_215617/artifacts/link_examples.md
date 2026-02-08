# Link Transformation Examples

## Overview

This document demonstrates the link transformation behavior implemented in TASK-HEAL-BUG3. All examples show actual test cases from `test_w5_link_transformer.py`.

## Transformation Rules

### Rule 1: Cross-Section Links → Absolute URLs
Links between different sections (blog→docs, docs→reference, etc.) are transformed to absolute URLs.

### Rule 2: Same-Section Links → Relative (Preserved)
Links within the same section remain relative.

### Rule 3: Internal Anchors → Preserved
Internal page anchors (#something) are never transformed.

### Rule 4: External Links → Preserved
External URLs (https://) are never transformed.

---

## Example 1: Blog → Docs (Cross-Section)

**Before Transformation**:
```markdown
See the [Getting Started Guide](../../docs/3d/python/getting-started/).
```

**After Transformation**:
```markdown
See the [Getting Started Guide](https://docs.aspose.org/3d/python/getting-started/).
```

**Context**:
- Current Section: `blog`
- Target Section: `docs`
- Action: Transform to absolute URL ✓

**Test**: `test_transform_blog_to_docs_link()`

---

## Example 2: Docs → Reference (Cross-Section)

**Before Transformation**:
```markdown
See the [API Reference](../../reference/cells/python/api/).
```

**After Transformation**:
```markdown
See the [API Reference](https://reference.aspose.org/cells/python/api/).
```

**Context**:
- Current Section: `docs`
- Target Section: `reference`
- Action: Transform to absolute URL ✓

**Test**: `test_transform_docs_to_reference_link()`

---

## Example 3: KB → Docs (Cross-Section)

**Before Transformation**:
```markdown
Follow the [installation tutorial](../../docs/cells/python/installation/).
```

**After Transformation**:
```markdown
Follow the [installation tutorial](https://docs.aspose.org/cells/python/installation/).
```

**Context**:
- Current Section: `kb`
- Target Section: `docs`
- Action: Transform to absolute URL ✓

**Test**: `test_transform_kb_to_docs_link()`

---

## Example 4: Same-Section Link (Preserved)

**Before Transformation**:
```markdown
See the [Next Page](./next-page/).
```

**After Transformation**:
```markdown
See the [Next Page](./next-page/).
```

**Context**:
- Current Section: `docs`
- Target Section: `docs` (implied by relative path)
- Action: No transformation (same section) ✓

**Test**: `test_preserve_same_section_link()`

---

## Example 5: Internal Anchor (Preserved)

**Before Transformation**:
```markdown
Jump to [Installation](#installation).
```

**After Transformation**:
```markdown
Jump to [Installation](#installation).
```

**Context**:
- Current Section: `docs`
- Link Type: Internal anchor
- Action: No transformation ✓

**Test**: `test_preserve_internal_anchor()`

---

## Example 6: External Link (Preserved)

**Before Transformation**:
```markdown
Visit [Aspose](https://www.aspose.com/).
```

**After Transformation**:
```markdown
Visit [Aspose](https://www.aspose.com/).
```

**Context**:
- Current Section: `docs`
- Link Type: External URL
- Action: No transformation ✓

**Test**: `test_preserve_external_link()`

---

## Example 7: Multiple Links (Mixed Transformation)

**Before Transformation**:
```markdown
See the [Getting Started](../../docs/3d/python/getting-started/) guide.
Check the [API Reference](../../reference/3d/python/api/) for details.
Also see [Next Page](./next-page/) for more.
```

**After Transformation**:
```markdown
See the [Getting Started](https://docs.aspose.org/3d/python/getting-started/) guide.
Check the [API Reference](https://reference.aspose.org/3d/python/api/) for details.
Also see [Next Page](./next-page/) for more.
```

**Context**:
- Current Section: `blog`
- First Link: blog → docs (transform) ✓
- Second Link: blog → reference (transform) ✓
- Third Link: Same-section relative (preserve) ✓

**Test**: `test_transform_multiple_links()`

---

## Example 8: Section Index Link (No Slug)

**Before Transformation**:
```markdown
Visit [Docs Home](../../docs/3d/python/).
```

**After Transformation**:
```markdown
Visit [Docs Home](https://docs.aspose.org/3d/python/).
```

**Context**:
- Current Section: `blog`
- Target Section: `docs`
- Target Page: Section index (no slug)
- Action: Transform to section index URL ✓

**Test**: `test_transform_section_index_link()`

---

## Example 9: Nested Subsections

**Before Transformation**:
```markdown
See [Advanced Guide](../../docs/cells/python/developer-guide/advanced/features/).
```

**After Transformation**:
```markdown
See [Advanced Guide](https://docs.aspose.org/cells/python/developer-guide/advanced/features/).
```

**Context**:
- Current Section: `blog`
- Target Section: `docs`
- Subsections: `developer-guide/advanced`
- Slug: `features`
- Action: Transform with subsections preserved ✓

**Test**: `test_transform_with_subsections()`

---

## Example 10: Same Section (Docs → Docs)

**Before Transformation**:
```markdown
See [Another Guide](../../docs/cells/python/another-guide/).
```

**After Transformation**:
```markdown
See [Another Guide](../../docs/cells/python/another-guide/).
```

**Context**:
- Current Section: `docs`
- Target Section: `docs` (detected from URL pattern)
- Action: No transformation (same section) ✓

**Test**: `test_transform_docs_to_docs_link_not_transformed()`

---

## Example 11: Products → Docs (Cross-Section)

**Before Transformation**:
```markdown
Read the [Documentation](../../docs/words/python/guide/).
```

**After Transformation**:
```markdown
Read the [Documentation](https://docs.aspose.org/words/python/guide/).
```

**Context**:
- Current Section: `products`
- Target Section: `docs`
- Action: Transform to absolute URL ✓

**Test**: `test_transform_products_to_docs_link()`

---

## Example 12: Link Without Leading ../ (Direct Section)

**Before Transformation**:
```markdown
See [Guide](docs/3d/python/getting-started/).
```

**After Transformation**:
```markdown
See [Guide](https://docs.aspose.org/3d/python/getting-started/).
```

**Context**:
- Current Section: `blog`
- Target Section: `docs` (detected from pattern regardless of ../)
- Action: Transform to absolute URL ✓

**Test**: `test_transform_link_without_dots()`

---

## Edge Cases

### Edge Case 1: Malformed Link (Too Short)

**Input**:
```markdown
See [Bad Link](../../docs/).
```

**Output**:
```markdown
See [Bad Link](../../docs/).
```

**Behavior**: Keeps original link (can't parse), logs warning, no exception thrown.

**Test**: `test_transform_malformed_link_keeps_original()`

---

### Edge Case 2: No Links in Content

**Input**:
```markdown
This is plain text with no markdown links.
```

**Output**:
```markdown
This is plain text with no markdown links.
```

**Behavior**: Returns unchanged.

**Test**: `test_no_links_returns_unchanged()`

---

### Edge Case 3: Empty Content

**Input**:
```markdown

```

**Output**:
```markdown

```

**Behavior**: Returns empty string.

**Test**: `test_empty_content_returns_empty()`

---

## Section Detection Patterns

The transformer uses these regex patterns to detect target sections:

```python
section_patterns = {
    "docs": r"(?:\.\.\/)*docs\/",
    "reference": r"(?:\.\.\/)*reference\/",
    "products": r"(?:\.\.\/)*products\/",
    "kb": r"(?:\.\.\/)*kb\/",
    "blog": r"(?:\.\.\/)*blog\/",
}
```

**Pattern Explanation**:
- `(?:\.\.\/)*` - Matches zero or more `../` sequences (non-capturing)
- `docs\/` - Matches the literal section name followed by `/`
- This allows matching both `../../docs/` and `docs/` patterns

---

## URL Parsing Strategy

For a link like `../../docs/cells/python/developer-guide/features/`:

1. **Split by `/`**: `["", "..", "..", "docs", "cells", "python", "developer-guide", "features", ""]`
2. **Filter empty and `..`**: `["docs", "cells", "python", "developer-guide", "features"]`
3. **Remove section name**: `["cells", "python", "developer-guide", "features"]`
4. **Parse components**:
   - `family` = `cells` (index 0)
   - `platform` = `python` (index 1)
   - `subsections` = `["developer-guide"]` (indices 2:-1)
   - `slug` = `features` (index -1)

5. **Call TC-938**:
```python
build_absolute_public_url(
    section="docs",
    family="cells",
    locale="en",
    platform="python",
    slug="features",
    subsections=["developer-guide"],
)
```

6. **Result**: `https://docs.aspose.org/cells/python/developer-guide/features/`

---

## Transformation Statistics

| Test Category | Count | Status |
|--------------|-------|--------|
| Cross-Section Transformations | 5 | ✓ Passing |
| Preservation Tests | 3 | ✓ Passing |
| Complex Scenarios | 4 | ✓ Passing |
| Edge Cases | 3 | ✓ Passing |
| **Total** | **15** | **✓ All Passing** |

---

## Integration Impact

### Before Integration (BROKEN)
User on `blog.aspose.org` clicks: `[Guide](../../docs/3d/python/guide/)`
- Browser resolves: `blog.aspose.org/docs/3d/python/guide/`
- Result: **404 Not Found** ❌

### After Integration (WORKS)
User on `blog.aspose.org` clicks: `[Guide](https://docs.aspose.org/3d/python/guide/)`
- Browser resolves: `docs.aspose.org/3d/python/guide/`
- Result: **Page loads correctly** ✓

---

**End of Examples**
