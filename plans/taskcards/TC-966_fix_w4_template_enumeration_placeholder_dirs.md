---
id: TC-966
title: "Fix W4 Template Enumeration - Search Placeholder Directories"
status: Done
priority: Critical
owner: "Agent B (Implementation)"
updated: "2026-02-04"
completed: "2026-02-04"
tags: ["blocker", "w4", "iaplanner", "template-enumeration", "critical-bug"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-966_fix_w4_template_enumeration_placeholder_dirs.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_template_enumeration_placeholders.py
  - plans/taskcards/INDEX.md
  - reports/agents/**/TC-966/**
evidence_required:
  - reports/agents/<agent>/TC-966/evidence.md
  - reports/agents/<agent>/TC-966/template_discovery_audit.md
  - reports/agents/<agent>/TC-966/vfv_success.json
  - reports/agents/<agent>/TC-966/test_output.txt
spec_ref: "94e5449f603ac7c559b3b892e0201d4689a09fdf"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-966: Fix W4 Template Enumeration - Search Placeholder Directories

## Objective

Fix W4 IAPlanner `enumerate_templates()` function to search for placeholder directories (`__LOCALE__`, `__PLATFORM__`, `__POST_SLUG__`) instead of literal values (`en`, `python`), enabling docs/products/reference/kb sections to use template-driven content generation.

## Problem Statement

**CRITICAL BUG**: 4 out of 5 pilot sections (docs, products, reference, kb) produce empty or minimal content because W4 template enumeration searches for literal directory paths that don't exist:

- **W4 searches**: `specs/templates/docs.aspose.org/3d/en/python/` ❌ (doesn't exist)
- **W4 fallback**: `specs/templates/docs.aspose.org/3d/en/` ❌ (doesn't exist)
- **What exists**: `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/` ✅ (has 6+ .md templates)

**Impact**: W4 returns empty template list → pages get `template_path: null` → W5 falls back to broken content generation → .md files are empty or repetitive.

**Why blog works**: Fallback at line 865 (`template_dir / subdomain / family`) accidentally finds placeholder dirs `__PLATFORM__/` and `__POST_SLUG__/` under `blog.aspose.org/3d/`.

**Evidence**:
- `runs/r_20260204T094825Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5/artifacts/page_plan.json` shows 4/5 sections with `template_path: null`
- Directory listing confirms ONLY placeholder dirs exist (no `en/`, `python/` dirs)

## Required spec references

- specs/07_section_templates.md:1-50 (Template directory structure - placeholder conventions)
- specs/20_rulesets_and_templates_registry.md (Template discovery and resolution)
- specs/21_worker_contracts.md (W4 IAPlanner template enumeration contract)
- specs/10_determinism_and_caching.md (Template enumeration must be deterministic)

## Scope

### In scope

- Fix `enumerate_templates()` function (lines 830-938) to search placeholder directories
- Add logic to discover `__LOCALE__`, `__PLATFORM__`, `__POST_SLUG__` dirs
- Enumerate templates within placeholder directories
- Maintain deterministic ordering (existing sort by template_path)
- Add unit tests for placeholder directory discovery
- Verify all 5 sections (docs, products, reference, kb, blog) enumerate templates correctly
- Re-run VFV to confirm all sections have non-null template_path

### Out of scope

- Changes to template files themselves (templates are correct)
- Modifications to template classification logic (classify_templates() is fine)
- Changes to W5 SectionWriter (TC-964 already fixed token rendering)
- Template variant selection logic (TC-959 deduplication already works)

## Inputs

- Existing `enumerate_templates()` function searching literal directories (lines 830-938)
- Template directory structure using placeholder dirs: `__LOCALE__/`, `__PLATFORM__/`, `__POST_SLUG__/`
- Pilot run_config.pinned.yaml with required_sections: ["products", "docs", "reference", "kb", "blog"]
- VFV evidence showing template_path=null for 4/5 sections

## Outputs

- Modified `enumerate_templates()` function discovering placeholder directories
- Template discovery for all 5 sections (not just blog)
- page_plan.json with non-null template_path for all sections
- Unit test file: tests/unit/workers/test_w4_template_enumeration_placeholders.py
- VFV success: all sections using template-driven generation
- Template discovery audit: reports/agents/<agent>/TC-966/template_discovery_audit.md

## Allowed paths

- `plans/taskcards/TC-966_fix_w4_template_enumeration_placeholder_dirs.md`
- `src/launch/workers/w4_ia_planner/worker.py`
- `tests/unit/workers/test_w4_template_enumeration_placeholders.py`
- `plans/taskcards/INDEX.md`
- `reports/agents/**/TC-966/**`## Implementation steps

### Step 1: Analyze current enumerate_templates() bug

**Read buggy code**:
```bash
cat src/launch/workers/w4_ia_planner/worker.py | sed -n '830,938p'
```

**Identify bug** (lines 859-867):
```python
# BUGGY: Searches for literal locale/platform dirs
if subdomain == "blog.aspose.org":
    search_root = template_dir / subdomain / family / platform  # Literal "python"
else:
    search_root = template_dir / subdomain / family / locale / platform  # Literal "en/python"

if not search_root.exists():
    if subdomain == "blog.aspose.org":
        search_root = template_dir / subdomain / family  # Works by accident!
    else:
        search_root = template_dir / subdomain / family / locale  # Fails!
```

**Expected**: Understand why blog works (line 865 finds placeholders) and others fail (line 867 searches for literal `en/` dir)

### Step 2: Design placeholder directory discovery

**New approach**: Instead of substituting literal values, discover placeholder dirs and enumerate within them.

**Pseudocode**:
```python
def enumerate_templates(template_dir, subdomain, family, locale, platform):
    templates = []

    # Search root: specs/templates/{subdomain}/{family}/
    base_search_root = template_dir / subdomain / family

    if not base_search_root.exists():
        return []

    # Discover all placeholder and literal directory combinations
    # Look for patterns:
    # - __LOCALE__/__PLATFORM__/
    # - __LOCALE__/__POST_SLUG__/
    # - __PLATFORM__/__POST_SLUG__/
    # - __POST_SLUG__/
    # - Direct .md files

    for template_path in base_search_root.rglob("*.md"):
        if template_path.name == "README.md":
            continue

        # Apply existing filters (blog __LOCALE__ exclusion, etc.)
        # Extract metadata (section, slug, placeholders)
        # Append to templates list

    templates.sort(key=lambda t: t["template_path"])
    return templates
```

**Expected**: Design that works for all sections uniformly

### Step 3: Implement placeholder-aware template discovery

**Modify enumerate_templates()** (lines 859-870):

**BEFORE** (buggy):
```python
if subdomain == "blog.aspose.org":
    search_root = template_dir / subdomain / family / platform
else:
    search_root = template_dir / subdomain / family / locale / platform

if not search_root.exists():
    if subdomain == "blog.aspose.org":
        search_root = template_dir / subdomain / family
    else:
        search_root = template_dir / subdomain / family / locale
```

**AFTER** (fixed):
```python
# FIXED: Search from family level, discover placeholders via rglob
search_root = template_dir / subdomain / family

if not search_root.exists():
    return []

# Walk from family level down, discovering all .md files in placeholder or literal dirs
# The rglob("*.md") on line 873 will find templates in any nested structure:
# - __LOCALE__/__PLATFORM__/*.md
# - __PLATFORM__/__POST_SLUG__/*.md
# - __POST_SLUG__/*.md
# - etc.
```

**Integration**: Remove lines 855-870, replace with simple search_root assignment. Existing rglob logic (line 873) will find all templates.

**Expected**: Template enumeration works for all sections

### Step 4: Test template discovery for all sections

**Create unit test**: `tests/unit/workers/test_w4_template_enumeration_placeholders.py`

**Test cases**:
1. `test_enumerate_templates_docs_section()` - Discovers templates in docs.aspose.org/3d/__LOCALE__/__PLATFORM__/
2. `test_enumerate_templates_products_section()` - Discovers templates in products.aspose.org/
3. `test_enumerate_templates_reference_section()` - Discovers templates in reference.aspose.org/
4. `test_enumerate_templates_kb_section()` - Discovers templates in kb.aspose.org/
5. `test_enumerate_templates_blog_section()` - Still discovers blog templates (no regression)
6. `test_template_discovery_deterministic()` - Same inputs produce same template list order

**Run tests**:
```bash
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w4_template_enumeration_placeholders.py -v
```

**Expected**: All 6 tests pass

### Step 5: Manual verification with pilot run

**Run W4 on pilot** (dry-run to check template enumeration):
```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

# Quick test: enumerate templates for docs section
.venv\Scripts\python.exe -c "
from pathlib import Path
from src.launch.workers.w4_ia_planner.worker import enumerate_templates

templates = enumerate_templates(
    template_dir=Path('specs/templates'),
    subdomain='docs.aspose.org',
    family='3d',
    locale='en',
    platform='python'
)
print(f'Found {len(templates)} templates for docs.aspose.org/3d')
for t in templates[:5]:
    print(f'  - {t[\"section\"]}/{t[\"slug\"]}: {t[\"template_path\"][:80]}...')
"
```

**Expected**: Non-zero template count (previously 0), template_path shows placeholder dirs

### Step 6: Re-run full pilot to verify page_plan.json

**Execute pilot**:
```bash
.venv\Scripts\python.exe scripts\launch_pilot.py --pilot pilot-aspose-3d-foss-python
```

**Inspect page_plan.json**:
```bash
cd runs/<latest_run_id>/artifacts

# Check template_path for all sections
jq '.pages[] | {section, slug, template_path: (.template_path // "NULL")}' page_plan.json
```

**Expected**: All sections have non-null template_path (not "NULL")

### Step 7: Re-run VFV to verify end-to-end

**Execute VFV**:
```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc966.json
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports\vfv_note_tc966.json
```

**Verify**:
- Both pilots: exit_code=0
- Both pilots: status=PASS
- All .md draft files have complete content (not empty/repetitive)
- validation_report.json: 0 unfilled token errors

**Expected**: VFV PASS, all sections working

## Task-specific review checklist

- [ ] enumerate_templates() modified to search from family level
- [ ] Placeholder directory discovery working (rglob finds all .md in nested dirs)
- [ ] Template count >0 for docs/products/reference/kb sections (not just blog)
- [ ] Unit tests created with 6 test cases
- [ ] All unit tests pass (6/6)
- [ ] Manual verification: template enumeration produces non-zero results
- [ ] Pilot run: page_plan.json has non-null template_path for all sections
- [ ] VFV re-run: exit_code=0, status=PASS for both pilots
- [ ] .md draft files have complete content (not empty/repetitive)
- [ ] No regression: blog section still works
- [ ] Template discovery audit complete
- [ ] Evidence captured: before/after page_plan.json comparison

## Deliverables

- Modified src/launch/workers/w4_ia_planner/worker.py (lines 855-870 simplified)
- Unit test file: tests/unit/workers/test_w4_template_enumeration_placeholders.py
- Template discovery audit: reports/agents/<agent>/TC-966/template_discovery_audit.md
- VFV success reports: reports/vfv_{3d,note}_tc966.json
- Test output: reports/agents/<agent>/TC-966/test_output.txt
- Evidence bundle: reports/agents/<agent>/TC-966/evidence.md

## Acceptance checks

- [ ] Template enumeration discovers templates for all 5 sections
- [ ] page_plan.json: all sections have non-null template_path
- [ ] Unit tests pass (6/6)
- [ ] VFV re-run: pilot-aspose-3d exit_code=0, status=PASS
- [ ] VFV re-run: pilot-aspose-note exit_code=0, status=PASS
- [ ] .md drafts: docs/getting-started.md has complete content (>50 lines, no repetition)
- [ ] .md drafts: reference/api-overview.md has complete content (not empty headers)
- [ ] Blog section still works (no regression)
- [ ] Template discovery deterministic (same order across runs)
- [ ] Evidence bundle complete

## Failure modes

### Failure mode 1: Template enumeration still returns 0 for non-blog sections

**Detection:** Manual test shows 0 templates found for docs.aspose.org
**Resolution:** Verify search_root path is correct; check rglob pattern; ensure placeholder dirs have .md files; review TC-957 blog filter doesn't exclude too broadly
**Spec/Gate:** specs/07_section_templates.md template structure

### Failure mode 2: Blog section breaks (regression)

**Detection:** VFV shows blog/index.md empty or template_path=null
**Resolution:** Ensure blog-specific logic (TC-957 filter) still works; verify rglob finds __PLATFORM__/__POST_SLUG__ templates; check deduplication (TC-959) doesn't skip all blog templates
**Spec/Gate:** TC-964 blog template rendering

### Failure mode 3: Template enumeration non-deterministic

**Detection:** Multiple runs produce different template order; VFV determinism check fails
**Resolution:** Verify templates.sort(key=lambda t: t["template_path"]) still executes; ensure no random/timestamp ordering; check rglob results are sorted
**Spec/Gate:** specs/10_determinism_and_caching.md

### Failure mode 4: page_plan.json has template_path but .md still empty

**Detection:** template_path non-null but drafts/docs/*.md files empty
**Resolution:** Check W5 SectionWriter applies templates correctly; verify TC-964 token_mappings logic works for non-blog sections; inspect W5 logs for errors
**Spec/Gate:** TC-964 W5 template rendering

### Failure mode 5: Unit tests fail after implementation

**Detection:** pytest shows test failures
**Resolution:** Review test expectations; verify test uses correct template_dir path; ensure test mocks/fixtures match real directory structure; check test assertions
**Spec/Gate:** Test coverage requirements

## Preconditions / dependencies

- Python virtual environment activated (.venv)
- Template directories exist with placeholder dirs (verified: __LOCALE__/, __PLATFORM__/, __POST_SLUG__/)
- TC-964 complete (W5 template rendering works for blog)
- VFV harness working correctly

## Test plan

### Test case 1: Template discovery for docs section
**Input**: enumerate_templates(template_dir, "docs.aspose.org", "3d", "en", "python")
**Expected**: Returns >0 templates from __LOCALE__/__PLATFORM__/ and __POST_SLUG__/ dirs

### Test case 2: Template discovery for all sections
**Input**: Call enumerate_templates() for each of 5 sections
**Expected**: All return >0 templates (not just blog)

### Test case 3: Deterministic ordering
**Input**: Call enumerate_templates() twice with same inputs
**Expected**: Identical template list order both times

### Test case 4: End-to-end pilot run
**Input**: Run pilot-aspose-3d-foss-python
**Expected**: page_plan.json has non-null template_path for all sections

### Test case 5: VFV verification
**Input**: Run VFV on both pilots
**Expected**: exit_code=0, all .md drafts have complete content

## E2E verification

```bash
# Full end-to-end verification workflow

# 1. Run unit tests
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w4_template_enumeration_placeholders.py -v

# 2. Manual template enumeration test
.venv\Scripts\python.exe -c "
from pathlib import Path
from src.launch.workers.w4_ia_planner.worker import enumerate_templates

for subdomain in ['docs.aspose.org', 'products.aspose.org', 'reference.aspose.org', 'kb.aspose.org', 'blog.aspose.org']:
    templates = enumerate_templates(
        template_dir=Path('specs/templates'),
        subdomain=subdomain,
        family='3d',
        locale='en',
        platform='python'
    )
    print(f'{subdomain}: {len(templates)} templates')
"

# 3. Run pilot
.venv\Scripts\python.exe scripts\launch_pilot.py --pilot pilot-aspose-3d-foss-python

# 4. Inspect page_plan.json
jq '.pages[] | {section, slug, has_template: (.template_path != null)}' <run_dir>/artifacts/page_plan.json

# 5. Run VFV
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc966.json

# 6. Verify VFV results
jq '.status' reports/vfv_3d_tc966.json  # Expected: "PASS"
```

**Expected artifacts**:
- **Unit tests**: 6/6 PASS
- **Manual test**: All 5 sections show >0 templates
- **page_plan.json**: All pages have template_path non-null
- **VFV report**: status=PASS, exit_code=0

**Expected final state**:
- Template enumeration works for all sections (not just blog)
- All .md draft files have complete content
- VFV PASS with determinism verified

## Integration boundary proven

**Upstream:** Template directories organized with placeholder conventions (__LOCALE__, __PLATFORM__, __POST_SLUG__); specs/07_section_templates.md defines structure

**Downstream:** W4 produces page_plan.json with template_path for each page; W5 SectionWriter uses template_path to render content; TC-964 token_mappings enable template filling

**Contract:** W4 `enumerate_templates()` must discover ALL templates regardless of directory structure (placeholder or literal). Template list must be deterministic (sorted by template_path). Each template descriptor must include section, slug, template_path, and placeholders list.

## Self-review

- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] Acceptance criteria are measurable and testable
- [ ] Evidence requirements clearly defined
- [ ] Failure modes include detection and resolution steps
- [ ] E2E verification workflow is complete and reproducible
- [ ] No dependencies listed (can execute independently)
