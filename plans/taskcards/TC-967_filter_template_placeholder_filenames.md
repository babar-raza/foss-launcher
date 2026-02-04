---
id: TC-967
title: "Filter W4 Template Files with Placeholder Filenames"
status: Draft
priority: Critical
owner: "Agent B (Implementation)"
updated: "2026-02-04"
tags: ["blocker", "w4", "iaplanner", "template-enumeration", "url-collision"]
depends_on: ["TC-966"]
allowed_paths:
  - plans/taskcards/TC-967_filter_template_placeholder_filenames.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_template_enumeration_placeholders.py
  - plans/taskcards/INDEX.md
  - reports/agents/**/TC-967/**
evidence_required:
  - reports/agents/<agent>/TC-967/evidence.md
  - reports/agents/<agent>/TC-967/vfv_success.json
  - reports/agents/<agent>/TC-967/test_output.txt
spec_ref: "f37ece0524313c11a8a771924ad75fb521d8d08d"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-967: Filter W4 Template Files with Placeholder Filenames

## Objective

Modify W4 `enumerate_templates()` to filter out templates where the FILENAME (not just directory path) contains placeholder tokens like `__*__`, eliminating URL collisions caused by literal placeholder filenames.

## Problem Statement

**CRITICAL BUG**: TC-966 successfully fixed W4 template enumeration to search placeholder directories (`__LOCALE__/`, `__PLATFORM__/`), increasing template discovery from 8 to 53 templates. However, VFV now fails with URL collisions because templates with placeholder FILENAMES (like `__REFERENCE_SLUG__.md`, `__FORMAT_SLUG__.md`) are being enumerated literally.

**Working Pattern (Blog)**:
```
specs/templates/blog.aspose.org/3d/__PLATFORM__/__POST_SLUG__/index.variant-minimal.md
                                    ↑ placeholder dir    ↑ concrete filename ✓
```
- Placeholder directories: `__PLATFORM__/`, `__POST_SLUG__/`
- Concrete filenames: `index.md`, `_index.md`
- Result: No URL collisions, works correctly

**Broken Pattern (Docs/Products/Reference)**:
```
specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/__REFERENCE_SLUG__.md
                                                           ↑ placeholder filename ✗
```
- Placeholder directories: `__LOCALE__/`, `__PLATFORM__/`
- Placeholder filenames: `__REFERENCE_SLUG__.md`, `__FORMAT_SLUG__.md`, `__TOPIC_SLUG__.md`
- Result: URL collisions `/3d/python/__REFERENCE_SLUG__/` (multiple templates with same placeholder)

**VFV Error Evidence**:
```
IAPlannerURLCollisionError: URL collision: /3d/python/__REFERENCE_SLUG__/ maps to multiple pages:
  - content/docs.aspose.org/3d/en/python/docs/__REFERENCE_SLUG__.md
  - content/docs.aspose.org/3d/en/python/docs/__REFERENCE_SLUG__.md

URL collision: /3d/python/index/ maps to multiple pages:
  - content/docs.aspose.org/3d/en/python/docs/index.md
  - content/docs.aspose.org/3d/en/python/docs/index.md
  - content/blog.aspose.org/3d/python/index/index.md
```

## Required spec references

- specs/07_section_templates.md:1-50 (Template filename conventions - placeholders in directories vs filenames)
- specs/20_rulesets_and_templates_registry.md (Template discovery and resolution)
- specs/21_worker_contracts.md (W4 IAPlanner template enumeration contract)
- specs/10_determinism_and_caching.md (Template enumeration must be deterministic)
- specs/06_page_planning.md:75-83 (URL collision detection and prevention)

## Scope

### In scope

- Add filename placeholder filter to `enumerate_templates()` (after line 869)
- Filter out templates where filename (not full path) contains `__*__` pattern
- Maintain placeholder directory support (TC-966 behavior)
- Log filtered templates for debugging
- Update unit tests to verify placeholder filename filtering
- Re-run VFV to confirm URL collisions eliminated
- Verify all 5 sections still enumerate usable templates

### Out of scope

- Changes to template files themselves (templates are correct)
- Modifications to template classification logic (classify_templates() is fine)
- Changes to W5 SectionWriter (template rendering logic unchanged)
- Template variant selection logic (TC-959 deduplication unchanged)
- Changes to URL path computation (working correctly)

## Inputs

- TC-966 modified `enumerate_templates()` function (lines 830-933)
- Template directory structure with placeholder dirs: `__LOCALE__/`, `__PLATFORM__/`, `__POST_SLUG__/`
- Template files with mixed filename patterns:
  - Concrete: `index.md`, `_index.md`, `getting-started.md`
  - Placeholder: `__REFERENCE_SLUG__.md`, `__FORMAT_SLUG__.md`, `__TOPIC_SLUG__.md`
- VFV evidence showing URL collision errors

## Outputs

- Modified `enumerate_templates()` with placeholder filename filter (after line 869)
- Template discovery excludes placeholder filenames but includes concrete filenames
- VFV success: both pilots pass with exit_code=0, status=PASS
- Unit test updates verifying placeholder filename filtering
- page_plan.json with no URL collisions
- validation_report.json with no IA_PLANNER_URL_COLLISION errors

## Allowed paths

- plans/taskcards/TC-967_filter_template_placeholder_filenames.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_template_enumeration_placeholders.py
- plans/taskcards/INDEX.md
- reports/agents/**/TC-967/**

### Allowed paths rationale

TC-967 adds filename filtering logic to W4 template enumeration to prevent URL collisions. Test file ensures regression prevention. Evidence artifacts document VFV success.

## Implementation steps

### Step 1: Analyze current enumerate_templates() behavior

**Read current code** (TC-966 implementation):
```bash
# View the enumerate_templates function
sed -n '830,933p' "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\src\launch\workers\w4_ia_planner\worker.py"
```

**Expected**: Understand TC-966 fix searches placeholder directories, but doesn't filter placeholder filenames

**Key insight**: Line 867 uses `search_root.rglob("*.md")` which finds ALL .md files recursively, including those with placeholder filenames like `__REFERENCE_SLUG__.md`

### Step 2: Design placeholder filename filter

**Filter logic**:
```python
import re

# Define pattern to match placeholder tokens in filenames
placeholder_pattern = re.compile(r'__[A-Z_]+__')

# After discovering templates with rglob, filter by filename
filtered_templates = []
for template_path in templates:
    filename = template_path.name  # e.g., "__REFERENCE_SLUG__.md" or "index.md"

    # Check if FILENAME contains placeholder tokens
    if placeholder_pattern.search(filename):
        logger.debug(
            f"[W4] Skipping template with placeholder filename: {template_path.relative_to(template_dir)}"
        )
        continue

    filtered_templates.append(template_path)

templates = filtered_templates
```

**Rationale**:
- Placeholder directories are OK (needed for path structure)
- Placeholder filenames cause URL collisions (multiple templates resolve to same slug)
- Only check filename, not full path (allows `__PLATFORM__/index.md` but blocks `__REFERENCE_SLUG__.md`)

### Step 3: Implement placeholder filename filter in enumerate_templates()

**Modify enumerate_templates()** (lines 866-870):

**BEFORE** (TC-966 code):
```python
# Walk directory tree and find all .md files
for template_path in search_root.rglob("*.md"):
    if template_path.name == "README.md":
        continue

    # HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
```

**AFTER** (TC-967 fix):
```python
# Walk directory tree and find all .md files
templates_discovered = list(search_root.rglob("*.md"))

# Filter out README files and templates with placeholder filenames
import re
placeholder_pattern = re.compile(r'__[A-Z_]+__')

templates_to_process = []
for template_path in templates_discovered:
    # Skip README files
    if template_path.name == "README.md":
        continue

    # TC-967: Filter out templates with placeholder filenames
    # Placeholder directories are OK, but filenames must be concrete
    filename = template_path.name
    if placeholder_pattern.search(filename):
        logger.debug(
            f"[W4] Skipping template with placeholder filename: {template_path.relative_to(search_root)}"
        )
        continue

    templates_to_process.append(template_path)

# Process filtered templates
for template_path in templates_to_process:
    # HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
```

**Expected**: Template enumeration filters placeholder filenames, preventing URL collisions

### Step 4: Update or create unit tests

**Test file**: `tests/unit/workers/test_w4_template_enumeration_placeholders.py`

**Add test case**:
```python
def test_enumerate_templates_filters_placeholder_filenames():
    """Test that templates with placeholder filenames are filtered out (TC-967)."""
    from pathlib import Path
    from src.launch.workers.w4_ia_planner.worker import enumerate_templates

    template_dir = Path("specs/templates")

    # Enumerate docs templates
    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="docs.aspose.org",
        family="3d",
        locale="en",
        platform="python"
    )

    # Verify no templates have placeholder filenames
    for template in templates:
        filename = Path(template["template_path"]).name
        assert "__" not in filename or filename in ["_index.md", "__init__.py"], \
            f"Template has placeholder filename: {filename}"

    # Verify concrete filenames are included
    filenames = [Path(t["template_path"]).name for t in templates]
    assert "index.md" in filenames or "_index.md" in filenames, \
        "Should include concrete index files"
```

**Run tests**:
```bash
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w4_template_enumeration_placeholders.py -v
```

**Expected**: All tests pass, including new placeholder filename filter test

### Step 5: Manual verification with pilot run

**Quick test**: Enumerate templates and check for placeholder filenames
```bash
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"

.venv\Scripts\python.exe -c "
from pathlib import Path
from src.launch.workers.w4_ia_planner.worker import enumerate_templates

# Test docs section (previously had placeholder filenames)
templates = enumerate_templates(
    template_dir=Path('specs/templates'),
    subdomain='docs.aspose.org',
    family='3d',
    locale='en',
    platform='python'
)

print(f'Found {len(templates)} templates for docs.aspose.org/3d')
print('\\nFilenames discovered:')
for t in templates[:10]:
    filename = Path(t['template_path']).name
    print(f'  - {filename}')
    if '__' in filename and filename not in ['_index.md']:
        print(f'    WARNING: Placeholder filename detected!')
"
```

**Expected**: No templates with placeholder filenames like `__REFERENCE_SLUG__.md`

### Step 6: Run full pilot to verify page_plan.json

**Execute pilot**:
```bash
.venv\Scripts\python.exe scripts\launch_pilot.py --pilot pilot-aspose-3d-foss-python
```

**Inspect page_plan.json** for URL collisions:
```bash
# Check for duplicate URL paths
.venv\Scripts\python.exe -c "
import json
from pathlib import Path
from collections import Counter

# Find latest run
runs_dir = Path('runs')
run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
latest_run = run_dirs[-1] if run_dirs else None

if latest_run:
    page_plan_path = latest_run / 'artifacts' / 'page_plan.json'
    with open(page_plan_path) as f:
        page_plan = json.load(f)

    # Count URL paths
    url_paths = [p['url_path'] for p in page_plan['pages']]
    duplicates = {url: count for url, count in Counter(url_paths).items() if count > 1}

    if duplicates:
        print('URL COLLISIONS DETECTED:')
        for url, count in duplicates.items():
            print(f'  {url}: {count} pages')
    else:
        print('No URL collisions - SUCCESS!')

    print(f'\\nTotal pages: {len(page_plan[\"pages\"])}')
    print(f'Unique URLs: {len(set(url_paths))}')
"
```

**Expected**: No URL collisions, all URLs unique

### Step 7: Run VFV to verify end-to-end

**Execute VFV** on both pilots:
```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc967.json
```

**Verify VFV results**:
```bash
# Check VFV status
.venv\Scripts\python.exe -c "
import json
with open('reports/vfv_3d_tc967.json') as f:
    vfv = json.load(f)
print(f'Status: {vfv[\"status\"]}')
print(f'Exit code: {vfv[\"exit_code\"]}')
print(f'Run 1 hash: {vfv[\"run1_truth_hash\"]}')
print(f'Run 2 hash: {vfv[\"run2_truth_hash\"]}')
print(f'Match: {vfv[\"truth_match\"]}')
"
```

**Check validation_report.json** for URL collision errors:
```bash
# Find latest run and check for IA_PLANNER_URL_COLLISION errors
.venv\Scripts\python.exe -c "
import json
from pathlib import Path

runs_dir = Path('runs')
run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
latest_run = run_dirs[-1] if run_dirs else None

if latest_run:
    validation_path = latest_run / 'artifacts' / 'validation_report.json'
    if validation_path.exists():
        with open(validation_path) as f:
            validation = json.load(f)

        # Find URL collision issues
        url_collisions = [
            issue for issue in validation.get('issues', [])
            if issue.get('error_code') == 'IA_PLANNER_URL_COLLISION'
        ]

        if url_collisions:
            print(f'FOUND {len(url_collisions)} URL COLLISION ERRORS:')
            for issue in url_collisions:
                print(f'  {issue.get(\"message\")}')
        else:
            print('No URL collision errors - SUCCESS!')
"
```

**Expected**:
- VFV status=PASS, exit_code=0
- No IA_PLANNER_URL_COLLISION errors in validation_report.json
- Deterministic truth hashes match between runs

### Step 8: Generate evidence bundle

**Create evidence directory**:
```bash
mkdir -p reports\agents\AGENT_B\TC-967
```

**Capture evidence**:
```bash
# Copy VFV results
copy reports\vfv_3d_tc967.json reports\agents\AGENT_B\TC-967\

# Copy test output
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w4_template_enumeration_placeholders.py -v > reports\agents\AGENT_B\TC-967\test_output.txt

# Document findings
echo "TC-967 Evidence Summary" > reports\agents\AGENT_B\TC-967\evidence.md
echo "======================" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "## Implementation" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "- Modified enumerate_templates() to filter placeholder filenames" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "- Pattern: r'__[A-Z_]+__' matches placeholder tokens in filenames" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "## Results" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "- VFV status: PASS" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "- URL collisions: 0" >> reports\agents\AGENT_B\TC-967\evidence.md
echo "- Tests: PASS" >> reports\agents\AGENT_B\TC-967\evidence.md
```

## Task-specific review checklist

- [ ] Placeholder filename filter added to enumerate_templates() (after line 869)
- [ ] Filter checks filename only (not full path)
- [ ] Regex pattern `r'__[A-Z_]+__'` correctly matches placeholder tokens
- [ ] Debug logging for filtered templates
- [ ] README.md exclusion still works (existing filter)
- [ ] Placeholder directories still work (TC-966 behavior maintained)
- [ ] Unit tests updated with placeholder filename filtering test
- [ ] All unit tests pass
- [ ] Manual verification: no placeholder filenames in enumerated templates
- [ ] Pilot run: page_plan.json has no URL collisions
- [ ] VFV re-run: exit_code=0, status=PASS for both pilots
- [ ] validation_report.json: no IA_PLANNER_URL_COLLISION errors
- [ ] Blog section still works (no regression)
- [ ] Evidence bundle complete with VFV results and test output

## Deliverables

- Modified src/launch/workers/w4_ia_planner/worker.py (lines 866-878 with filename filter)
- Updated tests/unit/workers/test_w4_template_enumeration_placeholders.py
- VFV success reports: reports/vfv_3d_tc967.json
- Test output: reports/agents/AGENT_B/TC-967/test_output.txt
- Evidence bundle: reports/agents/AGENT_B/TC-967/evidence.md
- Updated INDEX.md with TC-967 entry

## Acceptance checks

- [ ] Template enumeration filters placeholder filenames
- [ ] Blog templates still discovered (8 templates with concrete filenames)
- [ ] Docs/products/reference/kb templates reduced to only concrete filenames
- [ ] Unit tests pass (all existing + new placeholder filename test)
- [ ] VFV re-run: pilot-aspose-3d exit_code=0, status=PASS
- [ ] page_plan.json: all URL paths unique (no collisions)
- [ ] validation_report.json: 0 IA_PLANNER_URL_COLLISION errors
- [ ] Template discovery still finds usable templates (>0 for each section)
- [ ] No regression: TC-966 placeholder directory discovery still works
- [ ] Evidence bundle complete

## Failure modes

### Failure mode 1: VFV still shows URL collisions after fix

**Detection:** validation_report.json contains IA_PLANNER_URL_COLLISION errors
**Resolution:**
1. Check if placeholder filename filter is correctly applied
2. Verify regex pattern matches all placeholder tokens in filenames
3. Inspect page_plan.json to identify which templates are causing collisions
4. Review template_path values to see if placeholder filenames are still included
5. Add additional debug logging to show filtered vs included templates
**Spec/Gate:** specs/06_page_planning.md:75-83 (URL collision detection)

### Failure mode 2: Template discovery returns 0 templates for some sections

**Detection:** Manual test or pilot run shows 0 templates for docs/products/reference sections
**Resolution:**
1. Verify placeholder directory support still works (TC-966 not regressed)
2. Check if filter is too aggressive (filtering valid filenames like "_index.md")
3. Review regex pattern - ensure it only matches placeholder tokens (double underscores)
4. Inspect template directories to confirm concrete-filename templates exist
5. Adjust filter logic to exclude valid filenames with underscores (like _index.md)
**Spec/Gate:** specs/07_section_templates.md template structure

### Failure mode 3: Blog section breaks (regression)

**Detection:** VFV shows blog/index.md empty or template_path=null
**Resolution:**
1. Verify blog templates use concrete filenames (index.md, _index.md)
2. Check that filter doesn't exclude blog templates incorrectly
3. Ensure TC-966 placeholder directory discovery still works for blog
4. Review TC-957 blog __LOCALE__ filter is still applied
5. Test blog template enumeration in isolation
**Spec/Gate:** TC-964 blog template rendering

### Failure mode 4: Unit tests fail after implementation

**Detection:** pytest shows test failures in test_w4_template_enumeration_placeholders.py
**Resolution:**
1. Review test expectations - ensure test checks filename, not full path
2. Verify test fixtures match real template directory structure
3. Check test assertions for valid underscored filenames (_index.md should pass)
4. Update test to match actual filter behavior
5. Add debug output to tests to show which templates are filtered
**Spec/Gate:** Test coverage requirements

### Failure mode 5: Validator rejects taskcard due to missing sections

**Detection:** validate_taskcards.py shows "Missing required section: X"
**Resolution:**
1. Add missing section per 00_TASKCARD_CONTRACT.md
2. Ensure frontmatter and body sections match
3. Verify all 14 mandatory sections present
4. Check acceptance criteria are measurable
5. Validate evidence requirements clearly defined
**Spec/Gate:** Gate B taskcard validation

## Preconditions / dependencies

- TC-966 complete (placeholder directory discovery working)
- Python virtual environment activated (.venv)
- Template directories exist with mixed filename patterns
- VFV harness working correctly
- Both pilots have valid run_config.pinned.yaml

## Test plan

### Test case 1: Placeholder filename filtering

**Input**: enumerate_templates() on docs.aspose.org/3d
**Expected**: No templates with filenames matching `__[A-Z_]+__` pattern
**Verification**: Check template list for placeholder filenames

### Test case 2: Concrete filename inclusion

**Input**: enumerate_templates() on blog.aspose.org/3d
**Expected**: Templates with concrete filenames (index.md, _index.md) included
**Verification**: Verify blog templates still discovered (8 templates)

### Test case 3: URL collision elimination

**Input**: Run pilot-aspose-3d-foss-python
**Expected**: page_plan.json has all unique URL paths
**Verification**: Count URL paths, check for duplicates

### Test case 4: VFV success

**Input**: Run VFV on pilot-aspose-3d-foss-python
**Expected**: exit_code=0, status=PASS, no IA_PLANNER_URL_COLLISION errors
**Verification**: Check VFV report and validation_report.json

### Test case 5: Deterministic ordering

**Input**: Call enumerate_templates() twice with same inputs
**Expected**: Identical template list order both times
**Verification**: Compare template lists from two calls

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

    # Check for placeholder filenames
    placeholder_filenames = [
        Path(t['template_path']).name
        for t in templates
        if '__' in Path(t['template_path']).name and Path(t['template_path']).name != '_index.md'
    ]

    print(f'{subdomain}: {len(templates)} templates, {len(placeholder_filenames)} with placeholder filenames')
    if placeholder_filenames:
        print(f'  WARNING: {placeholder_filenames[:3]}')
"

# 3. Run pilot
.venv\Scripts\python.exe scripts\launch_pilot.py --pilot pilot-aspose-3d-foss-python

# 4. Check for URL collisions in page_plan.json
.venv\Scripts\python.exe -c "
import json
from pathlib import Path
from collections import Counter

runs_dir = Path('runs')
run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
latest_run = run_dirs[-1] if run_dirs else None

if latest_run:
    page_plan_path = latest_run / 'artifacts' / 'page_plan.json'
    with open(page_plan_path) as f:
        page_plan = json.load(f)

    url_paths = [p['url_path'] for p in page_plan['pages']]
    duplicates = {url: count for url, count in Counter(url_paths).items() if count > 1}

    if duplicates:
        print('URL COLLISIONS:', duplicates)
    else:
        print('No URL collisions - SUCCESS!')
"

# 5. Run VFV
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc967.json

# 6. Verify VFV results
.venv\Scripts\python.exe -c "
import json
with open('reports/vfv_3d_tc967.json') as f:
    vfv = json.load(f)
print(f'Status: {vfv[\"status\"]}')
print(f'Exit code: {vfv[\"exit_code\"]}')
"

# 7. Check validation_report for URL collision errors
.venv\Scripts\python.exe -c "
import json
from pathlib import Path

runs_dir = Path('runs')
run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
latest_run = run_dirs[-1] if run_dirs else None

if latest_run:
    validation_path = latest_run / 'artifacts' / 'validation_report.json'
    if validation_path.exists():
        with open(validation_path) as f:
            validation = json.load(f)

        url_collisions = [
            issue for issue in validation.get('issues', [])
            if issue.get('error_code') == 'IA_PLANNER_URL_COLLISION'
        ]

        print(f'URL collision errors: {len(url_collisions)}')
"
```

**Expected artifacts**:
- **Unit tests**: All tests PASS
- **Manual test**: 0 templates with placeholder filenames for all sections
- **page_plan.json**: All URL paths unique (no duplicates)
- **VFV report**: status=PASS, exit_code=0
- **validation_report.json**: 0 IA_PLANNER_URL_COLLISION errors

**Expected final state**:
- Template enumeration filters placeholder filenames
- All sections have usable templates with concrete filenames
- No URL collisions in page planning
- VFV PASS with determinism verified

## Integration boundary proven

**Upstream:** TC-966 placeholder directory discovery; template directory structure with mixed filename patterns (concrete and placeholder); specs/07_section_templates.md defines template conventions

**Downstream:** W4 produces page_plan.json with template_path for each page; URL path computation uses template slug; W5 SectionWriter uses template_path to render content; VFV validates determinism and URL uniqueness

**Contract:** W4 `enumerate_templates()` must:
1. Discover templates in placeholder directories (TC-966)
2. Filter out templates with placeholder filenames (TC-967)
3. Return only templates with concrete filenames
4. Maintain deterministic ordering (sorted by template_path)
5. Prevent URL collisions caused by duplicate placeholder slugs

## Self-review

### 12D Checklist

1. **Determinism:** Template enumeration deterministic (sorted by template_path); placeholder filter applies consistently; no random ordering

2. **Dependencies:** No new dependencies; uses existing re module for regex; TC-966 behavior maintained

3. **Documentation:** TC-967 comments explain placeholder filename filter; debug logging for filtered templates

4. **Data preservation:** No data loss; placeholder directory discovery still works; only filters unusable placeholder filenames

5. **Deliberate design:** Filter checks filename only (not full path) to allow placeholder directories but block placeholder filenames; prevents URL collisions at source

6. **Detection:** URL collisions detected by VFV; validation_report.json shows IA_PLANNER_URL_COLLISION errors if filtering fails

7. **Diagnostics:** Debug logging shows filtered templates; template count logged per section; VFV provides collision details

8. **Defensive coding:** Regex pattern validated; filter preserves valid underscored filenames (_index.md); existing README filter maintained

9. **Direct testing:** Unit test verifies placeholder filename filtering; VFV validates end-to-end URL uniqueness; manual test checks template discovery

10. **Deployment safety:** Change only affects template discovery; can revert by removing filter block; no schema changes

11. **Delta tracking:** Modified enumerate_templates() function (lines 866-878); added placeholder filename filter after README filter

12. **Downstream impact:** Eliminates URL collisions; enables VFV to pass; unblocks pilot validation; no user-facing changes

### Verification results

- [ ] Tests: X/X PASS (e.g., 7/7 PASS)
- [ ] Validation: VFV PASS for both pilots
- [ ] Evidence captured: reports/agents/AGENT_B/TC-967/

## Evidence Location

`reports/agents/AGENT_B/TC-967/`
- evidence.md (summary)
- vfv_success.json (VFV results)
- test_output.txt (unit test results)
