---
id: TC-985
title: "W7 Validator Gate 14: Mandatory Page Presence Check"
status: Done
owner: Agent-B
updated: "2026-02-06"
depends_on:
  - TC-983
  - TC-984
priority: P2
spec_ref: fad128dc63faba72bad582ddbc15c19a4c29d684
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w7_validator/worker.py
  - reports/agents/agent_b/TC-985/**
evidence_required:
  - reports/agents/agent_b/TC-985/evidence.md
  - reports/agents/agent_b/TC-985/self_review.md
---

## Objective

Add mandatory page presence validation to W7 Gate 14. Load merged page requirements config, verify every mandatory slug exists in page_plan, emit GATE14_MANDATORY_PAGE_MISSING (code 1411) for any absent pages.

## Required spec references

- specs/09_validation_gates.md — Gate 14 Content Distribution Compliance (updated by TC-983)
- specs/rulesets/ruleset.v1.yaml — mandatory_pages per section + family_overrides (from TC-983)
- specs/schemas/validation_report.schema.json — GATE14_MANDATORY_PAGE_MISSING error code

## Scope

### In scope
1. Add mandatory page presence check to validate_content_distribution() in W7
2. Load merged page requirements (same merge logic as W4, or read from page_plan metadata)
3. Emit GATE14_MANDATORY_PAGE_MISSING for each missing mandatory slug
4. Apply profile-based severity (local=warning, ci=error, prod=error)

### Out of scope
- Spec/schema changes (TC-983)
- W4 changes (TC-984)
- Other Gate 14 rules (already implemented per TC-974)

## Inputs
- Updated specs from TC-983
- page_plan.json from W4 (with evidence_volume, effective_quotas)
- specs/rulesets/ruleset.v1.yaml (mandatory_pages, family_overrides)

## Outputs
- Updated src/launch/workers/w7_validator/worker.py with mandatory page check

## Allowed paths
- src/launch/workers/w7_validator/worker.py
- reports/agents/agent_b/TC-985/**

## Implementation steps

1. Read mandatory_pages configuration from ruleset (reuse or import merge logic from W4)
2. In validate_content_distribution(), after existing checks, iterate mandatory_pages per section
3. For each mandatory page, check if a page with matching slug exists in page_plan.pages
4. If missing, emit issue with code GATE14_MANDATORY_PAGE_MISSING (1411), severity based on profile
5. Include section name, expected slug, and expected page_role in issue message

## Failure modes

### Failure mode 1: Ruleset loading fails

**Detection:** YAML parse error when loading ruleset config.
**Resolution:** Guard with try/except, emit blocker issue with clear error message.
**Spec/Gate:** Gate 1 (Schema Validation)

### Failure mode 2: False positives for optional pages

**Detection:** Gate fails on pages that should be optional (not mandatory).
**Resolution:** Only check mandatory_pages list, not optional_page_policies.
**Spec/Gate:** Gate 14 (Content Distribution)

### Failure mode 3: Family override not applied

**Detection:** Wrong mandatory list checked; missing family-specific pages not flagged.
**Resolution:** Use same merge logic as W4 (product_slug from page_plan metadata).
**Spec/Gate:** Gate 14, specs/06_page_planning.md family_overrides

## Task-specific review checklist

1. [ ] Only mandatory_pages checked (not optional)
2. [ ] family_overrides correctly merged with global
3. [ ] Error code 1411 used consistently
4. [ ] Profile-based severity applied correctly
5. [ ] Issue message includes section, slug, page_role
6. [ ] No false positives for legitimately optional pages

## Deliverables

- Updated src/launch/workers/w7_validator/worker.py
- reports/agents/agent_b/TC-985/evidence.md
- reports/agents/agent_b/TC-985/self_review.md

## Acceptance checks

- [ ] Gate 14 validates mandatory page presence
- [ ] Missing mandatory pages produce GATE14_MANDATORY_PAGE_MISSING
- [ ] Profile-based severity applied (local=warning, ci/prod=error)
- [ ] No regressions in existing Gate 14 checks

## E2E verification

```bash
# Run W7 gate tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w7_gate14.py -v

# Run both pilots end-to-end to verify Gate 14 passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/e2e-985
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output output/e2e-985-note
```

**Expected artifacts:**
- **src/launch/workers/w7_validator/worker.py** - Contains Gate 14 mandatory page check
- **tests/unit/workers/test_w7_gate14.py** - All tests PASS
- **output/e2e-985/** - Pilot 3D pass with exit_code=0
- **output/e2e-985-note/** - Pilot Note pass with exit_code=0

## Integration boundary proven

**Upstream:** TC-984 W4 produces page_plan with mandatory pages. TC-983 defines mandatory_pages config.
**Downstream:** W9 PRManager consumes validation_report with Gate 14 results.
**Contract:** Gate 14 emits GATE14_MANDATORY_PAGE_MISSING (code 1411) for any missing mandatory page.

## Self-review

12-dimension self-review required. All dimensions >=4/5.
