---
id: TC-3894
title: "Fix plan_bundle schema missing claim_saturation and richness_tier fields"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [schema, bug, planner]
depends_on: [TC-3876]
allowed_paths:
  - plans/taskcards/TC-3894_plan-schema-missing-tc3876-fields.md
  - specs/schemas/plan_bundle.schema.json
evidence_required:
  - plans/taskcards/TC-3894_plan-schema-missing-tc3876-fields.md
---

# Taskcard TC-3894 — Fix plan_bundle schema missing claim_saturation and richness_tier fields

## Objective

TC-3876 added `claim_saturation` and `richness_tier` fields to `PlannedPage` (model) but did not update `plan_bundle.schema.json`. The schema has `"additionalProperties": false`, causing schema validation failures whenever the planner produces output (e.g., during heal worker re-runs), blocking content generation.

## Required spec references

- `specs/schemas/plan_bundle.schema.json` — defines the planner output contract

## Scope

### In scope
- Add `claim_saturation` (number, 0.0–1.0) property to page items in `plan_bundle.schema.json`
- Add `richness_tier` (string enum A/B/C) property to page items in `plan_bundle.schema.json`

### Out of scope
- Changes to the PlannedPage model (already correct)
- Changes to other schemas
- Changes to the planner worker logic

## Inputs

- `specs/schemas/plan_bundle.schema.json` (current, missing TC-3876 fields)
- `src/launcher/models/plan.py` (PlannedPage model — source of truth)

## Outputs

- `specs/schemas/plan_bundle.schema.json` updated with both fields

## Allowed paths

- plans/taskcards/TC-3894_plan-schema-missing-tc3876-fields.md
- specs/schemas/plan_bundle.schema.json

### Allowed paths rationale
The schema file must be updated to match the model. No other files need changing.

## Implementation steps

### Step 1: Add claim_saturation and richness_tier to plan_bundle.schema.json page items

Add after the existing `golden_unmatched_sections` property in the pages items:
```json
"claim_saturation": {
  "type": "number",
  "minimum": 0.0,
  "maximum": 1.0,
  "default": 1.0,
  "description": "TC-3876: Ratio of assigned claims to skeleton sections. <0.5 = thin page."
},
"richness_tier": {
  "type": "string",
  "enum": ["A", "B", "C"],
  "default": "A",
  "description": "TC-3876: Richness tier (A/B/C) propagated from planner for tier-aware generation."
}
```

### Step 2: Verify schema validates a real planner checkpoint

Run:
```bash
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
python -c "
import json
from launcher.io.schema_validation import validate
schema = json.load(open('specs/schemas/plan_bundle.schema.json'))
data = json.load(open('runs/260309_082341_note_python_35f6/planner_checkpoint.json', encoding='utf-8'))
validate(data, schema, context='test')
print('Schema validation: PASS')
"
```

### Step 3: Run relevant tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "plan" -v --tb=short
```

## Failure modes

### Failure mode 1: enum constraint too strict

**Detection**: planner writes `richness_tier` values outside A/B/C (e.g., "tier_a")
**Resolution**: change `enum` to plain `string` type, remove enum constraint
**Gate**: schema_validation

### Failure mode 2: default values conflict with model defaults

**Detection**: test failure due to default mismatch
**Resolution**: align defaults with model (claim_saturation=1.0, richness_tier="A")
**Gate**: test suite

### Failure mode 3: schema $schema version incompatibility

**Detection**: jsonschema raises on `minimum`/`maximum` with draft/2020-12
**Resolution**: verify schema uses draft-07 compatible format or adjust accordingly
**Gate**: schema_validation

## Task-specific review checklist

1. [ ] `claim_saturation` added with correct type (number), range (0.0–1.0), and description
2. [ ] `richness_tier` added with correct type (string/enum) and description
3. [ ] Schema still validates existing planner_checkpoint.json from a known-good run
4. [ ] `additionalProperties: false` remains on page items (no relaxation of other constraints)
5. [ ] Default values match PlannedPage model defaults (1.0 and "A")
6. [ ] Tests pass with no regressions
7. [ ] Docstrings updated for all new/changed public functions — N/A (schema only)
8. [ ] Spec file updated if worker behavior changed — N/A (schema alignment, no behavior change)
9. [ ] Schema `"description"` fields present for all new/changed properties — Yes (included above)
10. [ ] Checked `docs/README.md` ownership map — N/A (schema fix, no new feature)
11. [ ] If a new `docs/guides/` file was added: N/A

## Deliverables

1. `specs/schemas/plan_bundle.schema.json` with both fields added

## Acceptance checks

1. [ ] Schema validation passes on a planner output dict containing `claim_saturation` and `richness_tier`
2. [ ] Heal re-run of note_python `35f6` no longer throws planner schema error
3. [ ] All existing tests pass (PYTHONHASHSEED=0, 0 failures)

## Self-review

### Verification results
- [x] Tests: 162/162 PASS (PYTHONHASHSEED=0)
- [x] Validation: plan_bundle schema validates planner_checkpoint.json from note run 35f6 — PASS
- [x] Evidence captured: schema fix verified inline

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "plan" -v --tb=short
```

**Expected results**:
- 0 test failures
- Schema validates planner output with claim_saturation and richness_tier present

## Integration boundary proven

**Upstream**: Planner worker produces PlanBundle with PlannedPage items including claim_saturation/richness_tier
**Downstream**: Generate worker consumes plan_bundle; schema validation gates progress between them
**Contract**: plan_bundle.schema.json must allow all fields that PlannedPage emits
