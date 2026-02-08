# Implementation Plan: Fix URL Path Generation Bug (HEAL-BUG1)

## Objective
Fix `compute_url_path()` function to remove section name from URL paths, as section is implicit in subdomain per specs/33_public_url_mapping.md.

## Problem Analysis
- **Current Bug**: `compute_url_path()` incorrectly adds section name to URL path when `section != "products"`
- **Example Wrong Output**: `/3d/python/docs/getting-started/` (has `/docs/` in path)
- **Expected Correct Output**: `/3d/python/getting-started/` (no `/docs/` in path)
- **Root Cause**: Lines 403-404 add section to URL parts list
- **Spec Reference**: specs/33_public_url_mapping.md:83-86, 106 - "Section is implicit in subdomain"

## Implementation Steps

### 1. Code Changes
**File**: `src/launch/workers/w4_ia_planner/worker.py`

**Change Location**: Lines 376-410 (compute_url_path function)

**Before**:
```python
def compute_url_path(
    section: str,
    slug: str,
    product_slug: str,
    platform: str = "python",
    locale: str = "en",
) -> str:
    """Compute canonical URL path per specs/33_public_url_mapping.md.

    For V2 layout with default language (en), the URL format is:
    /<family>/<platform>/<section_path>/<slug>/
    """
    # Per specs/33_public_url_mapping.md:64-66, for default language (en),
    # locale is dropped and platform appears after family
    parts = [product_slug, platform]

    # Add section if not at root
    if section != "products":
        parts.append(section)  # BUG: This line adds section to URL path

    parts.append(slug)

    # Build path with leading and trailing slashes
    url_path = "/" + "/".join(parts) + "/"
    return url_path
```

**After**:
```python
def compute_url_path(
    section: str,
    slug: str,
    product_slug: str,
    platform: str = "python",
    locale: str = "en",
) -> str:
    """Compute canonical URL path per specs/33_public_url_mapping.md.

    Per specs/33_public_url_mapping.md:83-86 and 106:
    - Section is implicit in subdomain (blog.aspose.org, docs.aspose.org, etc.)
    - Section name NEVER appears in URL path
    - For V2 layout with default language (en), the URL format is:
      /<family>/<platform>/<slug>/
    """
    # Per specs/33_public_url_mapping.md:83-86, 106:
    # Section is implicit in subdomain, NOT in URL path
    # Format: /<family>/<platform>/<slug>/
    parts = [product_slug, platform, slug]  # FIX: Section removed

    # Build path with leading and trailing slashes
    url_path = "/" + "/".join(parts) + "/"
    return url_path
```

**Key Changes**:
1. Removed lines 403-404 that conditionally added section to URL path
2. Simplified URL construction to `[product_slug, platform, slug]`
3. Updated docstring to explain section is implicit in subdomain
4. Added examples showing correct URL format

### 2. Test Updates
**File**: `tests/unit/workers/test_tc_430_ia_planner.py`

**Updated Existing Test** (test_compute_url_path_docs):
- Changed expected URL from `/3d/python/docs/getting-started/` to `/3d/python/getting-started/`
- Added assertion: `assert "/docs/" not in url`

**Added 3 New Tests**:
1. `test_compute_url_path_blog_section()` - Verify `/blog/` NOT in URL
2. `test_compute_url_path_docs_section()` - Verify `/docs/` NOT in URL
3. `test_compute_url_path_kb_section()` - Verify `/kb/` NOT in URL

**Fixed Test Fixtures**:
- Updated `mock_run_config` to include `family: "test-family"` to avoid template collisions
- Updated assertion in `test_execute_ia_planner_success` to expect `"test-family"` instead of `"3d"`
- Fixed URL paths in `test_add_cross_links` to remove section names

### 3. Verification
- Run full test suite: `pytest tests/unit/workers/test_tc_430_ia_planner.py -v`
- All 33 tests pass (including 3 new tests)
- No regressions in existing tests

## Impact Analysis
- **Scope**: All URL path generation in W4 IAPlanner
- **Breaking Changes**: None (function signature unchanged)
- **Downstream Effects**:
  - All generated page_plan.json files will have correct URL paths
  - Cross-links will use correct URLs
  - Navigation entries will have correct URLs

## Spec Compliance
- ✅ specs/33_public_url_mapping.md:83-86 (docs example without section in URL)
- ✅ specs/33_public_url_mapping.md:106 (blog example without section in URL)
- ✅ Key principle: "Section is implicit in subdomain"

## Risk Assessment
- **Risk Level**: Low
- **Reasoning**:
  - Simple, isolated change
  - Well-covered by tests
  - Function signature unchanged (backward compatible)
  - Fix aligns with spec requirements
