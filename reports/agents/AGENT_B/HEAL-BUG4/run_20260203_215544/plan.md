# HEAL-BUG4 Implementation Plan

## Task
Fix Template Discovery to Exclude Obsolete `__LOCALE__` Templates (Phase 0 - HIGHEST PRIORITY)

## Problem Statement
W4 IAPlanner's `enumerate_templates()` function discovers obsolete blog templates with `__LOCALE__` folder structure. While these templates have been deleted from the repo, the code doesn't have a filter to prevent them from being discovered if they existed. This could cause URL collisions and wrong content structure.

## Root Cause
The `enumerate_templates()` function (lines 824-923 in src/launch/workers/w4_ia_planner/worker.py) walks the template directory tree and discovers all .md files without filtering by path structure. For blog templates, it should skip any templates containing `__LOCALE__` in their path.

## Spec Evidence
- specs/33_public_url_mapping.md:100 states: "Blog uses filename-based i18n (no locale folder)"
- specs/33_public_url_mapping.md:88-96 shows blog structure: `content/blog.aspose.org/<family>/<platform>/...` (no locale folder)
- specs/07_section_templates.md documents template requirements per section

## Implementation Strategy

### 1. Code Changes
**File**: src/launch/workers/w4_ia_planner/worker.py
**Function**: `enumerate_templates()` (lines 824-923)

**Change**: Add filter in the template discovery loop (after line 867) to skip templates with `__LOCALE__` in their path ONLY for blog section.

**Implementation Pattern**:
```python
# Walk directory tree and find all .md files
for template_path in search_root.rglob("*.md"):
    if template_path.name == "README.md":
        continue

    # HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
    # Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n (no locale folder)
    if subdomain == "blog.aspose.org":
        path_str = str(template_path)
        if "__LOCALE__" in path_str:
            logger.debug(f"[W4] Skipping obsolete blog template with __LOCALE__: {path_str}")
            continue

    # Extract template metadata...
```

**Rationale**:
- Filter ONLY applies to blog section (subdomain == "blog.aspose.org")
- Docs, products, kb, and reference sections correctly use locale folders per spec
- Filter is surgical and minimal (single condition check)
- Uses logger.debug for observability without cluttering logs

### 2. Unit Tests
**File**: tests/unit/workers/test_w4_template_discovery.py (NEW FILE)

**Required Tests**:

1. **test_blog_templates_exclude_locale_folder()**
   - Purpose: Verify blog templates with `__LOCALE__` are filtered out
   - Setup: Create temp directory with mock blog templates including `__LOCALE__` paths
   - Action: Call enumerate_templates() with blog subdomain
   - Assert: No templates with `__LOCALE__` in path are returned

2. **test_blog_templates_use_platform_structure()**
   - Purpose: Verify blog templates use correct `__PLATFORM__` or `__POST_SLUG__` structure
   - Setup: Create temp directory with correct blog templates
   - Action: Call enumerate_templates() with blog subdomain
   - Assert: Templates with `__PLATFORM__` or `__POST_SLUG__` are discovered

3. **test_docs_templates_allow_locale_folder()**
   - Purpose: Verify non-blog sections are not over-filtered
   - Setup: Create temp directory with docs templates containing `__LOCALE__`
   - Action: Call enumerate_templates() with docs subdomain
   - Assert: Templates with `__LOCALE__` ARE returned (correct behavior for docs)

**Test Data Structure**:
```
temp_dir/
  blog.aspose.org/
    cells/
      __LOCALE__/              # OBSOLETE - should be filtered
        __PLATFORM__/
          __POST_SLUG__/
            index.md
      __PLATFORM__/            # CORRECT - should be discovered
        __POST_SLUG__/
          index.md
  docs.aspose.org/
    cells/
      __LOCALE__/              # CORRECT - should be discovered for docs
        __PLATFORM__/
          getting-started.md
```

### 3. Test Execution
```bash
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w4_template_discovery.py -v
```

Capture full output to evidence.md

### 4. Regression Testing
Ensure existing tests still pass:
```bash
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w4_ia_planner.py -v
```

## Acceptance Criteria
- [ ] `enumerate_templates()` filters `__LOCALE__` for blog section only
- [ ] 3 unit tests created and passing
- [ ] No regressions (existing W4 tests still pass)
- [ ] Evidence package complete in reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/
- [ ] Self-review complete with ALL dimensions ≥4/5
- [ ] Known Gaps section empty

## File Safety
- Read worker.py before modifying (DONE)
- Use Edit tool for modifications (never Write)
- Preserve existing code structure
- Add clear comments explaining the filter

## Timeline
1. Implement filter in worker.py (5 min)
2. Create unit tests (15 min)
3. Run tests and capture evidence (5 min)
4. Create documentation files (10 min)
5. Self-review (10 min)

**Total Estimated Time**: 45 minutes

## Dependencies
None - this is Phase 0 (root cause fix)

## Risks
- **Low Risk**: Filter is surgical and only affects blog template discovery
- **Mitigation**: Comprehensive unit tests for both blog and non-blog sections
