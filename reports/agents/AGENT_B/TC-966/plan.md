# TC-966 Implementation Plan

## Problem Analysis

**Root Cause**: W4 `enumerate_templates()` function (lines 855-870) searches for literal directory paths that don't exist:
- **Current code searches**: `specs/templates/docs.aspose.org/3d/en/python/`
- **What actually exists**: `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/`

**Impact**: 4 out of 5 sections (docs, products, reference, kb) return 0 templates, causing pages to have `template_path: null` and empty/broken content. Only blog works by accident because the fallback path finds placeholder directories.

## Directory Structure Evidence

From investigation, the template structure uses placeholders:
```
specs/templates/
  docs.aspose.org/3d/
    __LOCALE__/
      __PLATFORM__/
        __SECTION_PATH__/
          _index.variant-minimal.md
          _index.variant-standard.md
        __TOPIC_SLUG__.variant-standard.md
        _index.md
      __CONVERTER_SLUG__/
        __FORMAT_SLUG__.md
        __TOPIC_SLUG__.variant-steps.md
        _index.md
    __PLATFORM__/
      __POST_SLUG__/
        index.variant-minimal.md

  blog.aspose.org/3d/
    __PLATFORM__/
      __POST_SLUG__/
        index.variant-minimal.md
    __POST_SLUG__/
      index.variant-enhanced.md
```

## Solution Design

**Simple fix**: Remove the hardcoded path substitution logic. Instead, search from the family level and let `rglob("*.md")` discover all templates in any nested structure (placeholder or literal directories).

**Code change**:
- **BEFORE (lines 855-870)**: Complex conditional logic building paths with literal locale/platform values
- **AFTER**: Simple `search_root = template_dir / subdomain / family`

This works because:
1. The existing `rglob("*.md")` on line 873 already walks recursively
2. Template metadata extraction (lines 886-933) already handles any path structure
3. The blog filter (lines 880-884) already filters out `__LOCALE__` for blog subdomain

## Implementation Steps

1. **Simplify search_root logic** (lines 855-870)
   - Remove conditional path construction
   - Set `search_root = template_dir / subdomain / family`
   - Return empty list if not exists

2. **Verify existing logic still works**
   - `rglob("*.md")` discovers all templates recursively
   - README.md filtering still applies
   - Blog `__LOCALE__` filter still works
   - Template metadata extraction unchanged
   - Deterministic sorting preserved

3. **Create comprehensive unit tests**
   - Test all 5 sections (docs, products, reference, kb, blog)
   - Test determinism (multiple runs produce same order)
   - Test template counts >0 for non-blog sections

4. **Manual verification**
   - Run enumerate_templates() for each section
   - Verify template count >0
   - Verify template_path includes placeholder dirs

5. **Pilot verification**
   - Run pilot-aspose-3d-foss-python
   - Check page_plan.json has non-null template_path
   - Verify .md drafts have complete content

6. **VFV verification**
   - Run VFV on both pilots
   - Verify exit_code=0, status=PASS
   - Confirm all sections produce content

## Expected Outcomes

**Before fix**:
- docs.aspose.org/3d: 0 templates found
- products.aspose.org/3d: 0 templates found
- reference.aspose.org/3d: 0 templates found
- kb.aspose.org/3d: 0 templates found
- blog.aspose.org/3d: ~8 templates found (works by accident)

**After fix**:
- docs.aspose.org/3d: ~20+ templates found
- products.aspose.org/3d: ~10+ templates found
- reference.aspose.org/3d: ~5+ templates found
- kb.aspose.org/3d: ~10+ templates found
- blog.aspose.org/3d: ~8 templates found (no regression)

## Risk Mitigation

- **Minimal code change**: Only modifying 15 lines (855-870)
- **Existing logic preserved**: rglob, filtering, metadata extraction unchanged
- **Blog filter intact**: TC-957 __LOCALE__ exclusion still applies
- **Determinism maintained**: Template sorting by template_path unchanged
- **Comprehensive tests**: 6 test cases cover all sections + determinism
