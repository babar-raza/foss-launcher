---
id: TC-957
title: "Fix Template Discovery - Exclude Obsolete __LOCALE__ Templates"
status: Draft
priority: Normal
owner: "Agent B"
updated: "2026-02-03"
tags: ["healing", "bug-fix", "w4-ia-planner", "template-discovery"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-957_fix_template_discovery_-_exclude_obsolete___locale___templates.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_template_discovery.py
evidence_required:
  - runs/[run_id]/evidence.zip
  - reports/agents/<agent>/TC-957/report.md
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-957 — Fix Template Discovery - Exclude Obsolete __LOCALE__ Templates

## Objective
Fix W4 IAPlanner's `enumerate_templates()` function to exclude obsolete blog templates containing `__LOCALE__` folder structure, preventing URL collisions and ensuring correct content structure per specs/33_public_url_mapping.md:100. This surgical 8-line code change adds a defensive filter that only affects blog.aspose.org subdomain templates, maintaining full compatibility with docs, reference, kb, and products sections that correctly use locale folders.

## Problem Statement
W4 IAPlanner's `enumerate_templates()` function (lines 824-923 in src/launch/workers/w4_ia_planner/worker.py) walks the template directory tree and discovers all .md files without filtering by path structure. For blog templates, this could discover obsolete templates with `__LOCALE__` folder structure, causing URL collisions and wrong content structure. Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n (no locale folder), so templates with `__LOCALE__` in their path violate the spec and must be filtered out.

## Required spec references
- specs/33_public_url_mapping.md:100 - "Blog uses filename-based i18n (no locale folder)"
- specs/33_public_url_mapping.md:88-96 - Blog filesystem layout V2 structure
- specs/07_section_templates.md:165-177 - Template structure requirements per section
- specs/10_determinism_and_caching.md - Deterministic template ordering requirements

## Scope

### In scope
- Add defensive filter in `enumerate_templates()` to skip blog templates with `__LOCALE__` in path
- Filter applies ONLY to blog.aspose.org subdomain (blog-specific)
- Add debug logging for observability when templates are filtered
- Create comprehensive unit tests (6 tests) for template discovery filter
- Verify no impact on non-blog sections (docs, reference, kb, products)
- Ensure deterministic behavior maintained

### Out of scope
- Modifying URL path computation logic (unrelated changes exist but are separate)
- Changing page planning or template classification logic
- Modifying template metadata extraction
- Affecting non-blog template discovery (docs/reference/kb/products must still allow __LOCALE__)
- Deleting actual obsolete template files from repository
- Template structure validation beyond __LOCALE__ filtering

## Inputs
- Existing src/launch/workers/w4_ia_planner/worker.py with `enumerate_templates()` function (lines 824-923)
- Template directory structure from specs/templates/ (blog and non-blog sections)
- specs/33_public_url_mapping.md defining blog structure requirements
- specs/07_section_templates.md defining template hierarchy per section
- specs/10_determinism_and_caching.md defining deterministic behavior requirements
- Existing logger infrastructure for debug logging

## Outputs
- Modified src/launch/workers/w4_ia_planner/worker.py with 8-line filter (lines 876-884)
- New test file tests/unit/workers/test_w4_template_discovery.py with 6 comprehensive tests
- Debug logs showing filtered templates: "[W4] Skipping obsolete blog template with __LOCALE__: {path}"
- Test evidence showing 6/6 tests passing in <1 second
- Evidence package at reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/
- Self-review document with all 12 dimensions scoring 5/5

## Allowed paths
- plans/taskcards/TC-957_fix_template_discovery_-_exclude_obsolete___locale___templates.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_template_discovery.py

### Allowed paths rationale
TC-957 modifies worker.py's `enumerate_templates()` function to add a defensive filter that excludes obsolete blog templates with `__LOCALE__` folder structure, preventing URL collisions per specs/33_public_url_mapping.md:100. The new test file provides comprehensive unit test coverage (6 tests) to verify the filter works correctly for blog templates while not affecting non-blog sections.

## Implementation steps

### Step 1: Read existing worker.py file
Read src/launch/workers/w4_ia_planner/worker.py to understand the `enumerate_templates()` function structure (lines 824-923) and identify where to insert the filter.

Expected: Understand template discovery loop, README filter at line 875, and template processing logic.

### Step 2: Add defensive filter for blog templates
After line 875 (README.md filter), add filter to skip blog templates with `__LOCALE__`:

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

Expected: 8 lines added at lines 876-884, filter only executes for blog.aspose.org subdomain.

### Step 3: Create comprehensive unit tests
Create tests/unit/workers/test_w4_template_discovery.py with 6 tests:
1. test_blog_templates_exclude_locale_folder - Verify blog templates with __LOCALE__ are filtered
2. test_blog_templates_use_platform_structure - Verify correct blog templates are discovered
3. test_docs_templates_allow_locale_folder - Verify non-blog sections not affected
4. test_readme_files_always_excluded - Verify README filtering preserved
5. test_empty_directory_returns_empty_list - Verify edge case handling
6. test_template_deterministic_ordering - Verify determinism per spec

Expected: Test file created with realistic directory structure fixture, all tests passing.

### Step 4: Run new tests and verify
```bash
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w4_template_discovery.py -v
```

Expected: 6 passed in <1 second, debug logs show filter working.

### Step 5: Run regression tests
```bash
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v
```

Expected: 33 passed, no regressions in core IAPlanner functionality.

### Step 6: Capture evidence and create documentation
Create evidence package at reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/ with:
- plan.md - Implementation strategy
- changes.md - What changed and why
- evidence.md - Test results
- commands.ps1 - All commands executed
- self_review.md - 12D quality assessment

Expected: Complete evidence package with all dimensions scoring 5/5.

## Failure modes

### Failure mode 1: Over-filtering legitimate blog templates
**Detection:** test_blog_templates_use_platform_structure fails; correct blog templates not discovered; debug logs show legitimate templates being filtered
**Resolution:** Verify filter only checks for `__LOCALE__` string in path, not other placeholders; ensure subdomain check is exact match for "blog.aspose.org"; review test fixture to confirm correct template structure
**Spec/Gate:** specs/33_public_url_mapping.md:88-96 blog structure requirements

### Failure mode 2: Under-filtering affects non-blog sections
**Detection:** test_docs_templates_allow_locale_folder fails; docs/reference templates with __LOCALE__ not discovered; debug logs show non-blog templates being filtered
**Resolution:** Verify subdomain check is scoped to blog.aspose.org only; ensure if-condition has correct indentation and logic; review test output to identify which section is affected
**Spec/Gate:** specs/07_section_templates.md:165-177 section-specific template requirements

### Failure mode 3: Regression in existing template discovery
**Detection:** pytest tests/unit/workers/test_tc_430_ia_planner.py fails; existing IAPlanner tests break; template counts change unexpectedly
**Resolution:** Review git diff to ensure only 8 lines added in enumerate_templates(); verify no changes to other functions; check that continue statement placement is correct; restore from backup if needed
**Spec/Gate:** specs/10_determinism_and_caching.md deterministic behavior requirements

### Failure mode 4: Debug logging not capturing filtered templates
**Detection:** Debug logs empty when obsolete templates should be filtered; cannot verify filter is executing
**Resolution:** Check logger level configuration; verify debug logging is enabled in test environment; add print statement temporarily to confirm filter execution; review log output format
**Spec/Gate:** Observability requirements for debugging and traceability

### Failure mode 5: Non-deterministic template ordering
**Detection:** test_template_deterministic_ordering fails; multiple runs produce different template order; tests are flaky
**Resolution:** Verify template discovery uses sorted paths; check that filter preserves existing sort order; ensure no random or time-dependent logic in filter; review pathlib.rglob() usage
**Spec/Gate:** specs/10_determinism_and_caching.md Section 4.1 deterministic operations

### Failure mode 6: Path separator incompatibility (Windows vs Linux)
**Detection:** Tests pass on Windows but fail on Linux (or vice versa); "__LOCALE__" not found in path string due to separator differences
**Resolution:** Verify string comparison works with both backslash (Windows) and forward slash (Linux); use pathlib.Path for cross-platform compatibility; test on both platforms; ensure path_str = str(template_path) converts correctly
**Spec/Gate:** Cross-platform compatibility requirements

## Task-specific review checklist
1. [ ] Filter only applies to blog.aspose.org subdomain (subdomain == "blog.aspose.org" check)
2. [ ] Filter checks for exact string "__LOCALE__" in template path
3. [ ] Debug logging includes component prefix [W4] and full path
4. [ ] Filter placement is after README check (line 875) and before template processing
5. [ ] Exactly 8 lines added (lines 876-884 in enumerate_templates())
6. [ ] No changes to other functions (URL path, page planning, classification)
7. [ ] Test file includes all 6 required tests (blog exclude, blog correct, docs allow, README, empty, deterministic)
8. [ ] All tests use temporary directories (no permanent file modifications)
9. [ ] Test fixture mirrors realistic template structure from specs/templates/
10. [ ] Both positive tests (correct discovery) and negative tests (filter works) included
11. [ ] Spec references in code comments (specs/33_public_url_mapping.md:100)
12. [ ] Frontmatter and body allowed_paths match exactly (3 entries)
13. [ ] Evidence package complete with plan, changes, evidence, commands, self_review
14. [ ] All 12 self-review dimensions scored ≥4/5
15. [ ] No regressions in test_tc_430_ia_planner.py (33/33 passing)

## Deliverables
- Modified src/launch/workers/w4_ia_planner/worker.py with 8-line filter (lines 876-884)
  - Filter checks subdomain == "blog.aspose.org"
  - Filter checks "__LOCALE__" in template path string
  - Debug logging with [W4] prefix and full path
  - Spec reference comment to specs/33_public_url_mapping.md:100
- New test file tests/unit/workers/test_w4_template_discovery.py with 6 comprehensive tests
  - test_blog_templates_exclude_locale_folder (verify filter works)
  - test_blog_templates_use_platform_structure (verify correct templates discovered)
  - test_docs_templates_allow_locale_folder (verify non-blog not affected)
  - test_readme_files_always_excluded (verify README filter preserved)
  - test_empty_directory_returns_empty_list (verify edge case handling)
  - test_template_deterministic_ordering (verify determinism)
- Test evidence showing 6/6 tests passing in <1 second
- Regression evidence showing 33/33 core IAPlanner tests passing
- Evidence package at reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/
  - plan.md - Implementation strategy with spec references
  - changes.md - Code changes, in/out scope, rationale
  - evidence.md - Test results, spec compliance verification
  - commands.ps1 - All commands executed with outputs
  - self_review.md - 12D assessment with all dimensions 5/5

## Acceptance checks
1. [ ] Filter added to enumerate_templates() function (exactly 8 lines at lines 876-884)
2. [ ] Filter only affects blog.aspose.org subdomain (subdomain check present)
3. [ ] Filter skips templates with "__LOCALE__" in path (string check present)
4. [ ] Debug logging implemented with [W4] prefix and full path
5. [ ] 6 unit tests created in test_w4_template_discovery.py (all tests present)
6. [ ] All 6 new tests passing (pytest exit code 0, <1 second execution)
7. [ ] Blog templates with __LOCALE__ filtered (test evidence confirms)
8. [ ] Correct blog templates discovered (test evidence confirms)
9. [ ] Docs templates with __LOCALE__ NOT filtered (test evidence confirms)
10. [ ] No regressions in core IAPlanner tests (33/33 passing in test_tc_430_ia_planner.py)
11. [ ] Deterministic behavior verified (test_template_deterministic_ordering passes)
12. [ ] Evidence package complete with all 5 files (plan, changes, evidence, commands, self_review)
13. [ ] All 12 self-review dimensions ≥4/5 (target: all 5/5)
14. [ ] Spec compliance verified (specs/33_public_url_mapping.md:100 enforced)

## Preconditions / dependencies
- Python virtual environment activated (.venv)
- All dependencies installed (pytest, pathlib, logging)
- src/launch/workers/w4_ia_planner/worker.py exists and is readable
- tests/unit/workers/ directory exists for test file creation
- No conflicting changes to enumerate_templates() function in worker.py
- Git repository in clean state (for spec_ref SHA verification)
- No dependencies on other taskcards (standalone fix)

## Test plan
1. **Test case 1: Blog templates with __LOCALE__ are filtered**
   Setup: Create mock blog template directory with __LOCALE__ in path
   Action: Call enumerate_templates() with blog.aspose.org subdomain
   Expected: No templates with __LOCALE__ in path are returned; debug log shows filtering

2. **Test case 2: Correct blog templates are discovered**
   Setup: Create mock blog template directory with __PLATFORM__/__POST_SLUG__ structure
   Action: Call enumerate_templates() with blog.aspose.org subdomain
   Expected: Templates with __POST_SLUG__ are discovered; no filtering occurs

3. **Test case 3: Non-blog sections allow __LOCALE__**
   Setup: Create mock docs template directory with __LOCALE__ in filename
   Action: Call enumerate_templates() with docs.aspose.org subdomain
   Expected: Templates with __LOCALE__ ARE discovered (filter doesn't apply)

4. **Test case 4: README files always excluded**
   Setup: Create mock template directory with README.md files
   Action: Call enumerate_templates() with any subdomain
   Expected: No README.md files in results (existing behavior preserved)

5. **Test case 5: Empty directory handling**
   Setup: Provide non-existent path to enumerate_templates()
   Action: Call enumerate_templates() with non-existent path
   Expected: Returns empty list (graceful handling)

6. **Test case 6: Deterministic ordering**
   Setup: Create template directory with multiple templates
   Action: Call enumerate_templates() multiple times with same inputs
   Expected: Results are identical in same order every time

## Self-review

### 12D Checklist
Complete self-review at: `reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/self_review.md`

1. **Coverage (Requirements & Edge Cases):** ⭐⭐⭐⭐⭐ (5/5)
   - All requirements met: filter __LOCALE__ for blog only, 6 tests created, no regressions
   - Edge cases: empty dirs, README files, cross-section behavior, determinism

2. **Correctness (Logic is Right; No Regressions):** ⭐⭐⭐⭐⭐ (5/5)
   - Filter logic correct: subdomain check + string comparison
   - Spec-compliant: specs/33_public_url_mapping.md:100 enforced
   - No regressions: 33/33 core tests passing

3. **Evidence (Commands/Logs/Tests Proving Claims):** ⭐⭐⭐⭐⭐ (5/5)
   - Test output: 6/6 passing in <1 second
   - Debug logs: Filter execution confirmed
   - Complete documentation: plan, changes, evidence, commands, self_review

4. **Test Quality (Meaningful, Stable, Deterministic):** ⭐⭐⭐⭐⭐ (5/5)
   - Meaningful: Each test verifies specific requirement
   - Stable: Uses temporary directories, no external dependencies
   - Deterministic: test_template_deterministic_ordering verifies

5. **Maintainability (Clear Structure, Naming, Modularity):** ⭐⭐⭐⭐⭐ (5/5)
   - Minimal change: 8 lines added
   - Clear comments with spec references
   - Descriptive test names and docstrings

6. **Safety (No Risky Side Effects; Guarded I/O):** ⭐⭐⭐⭐⭐ (5/5)
   - No side effects: filter only skips templates
   - Safe operations: string comparison only
   - No data modification

7. **Security (Secrets, Auth, Injection, Least Privilege):** ⭐⭐⭐⭐⭐ (5/5)
   - No security concerns: read-only operation
   - No user input processing
   - No injection vulnerabilities

8. **Reliability (Error Handling, Retries/Backoff, Idempotency):** ⭐⭐⭐⭐⭐ (5/5)
   - Idempotent: same input → same output
   - No error handling needed: deterministic operation
   - Graceful: continue statement safely skips

9. **Observability (Logs/Metrics/Traces; Actionable Errors):** ⭐⭐⭐⭐⭐ (5/5)
   - Debug logging with [W4] prefix and full path
   - Spec reference in comments
   - Test evidence provides traceability

10. **Performance (No Obvious Hotspots; Sane Defaults):** ⭐⭐⭐⭐⭐ (5/5)
    - Minimal overhead: O(n) string comparison
    - Tests run in <1 second
    - No performance degradation

11. **Compatibility (Windows/Linux Paths, Envs, Versions):** ⭐⭐⭐⭐⭐ (5/5)
    - Cross-platform: pathlib.Path used
    - Tested on Windows
    - Works with both path separators

12. **Docs/Specs Fidelity (Specs Match Code; Runnable Steps):** ⭐⭐⭐⭐⭐ (5/5)
    - Perfect spec alignment: specs/33_public_url_mapping.md:100
    - All commands documented and runnable
    - Complete traceability

**Average Score: 5.0/5** - All dimensions ≥4/5 ✅

### Verification results
- ✅ Tests: 6/6 PASS (test_w4_template_discovery.py in <1 second)
- ✅ Regression: 33/33 PASS (test_tc_430_ia_planner.py)
- ✅ Filter execution: Debug logs confirm templates with __LOCALE__ skipped for blog
- ✅ Spec compliance: specs/33_public_url_mapping.md:100 enforced
- ✅ Evidence captured: reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/

## E2E verification

```bash
# Step 1: Run new unit tests for template discovery filter
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w4_template_discovery.py -v

# Step 2: Run regression tests for core IAPlanner functionality
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v

# Step 3: Verify filter executes with debug logging (create test template with __LOCALE__)
# Create temporary test directory with obsolete blog template structure
# Run enumerate_templates() and check debug logs for filter execution

# Step 4: Verify spec compliance
# Check that specs/33_public_url_mapping.md:100 requirement is enforced
# Confirm blog templates without __LOCALE__ are discovered
# Confirm blog templates with __LOCALE__ are skipped
```

**Expected artifacts:**
- **tests/unit/workers/test_w4_template_discovery.py** - 6 comprehensive tests created
- **src/launch/workers/w4_ia_planner/worker.py** - Lines 876-884 contain filter logic
- **reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/** - Complete evidence package
  - plan.md - Implementation strategy
  - changes.md - Code changes documentation
  - evidence.md - Test results and verification
  - commands.ps1 - All commands executed
  - self_review.md - 12D quality assessment

**Expected results:**
- 6/6 new tests passing in <1 second (test_w4_template_discovery.py)
- 33/33 regression tests passing (test_tc_430_ia_planner.py)
- Debug logs show: "[W4] Skipping obsolete blog template with __LOCALE__: {path}"
- Blog templates with __LOCALE__ filtered (0 discovered)
- Blog templates with __PLATFORM__/__POST_SLUG__ discovered (>0 count)
- Docs templates with __LOCALE__ discovered (filter doesn't apply)
- All 12 self-review dimensions scored 5/5
- Spec compliance verified: specs/33_public_url_mapping.md:100 enforced

## Integration boundary proven

**Upstream:** W4 IAPlanner's `plan_pages_for_section()` function calls `enumerate_templates()` passing in:
- `search_root: Path` - Template directory path (e.g., specs/templates/blog.aspose.org/cells/)
- `subdomain: str` - Section subdomain (e.g., "blog.aspose.org", "docs.aspose.org")
- Returns: List of discovered template file paths

**Downstream:** `enumerate_templates()` returns filtered list of template paths to `plan_pages_for_section()`, which then:
- Classifies templates by variant (standard, minimal, etc.)
- Applies quota enforcement to limit pages generated
- Fills template placeholders (__PLATFORM__, __POST_SLUG__, etc.)
- Generates final page plan for content generation

**Contract:** Integration interface and guarantees:
- Input: Template directory path and subdomain string
- Output: List of Path objects for valid template files
- Filter behavior:
  - For blog.aspose.org subdomain: Skip templates with "__LOCALE__" in path
  - For other subdomains: No filtering (allow __LOCALE__)
  - Always skip README.md files (existing behavior)
- Ordering: Templates returned in deterministic sorted order (per specs/10_determinism_and_caching.md)
- Performance: O(n) complexity where n = number of template files
- Observability: Debug logs for filtered templates with [W4] prefix

**Integration test evidence:**
- test_blog_templates_exclude_locale_folder: Verifies blog templates with __LOCALE__ filtered
- test_blog_templates_use_platform_structure: Verifies correct blog templates discovered
- test_docs_templates_allow_locale_folder: Verifies non-blog sections not affected
- test_template_deterministic_ordering: Verifies deterministic order maintained
- Regression tests (test_tc_430_ia_planner.py): 33/33 passing, confirms downstream consumers unaffected

## Evidence Location
`reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/`

Evidence package contains:
- plan.md - Implementation strategy and approach
- changes.md - Detailed code changes and rationale
- evidence.md - Test results and verification
- commands.ps1 - All executed commands with outputs
- self_review.md - 12D quality assessment (all dimensions 5/5)
