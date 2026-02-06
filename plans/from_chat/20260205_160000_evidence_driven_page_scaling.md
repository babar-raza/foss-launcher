# Evidence-Driven Page Scaling + Configurable Page Requirements
**Materialized**: 2026-02-05T16:00:00Z
**Source**: Chat conversation → `C:\Users\prora\.claude\plans\spicy-floating-tome.md`
**Status**: Active

## Context

Repositories with vastly different evidence volumes (42 vs 806 claims, 18 vs 138 formats) generate the same number of .md files. The page count is determined by hardcoded tier logic in `plan_pages_for_section()` and static ruleset quotas — neither scales with evidence. Additionally, mandatory page lists are hardcoded in Python rather than configurable per site/family.

## Goals

1. Richer repos MUST produce more pages than simpler repos across all subdomains
2. Per-subdomain mandatory page lists MUST be configurable through ruleset + family configs
3. Implement the spec 06 Optional Page Selection Algorithm (quality_score)
4. All spec artifacts (schemas, gates, contracts, specs) MUST be updated consistently
5. Maintain determinism (same input = same output)
6. No regressions in existing test suite

## Assumptions

- [VERIFIED] page_plan.schema.json already has page_role enum and content_strategy — no structural page schema changes needed
- [VERIFIED] ruleset.schema.json uses sectionMinPages $def — can be extended with mandatory_pages + optional_page_policies
- [VERIFIED] Gate 14 already exists in spec 09 — needs one new rule (GATE14_MANDATORY_PAGE_MISSING)
- [UNVERIFIED] family_overrides merge strategy: global + family = union (not replace). Must verify no edge cases.
- [UNVERIFIED] Existing tests don't assert exact page counts that would break with evidence scaling

## Steps

### Workstream 1 — Agent D: Specs & Schemas (Part C, independent)
1. Update `specs/rulesets/ruleset.v1.yaml`: add mandatory_pages + optional_page_policies per section, add family_overrides, update min_pages
2. Update `specs/schemas/ruleset.schema.json`: extend sectionMinPages $def with mandatory_pages[] + optional_page_policies[], add family_overrides
3. Update `specs/schemas/page_plan.schema.json`: add evidence_volume + effective_quotas optional properties
4. Update `specs/schemas/validation_report.schema.json`: add GATE14_MANDATORY_PAGE_MISSING error code
5. Update `specs/06_page_planning.md`: configurable requirements, tier softening, evidence scoring docs
6. Update `specs/07_section_templates.md`: per-feature workflow template expectations
7. Update `specs/08_content_distribution_strategy.md`: configurable page requirements section
8. Update `specs/09_validation_gates.md`: Gate 14 mandatory page presence rule
9. Update `specs/21_worker_contracts.md`: W4 contract update (new inputs/outputs)

### Workstream 2 — Agent B: W4 Implementation (Parts A + B)
1. B4: Soften CI-absent tier reduction in determine_launch_tier()
2. A4: Add load_and_merge_page_requirements() — reads ruleset mandatory_pages + family_overrides, merges
3. B1: Add compute_evidence_volume() — quality_score formula
4. B2: Add compute_effective_quotas() — tier coefficients × evidence targets
5. B3: Add generate_optional_pages() — spec 06 algorithm implementation
6. B5: Refactor execute_ia_planner() to use config-driven mandatory pages + evidence scaling
7. B6: Add evidence_volume + effective_quotas to page_plan output dict

### Workstream 3 — Agent B: W7 Gate 14 (Part C5)
1. Add mandatory page presence check to Gate 14 validate_content_distribution()
2. Load merged page requirements config
3. Emit GATE14_MANDATORY_PAGE_MISSING for absent mandatory slugs

### Workstream 4 — Agent C: Tests & Verification
1. Create test_w4_evidence_scaling.py with tests for all new functions
2. Run existing test suite for regressions
3. Verify determinism (two runs with same input)
4. Collect evidence artifacts

### Workstream 5 — Agent D: Final Documentation
1. Update reports/STATUS.md
2. Update reports/CHANGELOG.md

## Acceptance Criteria

- [ ] `pytest tests/unit/workers/test_w4_evidence_scaling.py -v` — all pass
- [ ] `pytest tests/unit/workers/test_w4_*.py -v` — no regressions
- [ ] `pytest tests/ -v` — full suite green
- [ ] ruleset.v1.yaml validates against updated ruleset.schema.json
- [ ] page_plan.json validates against updated page_plan.schema.json
- [ ] Small repo (3D pilot) produces fewer pages than large repo (Note pilot)
- [ ] Both repos produce all mandatory pages from config
- [ ] All spec artifacts updated consistently (no orphan references)

## Risks + Rollback

- **Risk**: Existing tests assert exact page counts → fix by updating assertions
- **Risk**: family_overrides merge logic could produce duplicate slugs → deduplicate in merge
- **Risk**: Template pathway conflicts with config-driven mandatory pages → config-driven pages take precedence, template pages become optional
- **Rollback**: Revert all changes (single coherent changeset)

## Evidence Commands

```bash
# Unit tests for new functions
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_evidence_scaling.py -v

# Existing W4 tests (regression)
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_*.py -v

# Full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v

# Schema validation (manual check)
python -c "import json, jsonschema; jsonschema.validate(json.load(open('specs/rulesets/ruleset.v1.yaml')), json.load(open('specs/schemas/ruleset.schema.json')))"

# Pilot runs (after implementation)
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/vfv_evidence_scaling_3d
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/vfv_evidence_scaling_note
```

## Open Questions

None — all clarified during planning phase (tier reduction: fix together, quotas: keep current).
