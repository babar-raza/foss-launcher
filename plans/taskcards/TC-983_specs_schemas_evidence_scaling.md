---
id: TC-983
title: "Specs & Schemas: Evidence-Driven Page Scaling + Configurable Page Requirements"
status: Done
owner: Agent-D
updated: "2026-02-06"
depends_on: []
priority: P0
spec_ref: fad128dc63faba72bad582ddbc15c19a4c29d684
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - specs/rulesets/ruleset.v1.yaml
  - specs/schemas/ruleset.schema.json
  - specs/schemas/page_plan.schema.json
  - specs/schemas/validation_report.schema.json
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - specs/08_content_distribution_strategy.md
  - specs/09_validation_gates.md
  - specs/21_worker_contracts.md
  - reports/agents/agent_d/TC-983/**
evidence_required:
  - reports/agents/agent_d/TC-983/evidence.md
  - reports/agents/agent_d/TC-983/self_review.md
---

## Objective

Update all spec artifacts to support evidence-driven page scaling and configurable per-section/family mandatory page requirements. This taskcard MUST complete before implementation taskcards (TC-984, TC-985) begin.

## Required spec references

- specs/06_page_planning.md — Mandatory vs Optional Page Policy, Optional Page Selection Algorithm
- specs/08_content_distribution_strategy.md — Content distribution rules
- specs/09_validation_gates.md — Gate 14 Content Distribution Compliance
- specs/21_worker_contracts.md — W4 IAPlanner contract
- specs/schemas/ruleset.schema.json — sectionMinPages $def
- specs/schemas/page_plan.schema.json — page_plan structure
- specs/34_strict_compliance_guarantees.md — Binding compliance guarantees

## Scope

### In scope
1. Extend ruleset.v1.yaml with `mandatory_pages[]` and `optional_page_policies[]` per section
2. Add `family_overrides` top-level key to ruleset.v1.yaml for per-family customization
3. Update ruleset.schema.json: extend `sectionMinPages` $def, add `family_overrides`
4. Update page_plan.schema.json: add optional `evidence_volume` and `effective_quotas` properties
5. Update validation_report.schema.json: add `GATE14_MANDATORY_PAGE_MISSING` error code (1411)
6. Update 06_page_planning.md: configurable requirements, CI-absent tier softening, evidence scoring
7. Update 07_section_templates.md: per-feature workflow template expectations
8. Update 08_content_distribution_strategy.md: configurable page requirements section
9. Update 09_validation_gates.md: Gate 14 mandatory page presence rule
10. Update 21_worker_contracts.md: W4 contract new inputs/outputs (evidence_volume, effective_quotas, merged page requirements)

### Out of scope
- Python implementation (TC-984, TC-985)
- Test creation (TC-986)
- Template file creation

## Inputs
- Current specs/rulesets/ruleset.v1.yaml
- Current specs/schemas/*.schema.json
- Current specs/06, 07, 08, 09, 21 markdown specs
- Plan: plans/from_chat/20260205_160000_evidence_driven_page_scaling.md

## Outputs
- Updated specs/rulesets/ruleset.v1.yaml with mandatory_pages, optional_page_policies, family_overrides
- Updated specs/schemas/ruleset.schema.json
- Updated specs/schemas/page_plan.schema.json
- Updated specs/schemas/validation_report.schema.json
- Updated specs/06_page_planning.md
- Updated specs/07_section_templates.md
- Updated specs/08_content_distribution_strategy.md
- Updated specs/09_validation_gates.md
- Updated specs/21_worker_contracts.md

## Allowed paths
- specs/rulesets/ruleset.v1.yaml
- specs/schemas/ruleset.schema.json
- specs/schemas/page_plan.schema.json
- specs/schemas/validation_report.schema.json
- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/08_content_distribution_strategy.md
- specs/09_validation_gates.md
- specs/21_worker_contracts.md
- reports/agents/agent_d/TC-983/**

## Implementation steps

1. **ruleset.v1.yaml**: Add `mandatory_pages` array to each section (products, docs, reference, kb, blog) with slug + page_role. Add `optional_page_policies` array with page_role + source + priority. Add `family_overrides` top-level with 3d and note examples. Update min_pages (docs: 2→5, kb: 3→4).
2. **ruleset.schema.json**: Extend `sectionMinPages` $def with `mandatory_pages` (array of objects with required slug + page_role) and `optional_page_policies` (array of objects with required page_role + source + priority). Add `family_overrides` as optional top-level property.
3. **page_plan.schema.json**: Add `evidence_volume` (optional object, additionalProperties: true) and `effective_quotas` (optional object, additionalProperties: true).
4. **validation_report.schema.json**: Add `GATE14_MANDATORY_PAGE_MISSING` to recognized error codes.
5. **06_page_planning.md**: Replace hardcoded "Mandatory Pages by Section" with reference to ruleset config. Add "Configurable Page Requirements" section documenting mandatory_pages + family_overrides merge. Update "Launch Tier Adjustments" to soften CI-absent reduction. Enhance "Optional Page Selection Algorithm" with evidence_volume scoring.
6. **07_section_templates.md**: Add template expectations for per-feature workflow pages under developer-guide.
7. **08_content_distribution_strategy.md**: Add "Configurable Page Requirements" section. Document optional_page_policies sources (per_feature, per_workflow, per_key_feature, per_api_symbol).
8. **09_validation_gates.md**: Add rule 8 to Gate 14: "All mandatory_pages from merged config MUST exist in page_plan." Add GATE14_MANDATORY_PAGE_MISSING error code (1411, severity: ERROR).
9. **21_worker_contracts.md**: Update W4 contract: add merged page requirements as input, add evidence_volume + effective_quotas to outputs. Document family_overrides merge behavior.

## Failure modes

### Failure mode 1: Schema breaks existing validation

**Detection:** Existing tests fail on schema validation after schema changes.
**Resolution:** Ensure all new properties are optional with backward-compatible defaults.
**Spec/Gate:** Gate 1 (Schema Validation)

### Failure mode 2: Ruleset YAML invalid

**Detection:** YAML parse error or schema validation failure when loading ruleset.
**Resolution:** Validate ruleset against updated schema before committing.
**Spec/Gate:** Gate 1 (Schema Validation)

### Failure mode 3: Spec inconsistency

**Detection:** Cross-spec reference mismatch (e.g., Gate 14 references field not in schema).
**Resolution:** Verify all cross-references in implementation steps; audit all spec files for consistency.
**Spec/Gate:** Gate D (docs audit)

## Task-specific review checklist

1. [ ] ruleset.v1.yaml validates against updated ruleset.schema.json
2. [ ] All mandatory_pages entries have valid page_role enum values
3. [ ] family_overrides structure mirrors sections structure
4. [ ] page_plan.schema.json backward-compatible (new fields optional)
5. [ ] Gate 14 error code 1411 documented with severity and detection
6. [ ] 06_page_planning.md references ruleset config (not hardcoded lists)
7. [ ] 21_worker_contracts.md W4 contract lists evidence_volume + effective_quotas as outputs
8. [ ] No orphan references (every field referenced in specs exists in schemas)

## Deliverables

- All 9 files updated per implementation steps
- reports/agents/agent_d/TC-983/evidence.md
- reports/agents/agent_d/TC-983/self_review.md

## Acceptance checks

- [ ] ruleset.v1.yaml has mandatory_pages for all 5 sections
- [ ] ruleset.v1.yaml has family_overrides with at least 3d entry
- [ ] ruleset.schema.json validates the updated ruleset
- [ ] page_plan.schema.json allows evidence_volume + effective_quotas
- [ ] Gate 14 spec includes mandatory page presence rule
- [ ] W4 worker contract documents new inputs and outputs
- [ ] All cross-references between specs are consistent

## E2E verification

```bash
# Verify schema validation passes
.venv/Scripts/python.exe -c "import yaml, jsonschema; schema=__import__('json').load(open('specs/schemas/ruleset.schema.json')); ruleset=yaml.safe_load(open('specs/rulesets/ruleset.v1.yaml')); jsonschema.validate(ruleset, schema); print('Schema validation PASS')"

# Run pilots to verify spec changes don't break pipeline
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/e2e-983
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output output/e2e-983-note
```

**Expected artifacts:**
- **specs/rulesets/ruleset.v1.yaml** - Contains mandatory_pages, optional_page_policies, family_overrides
- **specs/schemas/ruleset.schema.json** - Extended with sectionMinPages mandatory_pages
- **specs/schemas/page_plan.schema.json** - Contains evidence_volume, effective_quotas
- **output/e2e-983/** - Pilot 3D pass with exit_code=0
- **output/e2e-983-note/** - Pilot Note pass with exit_code=0

## Integration boundary proven

**Upstream:** Existing specs and schemas define page planning behavior.
**Downstream:** TC-984 (W4 implementation), TC-985 (W7 Gate 14), TC-986 (tests) consume these spec changes.
**Contract:** All new schema fields are optional for backward compatibility. Specs document evidence_volume formula and mandatory_pages merge behavior.

## Self-review

12-dimension self-review required per reports/templates/self_review_12d.md.
All dimensions must score >=4/5 with concrete evidence.
