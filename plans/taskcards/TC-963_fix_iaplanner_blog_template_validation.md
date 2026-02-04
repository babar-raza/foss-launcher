---
id: TC-963
title: "Fix IAPlanner Blog Template Validation - Missing Title Field"
status: Done
priority: Critical
owner: "Agent B (Implementation)"
updated: "2026-02-04"
completed: "2026-02-04"
tags: ["blocker", "iaplanner", "templates", "validation", "w4"]
depends_on: ["TC-957", "TC-959", "TC-961", "TC-962"]
allowed_paths:
  - plans/taskcards/TC-963_fix_iaplanner_blog_template_validation.md
  - specs/templates/blog.aspose.org/3d/__PLATFORM__/__POST_SLUG__/*.md
  - specs/templates/blog.aspose.org/3d/__POST_SLUG__/*.md
  - specs/templates/blog.aspose.org/note/__PLATFORM__/__POST_SLUG__/*.md
  - specs/templates/blog.aspose.org/note/__POST_SLUG__/*.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_blog_template_validation.py
  - plans/taskcards/INDEX.md
  - reports/agents/**/TC-963/**
evidence_required:
  - reports/agents/<agent>/TC-963/evidence.md
  - reports/agents/<agent>/TC-963/template_audit.md
  - reports/agents/<agent>/TC-963/vfv_success.json
  - reports/agents/<agent>/TC-963/test_output.txt
spec_ref: "555ddca2c0e3628063d56bb058814c021f372662"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-963: Fix IAPlanner Blog Template Validation - Missing Title Field

## Objective

Fix IAPlanner validation failure where blog template variants are missing required "title" field in frontmatter, causing both pilots to fail with exit_code=2 during W4 execution.

## Problem Statement

VFV end-to-end verification (WS-VFV-004) discovered that both pilots fail deterministically during IAPlanner (W4) with error: "Page 4: missing required field: title". This occurs after TC-959 index deduplication removes 6 duplicate index pages, and the surviving template variant lacks required frontmatter fields. No page_plan.json artifact is produced, blocking VFV determinism verification and IAPlanner readiness certification.

**Error Pattern** (identical for both pilots, both runs):
```
[debug] [W4] Skipping duplicate index page for section '__PLATFORM__'
[debug] [W4] Skipping duplicate index page for section '__POST_SLUG__' (5x)
[info] [W4] De-duplicated 6 duplicate index pages
[info] [W4 IAPlanner] Planned 1 pages for section: blog (template-driven)
[error] [W4 IAPlanner] Planning failed: Page 4: missing required field: title
Run failed: Page 4: missing required field: title
```

**Evidence Source**: WS-VFV-004 / reports/agents/AGENT_E/WS-VFV-004/run_20260204_114709/

## Required spec references

- specs/07_section_templates.md:196-209 (Blog template structure requirements)
- specs/21_worker_contracts.md (W4 IAPlanner PagePlan schema)
- specs/schemas/page_plan.schema.json (Required frontmatter fields)
- specs/33_public_url_mapping.md:100 (Blog uses filename-based i18n)
- plans/taskcards/TC-959_*.md (Index page deduplication)

## Scope

### In scope

- Audit all blog template variants for required frontmatter fields
- Identify which template variant survives TC-959 deduplication (alphabetically first by template_path)
- Add missing "title" field to all blog template frontmatter
- Verify PagePlan schema compliance for all templates
- Add unit test to validate blog template frontmatter before W4 execution
- Re-run VFV on both pilots to verify exit_code=0 and page_plan.json creation

### Out of scope

- Modifying TC-959 deduplication logic (already correct)
- Changes to PagePlan schema (schema is correct, templates must comply)
- Modifications to non-blog template families
- Changes to W4 IAPlanner validation logic (validation is correct)

## Inputs

- Existing blog templates in specs/templates/blog.aspose.org/{3d,note}/
- PagePlan Pydantic model schema with required "title" field
- TC-959 deduplication logic (alphabetical selection by template_path)
- VFV failure evidence from WS-VFV-004

## Outputs

- Updated blog template variants with complete frontmatter (title field added)
- Unit test validating blog template frontmatter schema compliance
- Successful VFV runs: exit_code=0, status=PASS, page_plan.json created
- Template audit report documenting all changes

## Allowed paths

- plans/taskcards/TC-963_fix_iaplanner_blog_template_validation.md
- specs/templates/blog.aspose.org/3d/__PLATFORM__/__POST_SLUG__/*.md
- specs/templates/blog.aspose.org/3d/__POST_SLUG__/*.md
- specs/templates/blog.aspose.org/note/__PLATFORM__/__POST_SLUG__/*.md
- specs/templates/blog.aspose.org/note/__POST_SLUG__/*.md
- src/launch/workers/w4_ia_planner/worker.py (if schema changes needed)
- tests/unit/workers/test_w4_blog_template_validation.py
- plans/taskcards/INDEX.md
- reports/agents/**/TC-963/**

### Allowed paths rationale

TC-963 fixes missing frontmatter fields in blog template variants to ensure IAPlanner PagePlan validation passes. May require schema inspection in worker.py to understand requirements. Test file ensures regression prevention.

## Implementation steps

### Step 1: Audit blog template variants

**Identify template structure**:
```bash
cd specs/templates/blog.aspose.org
find . -type f -name "*.md" | grep -E "(3d|note)" | grep -v "__LOCALE__" | sort
```

**For each template, extract frontmatter**:
```bash
# Check for title field in frontmatter
for template in 3d/__PLATFORM__/__POST_SLUG__/*.md 3d/__POST_SLUG__/*.md \
                note/__PLATFORM__/__POST_SLUG__/*.md note/__POST_SLUG__/*.md; do
  echo "=== $template ==="
  head -20 "$template" | grep -E "^(title|layout|---)" || echo "No frontmatter"
done
```

**Expected**: Identify which templates have frontmatter and which lack "title" field

### Step 2: Determine surviving template after TC-959 deduplication

**Logic**: TC-959 selects alphabetically first template by template_path when multiple _index variants exist

**Simulate deduplication**:
```python
# Pseudo-code based on worker.py:976-981
templates = sorted(glob("**/_index*.md"), key=lambda t: t)
seen_sections = {}
for template in templates:
    section = extract_section(template)
    if section not in seen_sections:
        seen_sections[section] = template  # First alphabetically wins
        print(f"SELECTED: {template}")
    else:
        print(f"SKIPPED: {template}")
```

**Expected**: Identify exact template variant that survives for "blog" section (likely `_index.md` or `_index.variant-minimal.md`)

### Step 3: Inspect PagePlan schema requirements

**Read IAPlanner worker code**:
```bash
grep -A 20 "class PageSpec" src/launch/workers/w4_ia_planner/worker.py
# Or check Pydantic model definition
grep -A 30 "title.*Field" src/launch/workers/w4_ia_planner/worker.py
```

**Check schema file**:
```bash
cat specs/schemas/page_plan.schema.json | jq '.properties.pages.items.required'
```

**Expected**: List of required fields for PageSpec (likely: title, output_path, url_path, template_id, etc.)

### Step 4: Add missing "title" field to all blog templates

**Template frontmatter format**:
```yaml
---
title: "__TITLE__"
layout: blog-post
date: "__DATE__"
author: "__AUTHOR__"
tags: ["__TAGS__"]
---
```

**For each template variant, add frontmatter** (if missing) or **add title field** (if frontmatter exists):
- Use placeholder tokens: `__TITLE__`, `__POST_TITLE__`, or similar
- Follow existing template token conventions (`__UPPER_SNAKE__`)
- Ensure "title" field is present and uses token format

**Apply changes**:
```bash
# For templates lacking frontmatter entirely
# Add YAML frontmatter block at top with title field

# For templates with partial frontmatter
# Add title: "__TITLE__" line after opening ---
```

### Step 5: Create unit test for template validation

**Test file**: `tests/unit/workers/test_w4_blog_template_validation.py`

**Test cases**:
1. `test_blog_templates_have_frontmatter()` - All blog templates have YAML frontmatter
2. `test_blog_templates_have_title_field()` - All blog templates have "title" in frontmatter
3. `test_blog_templates_schema_compliant()` - Templates match PagePlan required fields
4. `test_template_deduplication_survivor_valid()` - Surviving template (alphabetically first) is valid

**Run test**:
```bash
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w4_blog_template_validation.py -v
```

**Expected**: All 4 tests pass

### Step 6: Re-run VFV on both pilots

**Execute VFV**:
```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

# Run 3D pilot
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc963.json
echo Exit code 3d: %ERRORLEVEL%

# Run Note pilot
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports\vfv_note_tc963.json
echo Exit code note: %ERRORLEVEL%
```

**Verify success**:
- Both pilots: exit_code=0
- Both pilots: status=PASS in JSON report
- Both pilots: determinism=PASS (run1 SHA == run2 SHA)
- page_plan.json artifacts created in both run directories

**Inspect page_plan.json**:
```bash
# Find page_plan.json from latest runs
find runs/ -name "page_plan.json" -newer reports/vfv_3d_tc963.json

# Verify blog section pages created successfully
jq '.pages[] | select(.section == "blog") | {title, output_path, url_path}' <path_to_page_plan.json>
```

**Expected**: Blog pages present with proper title, URL paths format `/{family}/{platform}/{slug}/`

## Task-specific review checklist

- [ ] All blog template variants audited (6+ templates per family)
- [ ] Surviving template after TC-959 deduplication identified
- [ ] PagePlan schema requirements documented (required fields list)
- [ ] "title" field added to all blog template frontmatter
- [ ] Title field uses placeholder token format (`__TITLE__` or similar)
- [ ] Unit test created with 4 test cases
- [ ] All unit tests pass
- [ ] VFV re-run on pilot-aspose-3d: exit_code=0, status=PASS
- [ ] VFV re-run on pilot-aspose-note: exit_code=0, status=PASS
- [ ] page_plan.json artifacts created and contain blog pages
- [ ] Blog page URL paths verified: `/{family}/{platform}/{slug}/` (no section name)
- [ ] Template audit report documents all changes
- [ ] Evidence captured: template diffs, test output, VFV reports

## Failure modes

### Failure mode 1: VFV still fails with "missing required field: X"

**Detection:** VFV exit_code=2, error message shows different missing field (not "title")
**Resolution:** Repeat Step 3 to get complete list of required fields; add all missing fields to template frontmatter; verify against PageSpec model definition
**Spec/Gate:** specs/schemas/page_plan.schema.json, PageSpec Pydantic model

### Failure mode 2: Template deduplication selects wrong variant

**Detection:** VFV passes but page content is incorrect; logs show unexpected template variant selected
**Resolution:** Verify TC-959 deduplication logic at worker.py:976-981; ensure alphabetical sorting is correct; check that correct variant has complete frontmatter
**Spec/Gate:** TC-959 implementation, specs/07_section_templates.md

### Failure mode 3: Added title field breaks template rendering

**Detection:** VFV passes W4 but fails at W5 (SectionWriter) with template rendering error; Hugo build fails
**Resolution:** Verify title field uses correct placeholder token format; check that token is replaced during W5 execution; ensure token matches snippet/claim data available
**Spec/Gate:** specs/07_section_templates.md token conventions

### Failure mode 4: Unit tests fail after template changes

**Detection:** pytest shows test failures; frontmatter parsing errors
**Resolution:** Verify YAML frontmatter syntax (proper --- delimiters); ensure title field is valid YAML; check for indentation or special character issues
**Spec/Gate:** YAML specification, Python yaml.safe_load() requirements

### Failure mode 5: Only one pilot passes VFV

**Detection:** One pilot exit_code=0, other pilot exit_code=2; error indicates missing field in different template
**Resolution:** Ensure changes applied to BOTH 3d and note template families; verify all variants updated, not just one; check for copy-paste errors between families
**Spec/Gate:** Cross-family consistency requirement

## Deliverables

- Modified blog templates in specs/templates/blog.aspose.org/{3d,note}/ with complete frontmatter
- Unit test file: tests/unit/workers/test_w4_blog_template_validation.py
- Template audit report: reports/agents/<agent>/TC-963/template_audit.md
- VFV success reports: reports/vfv_{3d,note}_tc963.json
- Test output: reports/agents/<agent>/TC-963/test_output.txt
- Evidence bundle: reports/agents/<agent>/TC-963/evidence.md

## Acceptance checks

- [ ] All blog templates have YAML frontmatter
- [ ] All blog templates have "title" field in frontmatter
- [ ] Unit tests pass (4/4)
- [ ] pilot-aspose-3d VFV: exit_code=0, status=PASS, determinism=PASS
- [ ] pilot-aspose-note VFV: exit_code=0, status=PASS, determinism=PASS
- [ ] page_plan.json created for both pilots
- [ ] Blog pages in page_plan.json have correct URL paths (no section name)
- [ ] Template audit report complete
- [ ] Evidence bundle includes diffs, tests, VFV reports

## E2E verification

```bash
# Full end-to-end verification workflow

# 1. Run unit tests
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w4_blog_template_validation.py -v

# 2. Run VFV on both pilots
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc963.json
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports\vfv_note_tc963.json

# 3. Verify VFV results
jq '.status' reports/vfv_3d_tc963.json  # Expected: "PASS"
jq '.status' reports/vfv_note_tc963.json  # Expected: "PASS"
jq '.determinism.page_plan.match' reports/vfv_3d_tc963.json  # Expected: true
jq '.determinism.page_plan.match' reports/vfv_note_tc963.json  # Expected: true

# 4. Verify page_plan.json exists and has blog pages
# (Extract run directory from VFV report, then inspect page_plan.json)
```

**Expected artifacts**:
- **tests/unit/workers/test_w4_blog_template_validation.py** - 4/4 tests PASS
- **reports/vfv_3d_tc963.json** - status=PASS, exit_code=0, determinism=PASS
- **reports/vfv_note_tc963.json** - status=PASS, exit_code=0, determinism=PASS
- **runs/.../page_plan.json** - Blog pages with proper URL paths

**Expected final state**:
- Unit tests: 4/4 PASS
- pilot-aspose-3d: PASS (exit_code=0, determinism=PASS)
- pilot-aspose-note: PASS (exit_code=0, determinism=PASS)
- Both page_plan.json files contain blog section pages with proper URL paths

## Integration boundary proven

**Upstream:** TC-959 index deduplication selects template variant; TC-957 filters obsolete `__LOCALE__` templates; TC-961/TC-962 cleanup complete
**Downstream:** W4 IAPlanner creates page_plan.json; W5 SectionWriter uses templates; VFV verifies determinism
**Contract:** Templates must have complete frontmatter matching PagePlan schema; required fields include "title", "layout", and placeholder tokens for dynamic content

## Self-review

- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] Acceptance criteria are measurable and testable
- [ ] Evidence requirements clearly defined
- [ ] Failure modes include detection and resolution steps
- [ ] E2E verification workflow is complete and reproducible
- [ ] Depends_on lists all prerequisite taskcards (TC-957, TC-959, TC-961, TC-962)
