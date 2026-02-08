# Template Discovery Audit - TC-966

## Executive Summary

**Fix Status**: SUCCESS - All 5 sections now discover templates from placeholder directories.

**Before fix**: 4 out of 5 sections returned 0 templates (only blog worked by accident)
**After fix**: All 5 sections discover 5-27 templates each from placeholder directories

## Before/After Comparison

| Section | Family | Before (templates) | After (templates) | Status |
|---------|--------|-------------------|-------------------|--------|
| docs.aspose.org | 3d | 0 | 27 | FIXED |
| products.aspose.org | cells | 0 | 5 | FIXED |
| reference.aspose.org | cells | 0 | 3 | FIXED |
| kb.aspose.org | cells | 0 | 10 | FIXED |
| blog.aspose.org | 3d | ~8 | 8 | NO REGRESSION |

## Root Cause Analysis

**Bug**: `enumerate_templates()` function (lines 855-870) searched for literal directory paths:
- `specs/templates/docs.aspose.org/3d/en/python/` (doesn't exist)
- `specs/templates/docs.aspose.org/3d/en/` (doesn't exist - fallback)

**Actual structure**: Templates are organized in placeholder directories:
- `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/`
- `specs/templates/docs.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/`
- `specs/templates/docs.aspose.org/3d/__POST_SLUG__/`

**Why blog worked**: The fallback logic (line 865) accidentally set `search_root` to `blog.aspose.org/3d/`, which happens to be the correct level to discover `__PLATFORM__/` and `__POST_SLUG__/` placeholder directories.

## Fix Implementation

**Code change**: Simplified lines 855-870 to search from family level:

```python
# BEFORE (buggy):
if subdomain == "blog.aspose.org":
    search_root = template_dir / subdomain / family / platform
else:
    search_root = template_dir / subdomain / family / locale / platform

if not search_root.exists():
    if subdomain == "blog.aspose.org":
        search_root = template_dir / subdomain / family
    else:
        search_root = template_dir / subdomain / family / locale
    if not search_root.exists():
        return []

# AFTER (fixed):
search_root = template_dir / subdomain / family
if not search_root.exists():
    return []
```

**Impact**: Now `rglob("*.md")` discovers all templates in any nested structure (placeholder or literal directories).

## Template Discovery Details

### docs.aspose.org/3d (27 templates)

Found templates in placeholder directories:
- `__LOCALE__/_index.md`
- `__LOCALE__/__PLATFORM__/_index.md`
- `__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md`
- `__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-standard.md`
- `__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-standard.md`
- `__LOCALE__/__PLATFORM__/__REFERENCE_SLUG__.md`
- `__LOCALE__/__CONVERTER_SLUG__/_index.md` (multiple variants)
- `__LOCALE__/__CONVERTER_SLUG__/__FORMAT_SLUG__.md`
- `__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps*.md` (multiple)
- `__POST_SLUG__/index.variant-*.md` (multiple blog-style variants)

### products.aspose.org/cells (5 templates)

Found templates in:
- `__LOCALE__/_index.md`
- `__LOCALE__/__PLATFORM__/_index.md`
- `__LOCALE__/__PLATFORM__/__CONVERTER_SLUG__/_index.md`
- `__LOCALE__/__CONVERTER_SLUG__/_index.md`
- `__LOCALE__/__CONVERTER_SLUG__/__FORMAT_SLUG__.md`

### reference.aspose.org/cells (3 templates)

Found templates in:
- `__LOCALE__/__PLATFORM__/_index.md`
- `__LOCALE__/__PLATFORM__/__REFERENCE_SLUG__.md`
- `__LOCALE__/__REFERENCE_SLUG__.md`

### kb.aspose.org/cells (10 templates)

Found templates in:
- `__LOCALE__/_index.md`
- `__LOCALE__/__PLATFORM__/_index.md`
- `__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-standard.md`
- `__LOCALE__/__CONVERTER_SLUG__/_index.variant-*.md` (multiple)
- `__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-*.md` (multiple)

### blog.aspose.org/3d (8 templates - no regression)

Found templates in:
- `__PLATFORM__/__POST_SLUG__/index.variant-minimal.md`
- `__PLATFORM__/__POST_SLUG__/index.variant-standard.md`
- `__POST_SLUG__/index.variant-enhanced*.md` (multiple)
- `__POST_SLUG__/index.variant-minimal.md`
- `__POST_SLUG__/index.variant-standard.md`
- `__POST_SLUG__/index.variant-steps-usecases.md`

**Note**: Blog correctly excludes `__LOCALE__` templates per TC-957 filter.

## Verification Steps

1. **Unit tests**: 7/7 tests passed
   - test_enumerate_templates_docs_section: PASS
   - test_enumerate_templates_products_section: PASS
   - test_enumerate_templates_reference_section: PASS
   - test_enumerate_templates_kb_section: PASS
   - test_enumerate_templates_blog_section: PASS
   - test_template_discovery_deterministic: PASS
   - test_enumerate_templates_all_sections_nonzero: PASS

2. **Manual verification**: All sections show >0 templates
   ```
   docs.aspose.org/3d: 27 templates
   products.aspose.org/cells: 5 templates
   reference.aspose.org/cells: 3 templates
   kb.aspose.org/cells: 10 templates
   blog.aspose.org/3d: 8 templates
   ```

3. **Determinism**: Template order stable across runs (sorted by template_path)

## Impact Assessment

**Before fix symptoms**:
- page_plan.json: 4/5 sections had `template_path: null`
- .md draft files: empty or minimal content for docs/products/reference/kb
- VFV: Validation errors for unfilled tokens
- Only blog section worked correctly

**After fix expected results**:
- page_plan.json: All sections have non-null template_path
- .md draft files: Complete content for all sections
- VFV: PASS status for all pilots
- All 5 sections use template-driven generation

## Next Steps

1. Run pilot-aspose-3d-foss-python to verify page_plan.json
2. Run VFV on both pilots to verify end-to-end content generation
3. Inspect .md drafts to confirm complete content
4. Complete 12-D self-review with evidence

## Acceptance Criteria Status

- [x] Template enumeration discovers templates for all 5 sections
- [x] Template count >0 for docs/products/reference/kb (not just blog)
- [x] Unit tests created with 6 test cases
- [x] All unit tests pass (7/7)
- [x] Manual verification: template enumeration produces non-zero results
- [ ] Pilot run: page_plan.json has non-null template_path (pending pilot execution)
- [ ] VFV re-run: exit_code=0, status=PASS (pending VFV execution)
- [x] No regression: blog section still works
- [x] Template discovery deterministic
- [x] Template discovery audit complete
