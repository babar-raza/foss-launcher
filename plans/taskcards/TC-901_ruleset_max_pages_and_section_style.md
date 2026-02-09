---
id: "TC-901"
title: "Ruleset Schema: Add max_pages and Per-Section Style Configuration"
status: In-Progress
owner: "agent-2"
updated: "2026-02-01"
depends_on:
  - TC-200
allowed_paths:
  - plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - specs/schemas/ruleset.schema.json
  - specs/rulesets/ruleset.v1.yaml
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - specs/20_rulesets_and_templates_registry.md
  - reports/agents/**/TC-901/**
evidence_required:
  - reports/agents/agent-2/TC-901/report.md
  - reports/agents/agent-2/TC-901/self_review.md
spec_ref: d1d440f4b809781c9bf78516deac8168c54f22a6
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-901 — Ruleset Schema: Add max_pages and Per-Section Style Configuration

## Objective
Extend the ruleset schema to support max_pages quotas per section and optional per-section style configuration (style_by_section, limits_by_section), enabling fine-grained control over content generation constraints.

## Required spec references
- specs/schemas/ruleset.schema.json (schema definition)
- specs/rulesets/ruleset.v1.yaml (default ruleset configuration)
- specs/06_page_planning.md (page quota planning)
- specs/07_section_templates.md (section-specific styling)
- specs/20_rulesets_and_templates_registry.md (schema versioning)

## Scope
### In scope
- Add max_pages property to sectionMinPages schema definition
- Add optional style_by_section object (tone, voice)
- Add optional limits_by_section object (max_words, max_headings, max_code_blocks)
- Update ruleset.v1.yaml with sensible defaults for all sections
- Update documentation in specs/06, 07, 20
- Validation to ensure schema compliance

### Out of scope
- Implementation of enforcement logic (separate taskcard)
- Migration of existing content
- Auto-detection of optimal quotas

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue and stop that path.
- **Write fence:** you MAY ONLY change files under **Allowed paths** below.
- **Determinism:** stable file ordering (use sorted()), no timestamps in validation output.
- **Evidence:** all validation outputs recorded in report.

## Preconditions / dependencies
- TC-200 (Schemas and IO foundations) must be complete
- Python 3.12+ environment with .venv
- pytest installed for validation

## Inputs
- Current ruleset.schema.json (lines 89-96)
- Current ruleset.v1.yaml (lines 40-50)
- Spec documentation files

## Outputs
- Updated ruleset.schema.json with extended sectionMinPages definition
- Updated ruleset.v1.yaml with defaults for all sections
- Updated documentation files
- Validation passing (validate_swarm_ready.py, pytest)

## Allowed paths

- `plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `specs/schemas/ruleset.schema.json`
- `specs/rulesets/ruleset.v1.yaml`
- `specs/06_page_planning.md`
- `specs/07_section_templates.md`
- `specs/20_rulesets_and_templates_registry.md`
- `reports/agents/**/TC-901/**`## Implementation steps
1) Update specs/schemas/ruleset.schema.json:
   - Modify sectionMinPages definition (line 89-96)
   - Change required from ["min_pages"] to ["min_pages"]
   - Add max_pages property (type: integer, minimum: 0)
   - Add optional style_by_section object (tone, voice strings)
   - Add optional limits_by_section object (max_words, max_headings, max_code_blocks integers)

2) Update specs/rulesets/ruleset.v1.yaml:
   - Add max_pages to all sections (products, docs, reference, kb, blog)
   - Add style_by_section with tone and voice defaults
   - Use sensible defaults based on section purpose

3) Update specs/06_page_planning.md:
   - Document max_pages quota system
   - Explain how quotas prevent unbounded growth
   - Provide examples of quota configuration

4) Update specs/07_section_templates.md:
   - Document style_by_section usage
   - Explain how section-specific styles override global styles
   - Document limits_by_section constraints

5) Update specs/20_rulesets_and_templates_registry.md:
   - Update schema reference documentation
   - Note new optional properties

6) Run validation:
   - validate_swarm_ready.py
   - pytest suite

7) Create evidence bundle

## Test plan
- Schema validation:
  - Verify ruleset.v1.yaml validates against updated schema
  - Test that max_pages is optional (backwards compatible)
  - Test that style_by_section and limits_by_section are optional

- Integration tests:
  - Run validate_swarm_ready.py (must pass)
  - Run full pytest suite (must pass)

- Documentation:
  - Verify all spec files updated consistently
  - Check cross-references are correct

## E2E verification
**Concrete command(s) to run:**
```bash
# Activate .venv
.venv/Scripts/activate

# Validate schema compliance
python tools/validate_swarm_ready.py

# Run full test suite
python -m pytest -q

# Validate ruleset.v1.yaml against schema
python -c "import json, yaml, jsonschema; schema=json.load(open('specs/schemas/ruleset.schema.json')); data=yaml.safe_load(open('specs/rulesets/ruleset.v1.yaml')); jsonschema.validate(data, schema); print('✓ ruleset.v1.yaml validates')"
```

**Expected artifacts:**
- specs/schemas/ruleset.schema.json (extended sectionMinPages)
- specs/rulesets/ruleset.v1.yaml (all sections with max_pages and style_by_section)
- Updated documentation in specs/06, 07, 20
- Evidence bundle in reports/agents/agent-2/TC-901/

**Success criteria:**
- [ ] ruleset.schema.json updated with max_pages, style_by_section, limits_by_section
- [ ] ruleset.v1.yaml has sensible defaults for all sections
- [ ] All documentation updated
- [ ] validate_swarm_ready.py passes
- [ ] pytest suite passes
- [ ] Schema validation confirms ruleset.v1.yaml compliance
- [ ] Evidence bundle created with all outputs

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-200 (Schemas and IO foundations)
- Downstream: W4 IA Planner (TC-430) will consume these quotas
- Downstream: W5 SectionWriter (TC-440) will enforce limits
- Contracts: JSON schema compliance, YAML structure

## Failure modes

### Failure mode 1: Schema validation fails for ruleset.v1.yaml
**Detection:** jsonschema.validate() raises ValidationError when validating ruleset against schema; specific field or type errors reported
**Resolution:** Review properties against schema definition in ruleset.schema.json; ensure all required fields present and correctly typed; verify max_pages is integer >= 0; check style_by_section and limits_by_section structure matches schema; test with minimal valid example
**Spec/Gate:** specs/schemas/ruleset.schema.json, validate_swarm_ready.py (schema validation)

### Failure mode 2: Backwards compatibility broken by required fields
**Detection:** Existing code expecting only min_pages fails with KeyError or missing field errors; workers crash when loading ruleset
**Resolution:** Ensure max_pages, style_by_section, limits_by_section are optional in schema (not in required array); provide sensible defaults when fields missing; update worker code to handle both old and new schema versions gracefully
**Spec/Gate:** specs/20_rulesets_and_templates_registry.md (versioning and compatibility)

### Failure mode 3: Write fence violation - unauthorized file modifications
**Detection:** git status shows changes outside allowed_paths; files modified that aren't in this taskcard's scope
**Resolution:** Revert all unauthorized changes; verify only ruleset schema, ruleset.v1.yaml, and documentation files modified; check for accidental edits to worker code or other configs; ensure clean git diff before committing
**Spec/Gate:** plans/taskcards/00_TASKCARD_CONTRACT.md (write fence rule)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Schema changes are backwards compatible (optional properties)
- [ ] All sections in ruleset.v1.yaml have consistent structure
- [ ] Documentation cross-references updated
- [ ] No placeholder values (PIN_ME, TODO, FIXME)
- [ ] Evidence files include validation outputs
- [ ] Determinism verified (schema validation repeatable)

## Deliverables
- Code:
  - specs/schemas/ruleset.schema.json (extended)
  - specs/rulesets/ruleset.v1.yaml (with defaults)
- Documentation:
  - specs/06_page_planning.md (updated)
  - specs/07_section_templates.md (updated)
  - specs/20_rulesets_and_templates_registry.md (updated)
- Reports (required):
  - reports/agents/agent-2/TC-901/report.md
  - reports/agents/agent-2/TC-901/self_review.md
  - runs/tc901_ruleset_quotas_20260201_HHMMSS/tc901_evidence.zip

## Acceptance checks
- [ ] ruleset.schema.json extended with max_pages, style_by_section, limits_by_section
- [ ] All properties properly typed and constrained
- [ ] ruleset.v1.yaml has defaults for all 5 sections
- [ ] Defaults are sensible and consistent
- [ ] All documentation updated
- [ ] validate_swarm_ready.py passes
- [ ] pytest suite passes
- [ ] Schema validation passes
- [ ] Evidence bundle created
- [ ] No write fence violations

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
