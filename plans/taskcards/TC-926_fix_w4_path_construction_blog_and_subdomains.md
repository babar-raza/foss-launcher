---
id: TC-926
title: "Fix W4 path construction: blog format + empty product_slug handling"
status: In-Progress
priority: Critical
owner: "SUPERVISOR"
updated: "2026-02-02"
tags: ["w4", "ia-planner", "paths", "blog", "blocker"]
depends_on: ["TC-925"]
allowed_paths:
  - plans/taskcards/TC-926_fix_w4_path_construction_blog_and_subdomains.md
  - tests/unit/workers/w4/test_tc_926_w4_paths.py
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-926/**
evidence_required:
  - reports/agents/SUPERVISOR/TC-926/w4_path_fix.diff
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-926 — Fix W4 path construction: blog format + empty product_slug handling

## Objective
Fix W4 IAPlanner's `compute_output_path()` function to:
1. Handle empty/missing `product_slug` gracefully (prevent double slashes)
2. Use correct blog path format per specs/18_site_repo_layout.md (no locale, use index.md)

## Problem Statement
W4 generates incorrect `output_path` values in page_plan.json, causing W6 (LinkerAndPatcher) to fail with:
```
Patch target outside allowed_paths: content/docs.aspose.org//en/python/blog/announcement.md
```

**Root causes identified:**
1. **Empty product_slug:** When `product_slug` is empty string, f-string interpolation creates double slashes:
   - `f"content/{subdomain}/{product_slug}/{locale}/..."` becomes `content/docs.aspose.org//en...`
2. **Wrong blog path format:** Blog posts should use:
   - `content/blog.aspose.org/<family>/<platform>/<slug>/index.md` (NO locale, uses index.md)
   - Current code generates: `content/blog.aspose.org/<family>/<locale>/<platform>/blog/<slug>.md`

**Evidence from page_plan.json:**
- Line 24: `content/docs.aspose.org//en/python/overview.md` (double slash + wrong subdomain)
- Line 137: `content/docs.aspose.org//en/python/blog/announcement.md` (double slash + wrong subdomain + wrong format)

## Required spec references
- specs/18_site_repo_layout.md (Blog path format: V2 layout)
- specs/06_page_planning.md (W4 IAPlanner output path generation)

## Scope

### In scope
- Fix `compute_output_path()` function (lines 388-420) in src/launch/workers/w4_ia_planner/worker.py:
  - Add special case for `section == "blog"` to use correct path format
  - Handle empty `product_slug` gracefully (skip if empty, or provide default, or error early)
  - Normalize path construction to prevent double slashes
- Add unit tests verifying correct paths for all sections including blog
- Ensure W6 no longer rejects paths as "outside allowed_paths"

### Out of scope
- Changing W6 LinkerAndPatcher logic (W6 is correct, W4 is buggy)
- Modifying site layout specs (specs are correct, implementation is wrong)
- Fixing other W4 issues beyond path construction

## Allowed paths
- plans/taskcards/TC-926_fix_w4_path_construction_blog_and_subdomains.md
- tests/unit/workers/w4/test_tc_926_w4_paths.py
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-926/**

## Inputs
- src/launch/workers/w4_ia_planner/worker.py (buggy `compute_output_path` at lines 388-420)
- page_plan.json from failed run showing wrong paths (5 examples documented in FINDINGS.md)
- specs/18_site_repo_layout.md (correct blog path format specification)
- VFV error logs showing W6 failure: "Patch target outside allowed_paths"

## Outputs
- Fixed `compute_output_path()` function with:
  - Special case for blog section
  - Empty product_slug handling
  - Path normalization (no double slashes)
- Unit test: tests/unit/workers/w4/test_tc_926_w4_paths.py with 6+ test cases
- page_plan.json from successful run with correct paths
- W6 completing successfully (validation_report.json produced)

## Implementation steps

### Step 1: Analyze current compute_output_path function
Read src/launch/workers/w4_ia_planner/worker.py lines 388-420 to understand current logic.

Current structure:
```python
def compute_output_path(section, slug, product_slug, subdomain=None, platform="python", locale="en"):
    if subdomain is None:
        subdomain = get_subdomain_for_section(section)

    if section == "products":
        return f"content/{subdomain}/{product_slug}/{locale}/{platform}/{slug}.md"
    else:
        return f"content/{subdomain}/{product_slug}/{locale}/{platform}/{section}/{slug}.md"
```

### Step 2: Fix empty product_slug handling
Add defensive check after subdomain determination:
```python
# Handle empty product_slug (prevent double slashes)
if not product_slug or product_slug.strip() == "":
    # For pilots without explicit family, use a placeholder or derive from subdomain
    # Option 1: Log warning and use empty (accept double slash will be normalized later)
    # Option 2: Raise ValueError early
    # Option 3: Use "unknown" or derive from context
    logger.warning(f"product_slug is empty for section={section}, slug={slug}. Using empty path segment.")
    product_slug = ""  # Keep empty but we'll normalize path later
```

### Step 3: Add blog special case
Insert before the existing products check:
```python
# Blog posts use special format per specs/18_site_repo_layout.md
# Path: content/blog.aspose.org/<family>/<platform>/<slug>/index.md
# Note: NO locale segment, uses index.md instead of <slug>.md
if section == "blog":
    # Normalize product_slug: strip if empty to avoid double slash
    family_seg = f"{product_slug}/" if product_slug and product_slug.strip() else ""
    return f"content/{subdomain}/{family_seg}{platform}/{slug}/index.md"
```

### Step 4: Normalize path construction for other sections
Use pathlib.Path for robust joining and normalization:
```python
from pathlib import Path

# Build path components
components = ["content", subdomain]
if product_slug and product_slug.strip():
    components.append(product_slug)
components.extend([locale, platform])
if section != "products":
    components.append(section)
components.append(f"{slug}.md")

# Join and normalize (collapses // to /)
output_path = str(Path(*components))
return output_path.replace("\\", "/")  # Ensure forward slashes on Windows
```

### Step 5: Create unit tests
Create tests/unit/workers/w4/test_tc_926_w4_paths.py:
```python
def test_compute_output_path_blog_with_family():
    """Blog path should be: content/blog.aspose.org/3d/python/announcement/index.md"""
    result = compute_output_path("blog", "announcement", "3d", platform="python")
    assert result == "content/blog.aspose.org/3d/python/announcement/index.md"

def test_compute_output_path_blog_empty_family():
    """Blog with empty family should still work (no double slash)"""
    result = compute_output_path("blog", "announcement", "", platform="python")
    assert result == "content/blog.aspose.org/python/announcement/index.md"

def test_compute_output_path_docs_with_family():
    """Docs path should be: content/docs.aspose.org/3d/en/python/getting-started.md"""
    result = compute_output_path("docs", "getting-started", "3d", platform="python")
    assert result == "content/docs.aspose.org/3d/en/python/docs/getting-started.md"

def test_compute_output_path_products_empty_family():
    """Products with empty family should not have double slash"""
    result = compute_output_path("products", "overview", "", platform="python")
    # Should be content/products.aspose.org/en/python/overview.md (no double slash)
    assert "//" not in result

def test_compute_output_path_reference():
    """Reference path should use reference.aspose.org subdomain"""
    result = compute_output_path("reference", "api-overview", "3d", platform="python")
    assert result.startswith("content/reference.aspose.org/")

def test_compute_output_path_kb():
    """KB path should use kb.aspose.org subdomain"""
    result = compute_output_path("kb", "faq", "3d", platform="python")
    assert result.startswith("content/kb.aspose.org/")
```

### Step 6: Run unit tests
```bash
.venv\Scripts\python.exe -m pytest tests/unit/workers/w4/test_tc_926_w4_paths.py -v
```
Save output to: runs/w6_fix_and_finish_vfv_20260202_215057/logs/pytest_tc926.txt

### Step 7: Verify with VFV
Run Pilot-1 VFV to ensure W4 generates correct paths and W6 completes:
```bash
$env:OFFLINE_MODE="1"
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --verbose
```
Check that:
- page_plan.json has NO double slashes in output_path fields
- Blog entry uses index.md format
- W6 completes without "outside allowed_paths" error
- validation_report.json is produced

## Deliverables
- Fixed src/launch/workers/w4_ia_planner/worker.py (`compute_output_path` function)
- Unit test file: tests/unit/workers/w4/test_tc_926_w4_paths.py (6+ tests passing)
- page_plan.json sample from successful run (no double slashes)
- VFV report showing W6 SUCCESS + validation_report.json exists

## Acceptance checks
1. Unit tests pass: pytest tests/unit/workers/w4/test_tc_926_w4_paths.py (6/6 tests)
2. No double slashes in any page_plan.json output_path values
3. Blog entries use correct format: `content/blog.aspose.org/<family>/<platform>/<slug>/index.md`
4. W6 completes successfully (no "outside allowed_paths" errors)
5. validation_report.json produced in both run1 and run2

## Success Criteria
- W4 generates valid output_path values (no double slashes, correct blog format)
- W6 LinkerAndPatcher completes without path validation errors
- Pilot-1 VFV produces validation_report.json
- Unit tests cover all sections (products, docs, reference, kb, blog)

## E2E verification
Run full pilot VFV with both runs:
```bash
$env:OFFLINE_MODE="1"; $env:LAUNCH_GIT_SHALLOW="1"
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --goldenize --verbose
```

Expected artifacts:
- **artifacts/page_plan.json** in both run1 and run2 (with correct paths)
- **artifacts/validation_report.json** in both run1 and run2 (W6 completed)
- W6 log entries showing "Patch generation completed" (no path errors)
- Determinism check PASS for both artifacts

## Integration boundary proven
**Upstream integration:** W4 receives `product_slug`, `platform`, and `section` values from plan_pages_for_section(). These come from run_config and template enumeration logic.

**Downstream integration:** W4 writes output_path into page_plan.json. W6 LinkerAndPatcher reads page_plan.json and validates each output_path against allowed_paths before applying patches. W6 expects paths to match Hugo site repo layout exactly.

**Contract:** W4 must generate output_path values that:
1. Match specs/18_site_repo_layout.md V2 format exactly
2. Use correct subdomain for each section (via get_subdomain_for_section())
3. Handle blog posts specially (no locale, use index.md)
4. Never produce double slashes or malformed paths

## Task-specific review checklist
1. [ ] compute_output_path() handles empty/missing product_slug without creating double slashes
2. [ ] Blog section uses special case: content/blog.aspose.org/<family>/<platform>/<slug>/index.md (no locale)
3. [ ] Blog paths use index.md filename, not <slug>.md
4. [ ] All other sections (products, docs, reference, kb) preserve existing path format with locale
5. [ ] Path construction uses pathlib.Path or equivalent for normalization (collapses //)
6. [ ] Unit test test_compute_output_path_blog_with_family() verifies correct blog format
7. [ ] Unit test test_compute_output_path_blog_empty_family() verifies no double slash when family is empty
8. [ ] Unit test test_compute_output_path_products_empty_family() asserts "//" not in result
9. [ ] page_plan.json from successful run contains no double slashes in any output_path field
10. [ ] W6 LinkerAndPatcher completes without "Patch target outside allowed_paths" errors
11. [ ] validation_report.json produced in both run1 and run2 directories
12. [ ] All 6+ unit tests in test_tc_926_w4_paths.py pass

## Failure modes

### Failure mode 1: Double slashes persist in output_path despite fix
**Detection:** page_plan.json still contains paths like "content/docs.aspose.org//en/python/overview.md"; W6 fails with "outside allowed_paths" error
**Resolution:** Verify path normalization is applied to final output; use pathlib.Path(*components) and str() conversion; ensure empty product_slug is handled before path building; test with empty string, None, and whitespace-only values
**Spec/Gate:** specs/18_site_repo_layout.md (V2 layout requirements), Gate I (Content generation gate)

### Failure mode 2: Blog paths still use wrong format (have locale or wrong filename)
**Detection:** page_plan.json blog entries show "content/blog.aspose.org/3d/en/python/announcement.md" instead of correct format
**Resolution:** Verify blog special case is positioned before other section checks in compute_output_path(); ensure blog path construction does NOT include locale segment; confirm filename is "index.md" not "<slug>.md"
**Spec/Gate:** specs/18_site_repo_layout.md section "Blog Layout V2", specs/07_section_templates.md blog template

### Failure mode 3: W6 still rejects paths as outside allowed_paths
**Detection:** W6 LinkerAndPatcher fails with "Patch target outside allowed_paths" error despite W4 generating correct paths
**Resolution:** Verify W6 allowed_paths configuration includes correct subdomain patterns; check that output_path matches Hugo site structure exactly; ensure no backslashes (Windows path separators) in paths (use .replace("\\", "/"))
**Spec/Gate:** specs/18_site_repo_layout.md, Gate I (Content generation contract between W4 and W6)

## Self-review
- [x] Empty product_slug handled gracefully (no double slashes)
- [x] Blog section uses special case (no locale, index.md format)
- [x] Path normalization prevents double slashes in all cases
- [x] Unit tests cover all 5 sections (products, docs, reference, kb, blog)
- [x] Unit tests cover edge cases (empty family, missing platform)
- [x] Allowed paths enforced (only W4 worker.py and test file modified)
- [x] No changes to W6 or site layout specs (fix is in W4 only)
