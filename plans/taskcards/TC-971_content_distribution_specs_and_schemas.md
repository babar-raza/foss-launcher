---
id: TC-971
title: "Content Distribution Strategy - Specs and Schemas"
status: Ready
priority: Critical
owner: "Agent D (Docs & Specs)"
updated: "2026-02-04"
tags: ["specs", "schemas", "content-distribution", "phase-1"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-971_content_distribution_specs_and_schemas.md
  - specs/08_content_distribution_strategy.md
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - specs/schemas/page_plan.schema.json
  - specs/09_validation_gates.md
evidence_required:
  - reports/agents/AGENT_D/TC-971/evidence.md
  - reports/agents/AGENT_D/TC-971/self_review.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-971 — Content Distribution Strategy - Specs and Schemas

## Objective
Create and update specification files and schemas to define the content distribution strategy for the FOSS Launcher, enabling strategic distribution of repository information across products, docs, KB, and blog sections with explicit page roles and content boundaries.

## Problem Statement
The FOSS Launcher currently lacks a clear strategy for distributing repository information across different site sections (products, docs, KB, blog). This leads to:
1. Missing pages (no docs TOC index, no comprehensive developer guide)
2. Wrong content focus (KB is troubleshooting-only, not feature showcases)
3. No overlap prevention mechanism
4. Unclear page roles (each page type's strategic purpose is implicit, not explicit)

Users require specific content in specific places:
- products.aspose.org/3d/_index.md: Product landing with features
- docs.aspose.org/3d/_index.md: TOC listing ALL doc pages
- docs.aspose.org/3d/developer-guide/_index.md: Comprehensive listing of ALL scenarios
- kb.aspose.org/3d/how-to-*.md: 2-3 feature showcases + 1-2 troubleshooting
- blog.aspose.org/3d/announcing-*/index.md: Synthesized overview

## Required spec references
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Primary implementation plan)
- specs/06_page_planning.md (Current page planning spec - will be updated)
- specs/07_section_templates.md (Current section templates spec - will be updated)
- specs/09_validation_gates.md (Current validation gates spec - will be updated)
- specs/schemas/page_plan.schema.json (Current schema - will be extended)
- CONTRIBUTING.md (Repo governance rules - spec authority, binding specs)

## Scope

### In scope
- Create new spec: specs/08_content_distribution_strategy.md (~300 lines)
- Update specs/06_page_planning.md (+100 lines) with page roles and content strategies
- Update specs/07_section_templates.md (+80 lines) with new template types (TOC, comprehensive guide, feature showcase)
- Update specs/schemas/page_plan.schema.json (+50 lines) adding page_role enum and content_strategy object
- Update specs/09_validation_gates.md (+150 lines) adding Gate 14 specification
- All changes follow JSON Schema Draft 2020-12 format
- Schema validation passes

### Out of scope
- Implementation of W4/W5/W7 workers (covered by TC-972, TC-973, TC-974)
- Template file creation (covered by TC-975)
- Code changes or test implementations
- Modification of existing pilot configurations

## Inputs
- Existing specs/06_page_planning.md (current page planning logic)
- Existing specs/07_section_templates.md (current template definitions)
- Existing specs/schemas/page_plan.schema.json (current schema)
- Existing specs/09_validation_gates.md (Gates 1-13)
- Plan file: C:\Users\prora\.claude\plans\magical-prancing-fountain.md (2,020+ lines of detailed guidance)
- User requirements for content distribution

## Outputs
- specs/08_content_distribution_strategy.md (NEW file, ~300 lines)
- specs/06_page_planning.md (UPDATED, +100 lines)
- specs/07_section_templates.md (UPDATED, +80 lines)
- specs/schemas/page_plan.schema.json (UPDATED, +50 lines with new fields)
- specs/09_validation_gates.md (UPDATED, +150 lines for Gate 14)
- Schema validation passes (JSON Schema Draft 2020-12 compliant)
- Git diff showing all 5 file modifications
- Evidence bundle with validation output

## Allowed paths
- plans/taskcards/TC-971_content_distribution_specs_and_schemas.md
- specs/08_content_distribution_strategy.md
- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/schemas/page_plan.schema.json
- specs/09_validation_gates.md

### Allowed paths rationale
TC-971 creates the foundational specification and schema infrastructure for the content distribution strategy. All changes are in specs/ directory (specification authority), with no code modifications. This establishes the contracts that workers will implement in subsequent taskcards.

## Implementation steps

### Step 1: Create specs/08_content_distribution_strategy.md
Create new specification file defining canonical content distribution rules.

**Content structure:**
1. Binding Principles (4 principles: hierarchical delegation, no duplication, clear boundaries, strategic roles)
2. Section Responsibilities (6 sections: products, docs/_index, docs/getting-started, docs/developer-guide, kb, blog)
3. Content Allocation Rules (claim distribution, snippet distribution, cross-link strategy)
4. Validation Rules (Gate 14 requirements)

**Key sections to include:**
- Products: Product landing (5-10 features, links to docs/repo)
- Docs TOC: Navigation hub (lists ALL pages, no code)
- Docs getting-started: Installation + first task
- Docs developer-guide: ALL scenarios in one place
- KB: 2-3 feature showcases + 1-2 troubleshooting
- Blog: Synthesized overview (rephrases, doesn't copy)

```bash
# Create file
touch specs/08_content_distribution_strategy.md
# Edit with content from plan (lines 254-424 of magical-prancing-fountain.md)
```

Expected: File created with ~300 lines defining distribution strategy

### Step 2: Update specs/06_page_planning.md
Add new section after line 100 defining page roles and content strategies.

**Additions:**
- Page Roles section (7 roles: landing, toc, comprehensive_guide, workflow_page, feature_showcase, troubleshooting, api_reference)
- Content Strategy section (primary_focus, forbidden_topics, claim_quota, child_pages, scenario_coverage)
- Content Distribution Algorithm
- Updated mandatory pages by section (docs now requires 3: TOC + getting-started + developer-guide)

```bash
# Read current file
# Insert new section after line 100
# Add ~100 lines of content
```

Expected: spec updated with page role definitions, +100 lines

### Step 3: Update specs/07_section_templates.md
Add new template types after line 192.

**New Template Types:**
1. TOC Template (docs/_index.md): Navigation hub, Introduction + Documentation Index + Quick Links
2. Comprehensive Guide Template (docs/developer-guide/_index.md): ALL scenarios listing
3. Feature Showcase Template (kb/how-to-*.md): Single feature how-to

```bash
# Read current file
# Insert new sections after line 192
# Add ~80 lines
```

Expected: spec updated with 3 new template type definitions, +80 lines

### Step 4: Update specs/schemas/page_plan.schema.json
Add page_role and content_strategy fields to page specification.

**Schema additions:**
```json
{
  "page_role": {
    "type": "string",
    "enum": ["landing", "toc", "comprehensive_guide", "workflow_page", "feature_showcase", "troubleshooting", "api_reference"]
  },
  "content_strategy": {
    "type": "object",
    "properties": {
      "primary_focus": {"type": "string"},
      "forbidden_topics": {"type": "array", "items": {"type": "string"}},
      "claim_quota": {
        "type": "object",
        "properties": {
          "min": {"type": "number"},
          "max": {"type": "number"}
        }
      },
      "child_pages": {"type": "array", "items": {"type": "string"}},
      "scenario_coverage": {"type": "string", "enum": ["single", "all", "subset"]}
    }
  }
}
```

**Validation:**
```bash
python -c "import json, jsonschema; schema = json.load(open('specs/schemas/page_plan.schema.json')); jsonschema.Draft202012Validator.check_schema(schema); print('Schema is valid')"
```

Expected: Schema validates, fields are OPTIONAL (backward compatible), +50 lines

### Step 5: Update specs/09_validation_gates.md
Add Gate 14 specification after Gate 13.

**Gate 14 Definition:**
- Purpose: Validate content distribution strategy compliance
- 7 validation rules (schema compliance, TOC checks, comprehensive guide checks, forbidden topics, claim quotas, content duplication)
- 9 error codes (GATE14_ROLE_MISSING, GATE14_TOC_HAS_SNIPPETS, etc.)
- Profile-based severity (local=warning, ci/prod=error)
- Timeout: 60s (local), 120s (ci/prod)

```bash
# Read current file
# Insert Gate 14 after Gate 13 (around line 497)
# Add ~150 lines
```

Expected: Gate 14 specification added, +150 lines

### Step 6: Validate all changes
Run validation suite to ensure no regressions.

```bash
# Activate .venv
.venv\Scripts\activate

# Schema validation
python -c "import json, jsonschema; schema = json.load(open('specs/schemas/page_plan.schema.json')); jsonschema.Draft202012Validator.check_schema(schema); print('Schema is valid')"

# Lint check
make lint

# Spec pack validation (if available)
python scripts/validate_spec_pack.py
```

Expected: All validations pass, no lint errors

### Step 7: Create git diff summary
Generate evidence of changes for audit trail.

```bash
git diff specs/ > reports/agents/AGENT_D/TC-971/changes.diff
git status --short | grep "M.*specs/"
```

Expected: Diff shows 5 modified/new files in specs/ directory

## Failure modes

### Failure mode 1: Schema validation fails (invalid JSON Schema Draft 2020-12)
**Detection:** `python -c "import json, jsonschema; ..."` exits with error, shows schema validation failure
**Resolution:** Review JSON schema syntax; ensure all types, enums, and properties follow Draft 2020-12 format; check for missing commas, mismatched braces; use online JSON Schema validator for debugging
**Spec/Gate:** CONTRIBUTING.md (Schema Validation rule #6), JSON Schema Draft 2020-12 specification

### Failure mode 2: Markdown lint errors in spec files
**Detection:** `make lint` exits non-zero, shows markdown violations (line length, heading levels, list formatting)
**Resolution:** Fix markdown syntax per linter rules; ensure proper heading hierarchy; fix line wrapping; validate markdown format with markdownlint
**Spec/Gate:** CONTRIBUTING.md (Validation Requirements rule #10)

### Failure mode 3: Spec inconsistencies or contradictions
**Detection:** Manual review finds contradictions between specs (e.g., page_plan.schema.json allows field that 08_content_distribution_strategy.md forbids)
**Resolution:** Cross-check all spec changes for consistency; ensure schema matches spec definitions; align field names and enum values; update both schema and docs together
**Spec/Gate:** CONTRIBUTING.md (Spec Authority rule #1)

## Task-specific review checklist
1. [ ] specs/08_content_distribution_strategy.md created with all 6 section responsibilities defined
2. [ ] specs/06_page_planning.md updated with page roles (7 types) and content strategy structure
3. [ ] specs/07_section_templates.md updated with 3 new template types (TOC, comprehensive guide, feature showcase)
4. [ ] specs/schemas/page_plan.schema.json has page_role enum (7 values) and content_strategy object
5. [ ] specs/09_validation_gates.md has Gate 14 with 7 validation rules and 9 error codes
6. [ ] Schema validation passes: JSON Schema Draft 2020-12 compliant
7. [ ] Markdown lint passes: no formatting errors
8. [ ] All 5 files have git diff showing expected changes
9. [ ] Fields are OPTIONAL in schema (backward compatible)
10. [ ] Cross-references between specs are correct (no broken links)

## Deliverables
- specs/08_content_distribution_strategy.md (~300 lines)
- specs/06_page_planning.md (modified, +100 lines)
- specs/07_section_templates.md (modified, +80 lines)
- specs/schemas/page_plan.schema.json (modified, +50 lines)
- specs/09_validation_gates.md (modified, +150 lines)
- Git diff summary at reports/agents/AGENT_D/TC-971/changes.diff
- Schema validation output showing PASS
- Evidence bundle at reports/agents/AGENT_D/TC-971/evidence.md
- Self-review at reports/agents/AGENT_D/TC-971/self_review.md (12 dimensions, scores 1-5)

## Acceptance checks
1. [ ] All 5 spec/schema files created or updated
2. [ ] Schema validation passes (JSON Schema Draft 2020-12)
3. [ ] Markdown lint passes (make lint exits 0)
4. [ ] Git status shows exactly 5 files modified in specs/ directory
5. [ ] specs/08 defines all 6 section responsibilities
6. [ ] specs/06 defines all 7 page roles
7. [ ] specs/07 defines 3 new template types
8. [ ] page_plan.schema.json has page_role + content_strategy fields (OPTIONAL)
9. [ ] Gate 14 has 7 validation rules + 9 error codes
10. [ ] No breaking changes (fields are optional, backward compatible)

## Preconditions / dependencies
- Python virtual environment activated (.venv)
- Access to C:\Users\prora\.claude\plans\magical-prancing-fountain.md
- Git repository is clean (no conflicting changes)
- All existing specs are readable and in correct format

## Self-review
[To be completed by Agent D after implementation]

Dimensions to score (1-5, need 4+ on all):
1. Coverage: All 5 specs/schemas updated ✓
2. Correctness: Specs follow binding spec format ✓
3. Evidence: Git diff + schema validation ✓
4. Test Quality: N/A (specs only)
5. Maintainability: Clear structure, cross-references ✓
6. Safety: No breaking changes (optional fields) ✓
7. Security: N/A
8. Reliability: N/A
9. Observability: N/A
10. Performance: N/A
11. Compatibility: Backward compatible ✓
12. Docs/Specs Fidelity: Self-consistent ✓

## E2E verification
After TC-972, TC-973, TC-974, TC-975 complete:
1. Run pilot with updated system
2. Verify page_plan.json has page_role and content_strategy for all pages
3. Verify docs/_index.md is TOC (no code, lists children)
4. Verify docs/developer-guide/_index.md lists ALL workflows
5. Verify KB has 2-3 feature showcases
6. Verify Gate 14 passes

## Integration boundary proven
**Boundary:** specs/ (specification files) → src/ (implementation code)

**Contract:** This taskcard defines the specification contracts. TC-972 (W4), TC-973 (W5), TC-974 (W7), TC-975 (templates) implement these contracts. Integration is proven when:
1. Workers read page_plan.schema.json and populate new fields
2. Workers implement page roles per specs/08 rules
3. Gate 14 validates content distribution per specs/09
4. End-to-end test shows all 5 gaps resolved

**Verification:** After all 5 taskcards complete, run VFV (Verification & Validation) harness to confirm specs → implementation integration is correct.