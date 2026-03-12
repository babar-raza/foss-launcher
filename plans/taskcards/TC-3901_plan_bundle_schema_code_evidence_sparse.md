---
id: TC-3901
title: "Add code_evidence_sparse to plan_bundle.schema.json (schema drift blocks all pilots)"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-09"
tags: [schema, planner, pilot-blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3901_plan_bundle_schema_code_evidence_sparse.md
  - specs/schemas/plan_bundle.schema.json
evidence_required: []
---

# Taskcard TC-3901 — Add code_evidence_sparse to plan_bundle.schema.json

## Objective

All pilot re-runs fail at the planner stage with:
`planner.output: pages/N: Additional properties are not allowed ('code_evidence_sparse' was unexpected)`

The `PlannedPage` Pydantic model (`src/launcher/models/plan.py:34`) includes
`code_evidence_sparse: bool` (TR-01) but `specs/schemas/plan_bundle.schema.json`
does not — `additionalProperties: false` on page items causes a hard schema
validation failure that stops the pipeline after understand.

## Required spec references

- `specs/schemas/plan_bundle.schema.json`
- `src/launcher/models/plan.py`

## Scope

### In scope
- Add `code_evidence_sparse` boolean property to the `pages.items` object in
  `plan_bundle.schema.json`

### Out of scope
- Changing the Pydantic model, planner worker, or any other file
- Changing any other schema field

## Inputs

- `specs/schemas/plan_bundle.schema.json` — missing `code_evidence_sparse`
- `src/launcher/models/plan.py` line 34 — Pydantic field definition

## Outputs

- Updated `specs/schemas/plan_bundle.schema.json` with `code_evidence_sparse`

## Allowed paths

- plans/taskcards/TC-3901_plan_bundle_schema_code_evidence_sparse.md
- specs/schemas/plan_bundle.schema.json

## Implementation steps

### Step 1: Add code_evidence_sparse to pages.items.properties

In `plan_bundle.schema.json`, under `properties.pages.items.properties`, add:
```json
"code_evidence_sparse": {
  "type": "boolean",
  "default": false,
  "description": "TR-01: True when example_files + extracted_snippets < 3. Triggers EVIDENCE ABSENT prompt instruction in section_prompt."
}
```

## Failure modes

### Failure mode 1: Schema still rejects field after edit
**Detection**: Pipeline still fails with same validation error
**Resolution**: Verify JSON is valid and the property was added to the correct level
**Gate**: schema validation at planner output

### Failure mode 2: JSON parse error in schema file
**Detection**: `python -c "import json; json.load(open('specs/schemas/plan_bundle.schema.json'))"` fails
**Resolution**: Fix JSON syntax (missing comma, brace mismatch)
**Gate**: import at startup

### Failure mode 3: Other PlannedPage fields also missing from schema
**Detection**: Same error with different field name after this fix
**Resolution**: Compare PlannedPage model fields against schema properties
**Gate**: schema validation

## Task-specific review checklist

1. [x] `code_evidence_sparse` added to `pages.items.properties` (correct level)
2. [x] Type is `"boolean"` with `"default": false`
3. [x] Schema file parses as valid JSON after edit
4. [x] No other fields are added or removed
5. [x] `additionalProperties: false` unchanged (this field is now declared)
6. [x] All PlannedPage model fields present in schema after fix

## Deliverables

1. Updated `specs/schemas/plan_bundle.schema.json`

## Acceptance checks

1. [ ] `python -c "import json; json.load(open('specs/schemas/plan_bundle.schema.json'))"` succeeds
2. [ ] Fresh pilot run completes past planner stage without schema error
3. [ ] All PlannedPage model fields are in schema

## Self-review

### Verification results
- [ ] JSON parse check: PASS
- [ ] Pilot run reaches generate stage

## E2E verification

```bash
python -c "import json; s=json.load(open('specs/schemas/plan_bundle.schema.json')); print('code_evidence_sparse' in s['properties']['pages']['items']['properties'])"
# Expected: True
```

## Integration boundary proven

**Upstream**: Planner worker populates `code_evidence_sparse` on each `PlannedPage`
**Downstream**: Generate worker reads `code_evidence_sparse` to inject EVIDENCE ABSENT prompt
**Contract**: Schema validation at planner output boundary must accept the field
