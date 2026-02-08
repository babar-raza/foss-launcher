# HEAL-BUG4 Changes Documentation

## Summary
Fixed W4 IAPlanner's `enumerate_templates()` function to exclude obsolete blog templates with `__LOCALE__` folder structure, preventing URL collisions and ensuring correct content structure per spec.

---

## Changes Made

### 1. Code Change: src/launch/workers/w4_ia_planner/worker.py

**Function Modified**: `enumerate_templates()` (lines 824-923)

**Location**: After line 875 (after README.md filter, before template metadata extraction)

**Change Type**: Added defensive filter

**Lines Added**: 876-884

**Code Added**:
```python
# HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
# Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n (no locale folder)
# Blog templates should use __PLATFORM__/__POST_SLUG__ structure, not __LOCALE__
if subdomain == "blog.aspose.org":
    path_str = str(template_path)
    if "__LOCALE__" in path_str:
        logger.debug(f"[W4] Skipping obsolete blog template with __LOCALE__: {path_str}")
        continue
```

**Rationale**:
- **Why here?** Filter must execute early in the loop, after basic file type checks (README) but before any template processing
- **Why blog only?** Per specs/33_public_url_mapping.md:100, only blog uses filename-based i18n. Docs/reference/kb/products correctly use locale folders.
- **Why string check?** Simple, fast, and deterministic. No regex overhead needed for literal string matching.
- **Why debug log?** Provides observability without cluttering normal logs. Critical for debugging template discovery issues.

**Impact**:
- Prevents discovery of obsolete blog templates with `__LOCALE__` in their path
- No impact on non-blog sections (docs, reference, kb, products)
- No impact on blog templates with correct structure (`__PLATFORM__/__POST_SLUG__`)
- Minimal performance impact (one string comparison per template file)

---

### 2. New Test File: tests/unit/workers/test_w4_template_discovery.py

**Location**: New file created

**Purpose**: Comprehensive unit testing for template discovery filter

**Tests Created**: 6 tests total

#### Core Tests (Required by Task)

1. **test_blog_templates_exclude_locale_folder()**
   - Verifies blog templates with `__LOCALE__` are filtered out
   - Creates mock blog templates with obsolete structure
   - Asserts no `__LOCALE__` in discovered template paths
   - Evidence: Filter works correctly

2. **test_blog_templates_use_platform_structure()**
   - Verifies blog templates with correct structure are discovered
   - Creates mock blog templates with `__PLATFORM__/__POST_SLUG__`
   - Asserts templates with `__POST_SLUG__` are found
   - Evidence: Filter doesn't over-filter correct templates

3. **test_docs_templates_allow_locale_folder()**
   - Verifies non-blog sections are not over-filtered
   - Creates mock docs templates with `__LOCALE__` in filename
   - Asserts docs templates with `__LOCALE__` are discovered
   - Evidence: Filter is blog-specific, doesn't affect other sections

#### Additional Tests (Comprehensive Coverage)

4. **test_readme_files_always_excluded()**
   - Verifies README.md files are excluded (existing behavior)
   - Ensures filter doesn't interfere with README filtering

5. **test_empty_directory_returns_empty_list()**
   - Verifies graceful handling of non-existent paths (existing behavior)
   - Ensures filter doesn't break error handling

6. **test_template_deterministic_ordering()**
   - Verifies deterministic behavior per specs/10_determinism_and_caching.md
   - Ensures filter maintains stable ordering

**Test Fixture**: `temp_template_dir`
- Creates temporary directory structure with realistic template hierarchy
- Includes both obsolete and correct templates
- Mirrors actual template structure in specs/templates/

**Test Coverage**:
- ✅ Positive cases (correct templates discovered)
- ✅ Negative cases (obsolete templates filtered)
- ✅ Edge cases (empty dirs, README files)
- ✅ Cross-section behavior (blog vs docs)
- ✅ Determinism and stability

---

## What Was NOT Changed

### Functions Not Modified
- `plan_pages_for_section()` - Page planning logic unchanged
- `compute_url_path()` - URL path computation unchanged (unrelated changes exist but are out of scope)
- `compute_output_path()` - Output path computation unchanged
- `classify_templates()` - Template classification unchanged
- `select_templates_with_quota()` - Quota enforcement unchanged
- `fill_template_placeholders()` - Placeholder filling unchanged

### Behavior Preserved
- Template discovery for docs/reference/kb/products sections unchanged
- Template sorting and deterministic ordering preserved
- README.md filtering logic preserved
- Empty directory handling preserved
- Template metadata extraction unchanged
- Template classification by variant unchanged

---

## Why These Changes Fix the Bug

### Root Cause
The `enumerate_templates()` function walks the template directory tree and discovers ALL .md files without filtering by path structure. If obsolete templates with `__LOCALE__` folder structure existed, they would be discovered and could cause:
- URL collisions (multiple templates mapping to same URL)
- Wrong content structure (blog posts with locale folders)
- Violation of spec (specs/33_public_url_mapping.md:100)

### How the Fix Works
1. **Early Filtering**: Check happens immediately after README filter, before any processing
2. **Section-Specific**: Only applies to blog.aspose.org subdomain
3. **Simple Detection**: String comparison for `__LOCALE__` in path
4. **Defensive**: Even if obsolete templates are deleted, code prevents future mistakes

### Why This Prevents URL Collisions
Blog templates with `__LOCALE__` folder structure would generate URLs like:
- Obsolete: `content/blog.aspose.org/cells/__LOCALE__/python/__POST_SLUG__/index.md`
  - Could map to: `/cells/python/post-title/` (locale dropped per spec)

Blog templates with correct structure generate:
- Correct: `content/blog.aspose.org/cells/python/__POST_SLUG__/index.md`
  - Maps to: `/cells/python/post-title/`

Both would map to the same URL → **COLLISION**

By filtering out obsolete templates, only correct templates are discovered, preventing collisions.

---

## Verification of Correctness

### Spec Compliance

**specs/33_public_url_mapping.md:100**:
> "Blog uses filename-based i18n (no locale folder)"

✅ Filter enforces this rule by excluding `__LOCALE__` in blog template paths

**specs/33_public_url_mapping.md:88-96**:
> Blog filesystem layout (V2):
> ```
> content/blog.aspose.org/<family>/<platform>/
>   ├── _index.md
>   ├── <year>-<month>-<day>-<slug>.md
> ```

✅ Filter allows this structure (no `__LOCALE__` in path)

**specs/07_section_templates.md:165-177**:
> Non-blog: specs/templates/<subdomain>/<family>/<locale>/<platform>/...
> Blog: specs/templates/blog.aspose.org/<family>/<platform>/...

✅ Filter correctly distinguishes blog from non-blog sections

### Test Evidence
- ✅ 6/6 unit tests passing
- ✅ Filter correctly skips obsolete templates (debug log confirms)
- ✅ Filter correctly allows correct templates (discovery confirms)
- ✅ Filter doesn't affect non-blog sections (docs test confirms)

### Code Review Checklist
- ✅ Minimal change (8 lines added)
- ✅ Clear comments explaining purpose and spec reference
- ✅ Consistent with existing code style
- ✅ Uses existing logging patterns (logger.debug)
- ✅ No new dependencies or imports needed
- ✅ Deterministic behavior (no randomness)
- ✅ No performance degradation (simple string check)

---

## Migration Path

### For Existing Repositories
If a repository has obsolete blog templates with `__LOCALE__` structure:
1. W4 IAPlanner will now skip them automatically
2. Debug logs will show which templates are being skipped
3. Repository owner can delete obsolete templates at leisure
4. No immediate action required - filter provides safety

### For New Repositories
1. Follow specs/33_public_url_mapping.md:88-96 for blog structure
2. Use `__PLATFORM__/__POST_SLUG__` structure, not `__LOCALE__`
3. Filter will automatically validate structure during discovery

### For Template Authors
When creating new blog templates:
- ✅ Use: `specs/templates/blog.aspose.org/<family>/<platform>/__POST_SLUG__/`
- ❌ Avoid: `specs/templates/blog.aspose.org/<family>/__LOCALE__/<platform>/`

Filter will catch mistakes during template discovery.

---

## Risks and Mitigation

### Risk 1: Over-filtering
**What if**: Legitimate blog templates have `__LOCALE__` in their *filename* (not folder structure)?

**Mitigation**:
- Filter checks entire path string, so it catches both folder names and filenames
- This is actually DESIRED behavior per spec (blog should not use locale anywhere)
- If filename-based locale is needed, use `.lang.md` suffix per Hugo conventions

**Evidence**: Test `test_blog_templates_use_platform_structure()` verifies correct templates are still discovered

### Risk 2: Under-filtering
**What if**: Obsolete templates don't have exact string `__LOCALE__` but use variations like `__LANG__`?

**Mitigation**:
- Spec explicitly uses `__LOCALE__` placeholder (specs/33_public_url_mapping.md)
- Real-world deleted templates all used `__LOCALE__` (git status confirms)
- If variations exist, they're not following spec and should be fixed

**Evidence**: Git status shows all deleted templates used exact `__LOCALE__` string

### Risk 3: Performance
**What if**: String check on every template file degrades performance?

**Mitigation**:
- String comparison is O(n) where n = path length (~100 chars)
- Filter only applies to blog section
- Typical repo has <100 blog templates
- Total overhead: <10ms

**Evidence**: Tests complete in <1 second, no performance concerns

---

## Future Enhancements

### Potential Improvements (Out of Scope)
1. Validate template structure against spec schema
2. Emit warning events for obsolete templates (not just debug logs)
3. Auto-suggest correct template path when obsolete template found
4. Add template linter to pre-commit hooks

These are enhancements beyond the bug fix and are not required for HEAL-BUG4.

---

## Summary

**What**: Added 8-line filter to skip obsolete blog templates with `__LOCALE__` folder structure

**Why**: Prevent URL collisions and enforce spec compliance (specs/33_public_url_mapping.md:100)

**How**: String check in `enumerate_templates()` loop, blog-specific, before template processing

**Impact**:
- ✅ Fixes root cause of URL collision bug
- ✅ No impact on non-blog sections
- ✅ No performance degradation
- ✅ Comprehensive test coverage (6 tests)
- ✅ Backward compatible (doesn't break existing behavior)

**Verification**: All tests passing, spec-compliant, minimal code change
