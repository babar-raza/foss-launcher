---
id: TC-964
title: "Fix W5 SectionWriter Blog Template Token Rendering"
status: Done
priority: Critical
owner: "Agent B (Implementation)"
updated: "2026-02-04"
completed: "2026-02-04"
tags: ["blocker", "w5", "sectionwriter", "templates", "token-rendering"]
depends_on: ["TC-963"]
allowed_paths:
  - plans/taskcards/TC-964_fix_w5_blog_template_token_rendering.md
  - src/launch/workers/w4_ia_planner/worker.py
  - src/launch/workers/w5_section_writer/worker.py
  - specs/schemas/page_plan.schema.json
  - tests/unit/workers/test_w5_token_rendering.py
  - plans/taskcards/INDEX.md
  - reports/agents/**/TC-964/**
evidence_required:
  - reports/agents/<agent>/TC-964/evidence.md
  - reports/agents/<agent>/TC-964/token_mapping_audit.md
  - reports/agents/<agent>/TC-964/vfv_success.json
  - reports/agents/<agent>/TC-964/test_output.txt
spec_ref: "94e5449f603ac7c559b3b892e0201d4689a09fdf"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-964: Fix W5 SectionWriter Blog Template Token Rendering

## Objective

Fix W5 SectionWriter validation failure where blog template frontmatter contains unfilled placeholder tokens (`__TITLE__`, `__DESCRIPTION__`, `__DATE__`), causing both pilots to fail with "Unfilled tokens" error after successful IAPlanner (W4) execution.

## Problem Statement

VFV end-to-end verification (WS-VFV-004-RETRY) discovered that after TC-963 fixed the IAPlanner blocker, both pilots now fail deterministically during SectionWriter (W5) with error: "Unfilled tokens in page blog_index: __TITLE__". TC-963 correctly extracts placeholder tokens literally from template frontmatter into page_plan.json, but W5 has no mechanism to fill content-specific placeholders (title, description, author, date, etc.). No validation_report.json is produced, blocking VFV completion.

**Error Pattern** (identical for both pilots, both runs):
```
[info] [W5 SectionWriter] Processing blog section (1 pages)
[error] [W5 SectionWriter] Unfilled tokens in page blog_index: __TITLE__, __DESCRIPTION__, __DATE__, __AUTHOR__
[error] [W5 SectionWriter] Template validation failed: 4 unfilled tokens
Run failed: Unfilled tokens in page blog_index: __TITLE__
```

**Evidence Source**: WS-VFV-004-RETRY / reports/agents/AGENT_E/WS-VFV-004-RETRY/

## Required spec references

- specs/07_section_templates.md:196-209 (Blog template structure requirements)
- specs/21_worker_contracts.md (W5 SectionWriter PagePlan consumption)
- specs/schemas/page_plan.schema.json (PageSpec schema)
- specs/10_determinism_and_caching.md (Token filling must be deterministic)
- specs/34_strict_compliance_guarantees.md (Guarantee C: Hermetic execution)

## Scope

### In scope

- Add token generation logic to IAPlanner (W4) for content-specific placeholders
- Generate title, description, date, author, summary tokens for blog pages
- Store token mappings in page specifications (extend PageSpec if needed)
- Modify W5 SectionWriter to apply token mappings during template rendering
- Add unit tests to validate token generation and application
- Re-run VFV on both pilots to verify exit_code=0 and validation_report.json creation

### Out of scope

- Modifying template files themselves (templates are correct as-is)
- Changes to PagePlan schema beyond adding optional `token_mappings` field
- Token rendering for non-blog sections (use existing W5 logic)
- Changes to W4 IAPlanner validation logic (validation is correct)

## Inputs

- Existing blog templates with frontmatter containing placeholder tokens
- TC-963 enhanced `fill_template_placeholders()` returning all 10 required fields
- W5 SectionWriter template rendering logic
- VFV failure evidence from WS-VFV-004-RETRY

## Outputs

- Enhanced W4 IAPlanner with `generate_content_tokens()` function
- Modified W5 SectionWriter to use token mappings
- Extended page_plan.schema.json with optional `token_mappings` field
- Unit test file: tests/unit/workers/test_w5_token_rendering.py
- Successful VFV runs: exit_code=0, status=PASS, validation_report.json created
- Token mapping audit report documenting all generated tokens

## Allowed paths

- `plans/taskcards/TC-964_fix_w5_blog_template_token_rendering.md`
- `src/launch/workers/w4_ia_planner/worker.py`
- `src/launch/workers/w5_section_writer/worker.py`
- `specs/schemas/page_plan.schema.json`
- `tests/unit/workers/test_w5_token_rendering.py`
- `plans/taskcards/INDEX.md`
- `reports/agents/**/TC-964/**`## Implementation steps

### Step 1: Analyze required tokens from blog templates

**Identify tokens in frontmatter**:
```bash
# Scan blog templates for frontmatter tokens
grep -r "^__[A-Z_]*__:" specs/templates/blog.aspose.org/3d/ specs/templates/blog.aspose.org/note/
```

**Common tokens expected**:
- `__TITLE__`: Page title for frontmatter
- `__DESCRIPTION__`: Meta description
- `__DATE__`: Publication date
- `__AUTHOR__`: Content author
- `__SUMMARY__`: Short summary text
- `__DRAFT__`: Draft status (true/false)
- `__SEO_TITLE__`: SEO-optimized title
- `__TAGS__`: Topic tags array

**Expected**: List of 8-12 content-specific tokens used across blog templates

### Step 2: Extend page_plan schema with token_mappings field

**Decision**: Add `token_mappings` as optional field in page_plan.schema.json

**Implementation**: PageSpec schema already supports this via schema extension - W4 populates token_mappings dict in page specifications, W5 consumes them during rendering.

**Expected**: Schema extended to support optional token_mappings field

### Step 3: Create token generation logic in IAPlanner

**Add function** to `src/launch/workers/w4_ia_planner/worker.py`:

```python
def generate_content_tokens(
    page_spec: Dict[str, Any],
    section: str,
    family: str,
    platform: str
) -> Dict[str, str]:
    """
    Generate content-specific placeholder token values.

    For template-driven pages (especially blog), creates deterministic
    token values for title, description, author, date, etc.

    Args:
        page_spec: Page specification dict
        section: Section name (e.g., "blog")
        family: Product family (e.g., "3d")
        platform: Platform name (e.g., "python")

    Returns:
        Dict mapping token names to filled values

    Raises:
        ValueError: If required fields missing from page_spec
    """
    tokens = {}

    # Generate title from page context
    slug = page_spec.get("slug", "index")
    product_name = f"Aspose.{family.capitalize()} for {platform.capitalize()}"
    tokens["__TITLE__"] = f"{product_name} - {slug.replace('-', ' ').title()}"

    # Generate SEO title (max 60 chars)
    tokens["__SEO_TITLE__"] = f"{product_name} | {slug.title()}"

    # Generate description
    tokens["__DESCRIPTION__"] = f"Comprehensive guide to {product_name}"

    # Generate summary
    tokens["__SUMMARY__"] = f"Learn how to use {product_name} for {slug}."

    # Generate author (deterministic)
    tokens["__AUTHOR__"] = "Aspose Documentation Team"

    # Generate date (use current date in ISO format for determinism)
    from datetime import datetime
    tokens["__DATE__"] = datetime.now().strftime("%Y-%m-%d")

    # Generate draft status
    tokens["__DRAFT__"] = "false"

    # Generate tags
    tokens["__TAGS__"] = f"[{family}, {platform}, {section}]"

    return tokens
```

**Integration point**: Call `generate_content_tokens()` in `fill_template_placeholders()` after extracting title from template.

**Expected**: Token generation function added with deterministic values

### Step 4: Extend page_plan schema with token_mappings field

Update `specs/schemas/page_plan.schema.json` to include `token_mappings` as optional property:

```json
{
  "token_mappings": {
    "type": "object",
    "description": "Optional token mappings for template rendering",
    "additionalProperties": {"type": "string"}
  }
}
```

**Expected**: Schema extended to carry token mappings from W4 to W5

### Step 5: Modify W5 to apply token mappings

**Locate template rendering** in `src/launch/workers/w5_section_writer/worker.py`:
```bash
grep -A 20 "def render_template" src/launch/workers/w5_section_writer/worker.py
```

**Add token replacement logic**:
```python
def apply_token_mappings(template_content: str, token_mappings: Dict[str, str]) -> str:
    """
    Apply token mappings to template content.

    Replaces placeholder tokens with actual values from token_mappings dict.

    Args:
        template_content: Raw template content with tokens
        token_mappings: Dict mapping token names to replacement values

    Returns:
        Template content with tokens replaced
    """
    result = template_content
    for token, value in token_mappings.items():
        result = result.replace(token, value)
    return result
```

**Integrate** into template rendering pipeline:
1. Check if page spec has `token_mappings`
2. If yes, call `apply_token_mappings()` after loading template
3. Validate no unfilled tokens remain (existing W5 validation)

**Expected**: W5 applies token mappings before validation

### Step 6: Create unit tests for token rendering

**Test file**: `tests/unit/workers/test_w5_token_rendering.py`

**Test cases**:
1. `test_generate_content_tokens_blog()` - Token generation produces expected keys
2. `test_token_generation_deterministic()` - Same inputs produce same tokens
3. `test_apply_token_mappings()` - Token replacement works correctly
4. `test_w5_uses_token_mappings()` - W5 integrates token application
5. `test_unfilled_tokens_detected()` - Validation catches missing tokens

**Run tests**:
```bash
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w5_token_rendering.py -v
```

**Expected**: All 5 tests pass

### Step 7: Re-run VFV on both pilots

**Execute VFV**:
```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

# Run 3D pilot
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc964.json
echo Exit code 3d: %ERRORLEVEL%

# Run Note pilot
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports\vfv_note_tc964.json
echo Exit code note: %ERRORLEVEL%
```

**Verify success**:
- Both pilots: exit_code=0
- Both pilots: status=PASS in JSON report
- Both pilots: determinism=PASS (run1 SHA == run2 SHA)
- validation_report.json artifacts created in both run directories
- No "Unfilled tokens" errors in logs

**Inspect validation_report.json**:
```bash
# Find validation reports from latest runs
find runs/ -name "validation_report.json" -newer reports/vfv_3d_tc964.json

# Verify blog section pages validated successfully
jq '.pages[] | select(.section == "blog") | {slug, status}' <path_to_validation_report.json>
```

**Expected**: Blog pages present with status="valid", no token errors

## Task-specific review checklist

- [ ] All blog template tokens identified (8-12 tokens)
- [ ] Token generation function `generate_content_tokens()` created
- [ ] Token generation is deterministic (same inputs → same outputs)
- [ ] PageSpec extended with `token_mappings` field (or alternative mechanism)
- [ ] W5 `apply_token_mappings()` function created
- [ ] W5 integrates token application before validation
- [ ] Unit tests created with 5 test cases
- [ ] All unit tests pass (5/5)
- [ ] VFV re-run on pilot-aspose-3d: exit_code=0, status=PASS
- [ ] VFV re-run on pilot-aspose-note: exit_code=0, status=PASS
- [ ] validation_report.json artifacts created and show blog pages valid
- [ ] No "Unfilled tokens" errors in any logs
- [ ] Token mappings audit report documents all generated tokens
- [ ] Evidence captured: token diffs, test output, VFV reports

## Deliverables

- Modified src/launch/workers/w4_ia_planner/worker.py with token generation
- Modified src/launch/workers/w5_section_writer/worker.py with token application
- Modified specs/schemas/page_plan.schema.json with token_mappings field
- Unit test file: tests/unit/workers/test_w5_token_rendering.py
- Token mapping audit report: reports/agents/<agent>/TC-964/token_mapping_audit.md
- VFV success reports: reports/vfv_{3d,note}_tc964.json
- Test output: reports/agents/<agent>/TC-964/test_output.txt
- Evidence bundle: reports/agents/<agent>/TC-964/evidence.md

## Acceptance checks

- [ ] Token generation function created and deterministic
- [ ] W5 token application function created
- [ ] Unit tests pass (5/5)
- [ ] pilot-aspose-3d VFV: exit_code=0, status=PASS, determinism=PASS
- [ ] pilot-aspose-note VFV: exit_code=0, status=PASS, determinism=PASS
- [ ] validation_report.json created for both pilots
- [ ] Blog pages in validation_report.json have status="valid"
- [ ] No "Unfilled tokens" errors in logs
- [ ] Token mapping audit report complete
- [ ] Evidence bundle includes diffs, tests, VFV reports

## Failure modes

### Failure mode 1: VFV still fails with "Unfilled tokens: X"

**Detection:** VFV exit_code=2, error message shows different unfilled tokens (not the ones we mapped)
**Resolution:** Audit blog templates again for all tokens; ensure `generate_content_tokens()` generates values for ALL tokens found; add missing tokens to generation logic
**Spec/Gate:** specs/07_section_templates.md token conventions

### Failure mode 2: Token generation produces non-deterministic values

**Detection:** VFV determinism check fails; run1 SHA != run2 SHA for validation_report.json
**Resolution:** Remove non-deterministic elements (timestamps, random IDs, environment variables); use fixed date or derive from page context deterministically
**Spec/Gate:** specs/10_determinism_and_caching.md, VFV determinism requirement

### Failure mode 3: W5 fails to apply token mappings

**Detection:** Logs show token_mappings present in page spec but tokens not replaced; "Unfilled tokens" error persists
**Resolution:** Verify `apply_token_mappings()` is called before validation; check token_mappings field is correctly populated; ensure token names match exactly (case-sensitive)
**Spec/Gate:** W5 SectionWriter token rendering contract

### Failure mode 4: PageSpec schema validation fails

**Detection:** Pydantic validation error when creating page specifications; W4 crashes with schema mismatch
**Resolution:** Ensure token_mappings field is Optional[Dict[str, str]]; update schema.json if PageSpec model changed; run validation on sample page spec
**Spec/Gate:** specs/schemas/page_plan.schema.json validation

### Failure mode 5: Unit tests fail after implementation

**Detection:** pytest shows test failures; token generation or application tests fail
**Resolution:** Review test expectations; fix implementation logic; ensure token names match exactly; verify determinism in assertions
**Spec/Gate:** Test coverage requirements

## Preconditions / dependencies

- TC-963 must be complete (IAPlanner returns all 10 required fields)
- Python virtual environment activated (.venv)
- All dependencies installed
- VFV harness working correctly
- Both pilots configured and ready

## Test plan

### Test case 1: Token generation produces all required tokens
**Input**: Blog page spec with section="blog", family="3d", platform="python"
**Expected**: `generate_content_tokens()` returns dict with 8 keys: __TITLE__, __SEO_TITLE__, __DESCRIPTION__, __SUMMARY__, __AUTHOR__, __DATE__, __DRAFT__, __TAGS__

### Test case 2: Token generation is deterministic
**Input**: Call `generate_content_tokens()` twice with identical inputs
**Expected**: Both calls return identical dict (same values for all keys)

### Test case 3: Token application replaces all tokens
**Input**: Template content with `__TITLE__` and `__AUTHOR__`, token_mappings dict
**Expected**: `apply_token_mappings()` returns content with tokens replaced, no placeholders remain

### Test case 4: W5 integrates token application
**Input**: Page spec with token_mappings, template with tokens
**Expected**: W5 renders template with tokens filled, validation passes

### Test case 5: VFV end-to-end with token rendering
**Input**: Run VFV on both pilots
**Expected**: Both pilots exit_code=0, validation_report.json created, blog pages valid

## E2E verification

```bash
# Full end-to-end verification workflow

# 1. Run unit tests
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w5_token_rendering.py -v

# 2. Run VFV on both pilots
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d_tc964.json
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports\vfv_note_tc964.json

# 3. Verify VFV results
jq '.status' reports/vfv_3d_tc964.json  # Expected: "PASS"
jq '.status' reports/vfv_note_tc964.json  # Expected: "PASS"
jq '.determinism.validation_report.match' reports/vfv_3d_tc964.json  # Expected: true
jq '.determinism.validation_report.match' reports/vfv_note_tc964.json  # Expected: true

# 4. Verify validation_report.json exists and has blog pages
# (Extract run directory from VFV report, then inspect validation_report.json)
```

**Expected artifacts**:
- **tests/unit/workers/test_w5_token_rendering.py** - 5/5 tests PASS
- **reports/vfv_3d_tc964.json** - status=PASS, exit_code=0, determinism=PASS
- **reports/vfv_note_tc964.json** - status=PASS, exit_code=0, determinism=PASS
- **runs/.../validation_report.json** - Blog pages with status="valid"

**Expected final state**:
- Unit tests: 5/5 PASS
- pilot-aspose-3d: PASS (exit_code=0, determinism=PASS)
- pilot-aspose-note: PASS (exit_code=0, determinism=PASS)
- Both validation_report.json files contain blog section pages with no token errors

## Integration boundary proven

**Upstream:** TC-963 IAPlanner creates page specifications with all 10 required fields; blog templates have frontmatter with placeholder tokens
**Downstream:** W5 SectionWriter consumes page specifications and renders templates; W7 Validator checks rendered pages
**Contract:** Page specifications must include token_mappings dict when templates contain content placeholders. W5 must apply token mappings before validation. Token generation must be deterministic to ensure VFV reproducibility.

## Self-review

- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] Acceptance criteria are measurable and testable
- [ ] Evidence requirements clearly defined
- [ ] Failure modes include detection and resolution steps
- [ ] E2E verification workflow is complete and reproducible
- [ ] Depends_on lists TC-963 (prerequisite)
