---
id: TC-3801
title: "Schema alignment for skeleton_variant and ProductEvidence"
status: Done
priority: High
owner: "agent"
updated: "2026-03-07"
tags: [schema, planner, understand, pilot-blocker]
depends_on: [TC-3799]
allowed_paths:
  - plans/taskcards/TC-3801_schema_alignment_slides_pilot.md
  - specs/schemas/plan_bundle.schema.json
  - src/launcher/models/understanding.py
  - src/launcher/shared/code_analyzer.py
  - specs/schemas/understanding_bundle.schema.json
evidence_required:
  - runs/r_slides_pilot/events.ndjson
---

# Taskcard TC-3801 — Schema alignment for skeleton_variant and ProductEvidence

## Objective

Fix two schema mismatches that block the Aspose.Slides pilot run:
1. `skeleton_variant` field exists in Pydantic model but not in `plan_bundle.schema.json`
2. `ProductEvidence.capabilities` typed as `list[dict[str, str]]` but `code_analyzer` returns nested dicts with `evidence: {file, line}`

## Required spec references

- `specs/schemas/plan_bundle.schema.json` (defines planner output contract)
- `src/launcher/models/plan.py` (PlannedPage Pydantic model)
- `src/launcher/models/understanding.py` (ProductEvidence Pydantic model)
- `src/launcher/shared/code_analyzer.py` (_extract_capabilities returns evidence dicts)

## Scope

### In scope
- Add `skeleton_variant` property to `plan_bundle.schema.json`
- Fix `ProductEvidence.capabilities` type to accept nested evidence dicts (or coerce evidence to string in code_analyzer)

### Out of scope
- Changes to planner logic (TC-3799 already delivered skeleton_variant)
- Other schema drift unrelated to the Slides pilot failure

## Inputs

- Error log from `r_20260307T075955_6176c5e1` showing both failures
- Existing `plan_bundle.schema.json` (line 61: `additionalProperties: false`)
- `code_analyzer.py` line 229: `entry["evidence"] = evidence` (dict, not string)

## Outputs

- Updated `specs/schemas/plan_bundle.schema.json` with `skeleton_variant` property
- Updated `src/launcher/models/understanding.py` OR `src/launcher/shared/code_analyzer.py` to align evidence type
- Successful Slides pilot run (at least through planner)

## Allowed paths

- plans/taskcards/TC-3801_schema_alignment_slides_pilot.md
- specs/schemas/plan_bundle.schema.json
- specs/schemas/understanding_bundle.schema.json
- src/launcher/models/understanding.py
- src/launcher/shared/code_analyzer.py

### Allowed paths rationale
- `plan_bundle.schema.json`: Must add `skeleton_variant` property to match Pydantic model
- `understanding.py`: May need to widen `capabilities` type from `dict[str, str]` to `dict[str, Any]`
- `code_analyzer.py`: Alternative fix — coerce evidence dict to string before returning

## Implementation steps

### Step 1: Add skeleton_variant to plan_bundle.schema.json

Add `"skeleton_variant": {"type": "string", "description": "Template variant used for skeleton selection."}` to the page item properties in `plan_bundle.schema.json`.

### Step 2: Fix ProductEvidence capabilities type

Change `capabilities: list[dict[str, str]]` to `capabilities: list[dict[str, Any]]` in `understanding.py` line 80, since the `evidence` value is a dict `{file, line}` not a string.

### Step 3: Run existing tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

### Step 4: Re-run Slides pilot

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/pilot-aspose-slides-foss-aspose-slides-foss-for-python.yaml --verbose
```

## Failure modes

### Failure mode 1: Other pages schemas also missing skeleton_variant

**Detection**: Grep for `additionalProperties.*false` in other page-related schemas
**Resolution**: Update those schemas too
**Gate**: schema_validation at planner output boundary

### Failure mode 2: Downstream workers expect string evidence

**Detection**: Pydantic validation errors in generate/evaluate workers referencing capabilities.evidence
**Resolution**: Add evidence serializer or keep as `dict[str, Any]`
**Gate**: Worker output validation

### Failure mode 3: Test regressions from type widening

**Detection**: Test failures in understanding/code_analyzer tests
**Resolution**: Update test assertions for new type
**Gate**: Unit test suite

## Task-specific review checklist

1. [ ] `skeleton_variant` added to plan_bundle.schema.json with correct type
2. [ ] No other `additionalProperties: false` schemas block skeleton_variant
3. [ ] ProductEvidence.capabilities accepts evidence dicts without error
4. [ ] Existing tests still pass (PYTHONHASHSEED=0)
5. [ ] Slides pilot passes planner stage without schema error
6. [ ] No downstream workers break from widened type

## Deliverables

1. Updated `specs/schemas/plan_bundle.schema.json`
2. Updated `src/launcher/models/understanding.py`
3. Successful Slides pilot run evidence

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 pytest tests/ -x -q` passes
2. [ ] Slides pilot completes planner stage without `skeleton_variant` error
3. [ ] Slides pilot completes understand stage without `ProductEvidence` error
4. [ ] Full Slides pilot run produces content_bundle

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: planner output PASS
- [ ] Evidence captured: runs/r_slides_pilot/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/pilot-aspose-slides-foss-aspose-slides-foss-for-python.yaml --verbose
```

**Expected results**:
- All tests pass
- Slides pilot reaches at least evaluate stage
- No schema validation errors in logs

## Integration boundary proven

**Upstream**: Planner worker produces PlannedPage with skeleton_variant; code_analyzer produces capabilities with evidence dicts
**Downstream**: Generate worker consumes plan_bundle; Evaluate worker reads ProductEvidence
**Contract**: JSON schema + Pydantic models aligned on both fields
