---
id: TC-4016
title: "Sync intake_bundle and understanding_bundle schemas with Phase 1-4 models"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [humming-greeting-kay, schema, blocking]
depends_on: [TC-4001, TC-4002, TC-4003, TC-4004]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4016_intake-bundle-schema-sync.md
  - specs/schemas/intake_bundle.schema.json
  - specs/schemas/understanding_bundle.schema.json
  - specs/schemas/evaluation_report.schema.json
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4016 — Schema Sync with Phase 1-4 Models

## Objective

The Phase 1-4 Understand redesign added new fields to `IntakeBundle`,
`ProductIdentity`, `ApiSurface`, `ClassBrief`, and `ProductEvidence` models.
The JSON schemas for these bundles were not updated, causing schema validation
failures that blocked all pilot runs. This taskcard syncs the schemas.

## Required spec references

- `src/launcher/models/intake.py` (IntakeBundle)
- `src/launcher/models/product.py` (ApiSurface, ClassBrief, ProductIdentity)
- `src/launcher/models/understanding.py` (ProductEvidence, LimitationEntry)

## Scope

### In scope

- Add `runtime_import` to `intake_bundle.schema.json`
- Add `runtime_import`, `platform_profile` to `understanding_bundle.schema.json` (product)
- Add `typed_methods`, `typed_properties`, `enums` to ClassBrief in understanding schema
- Add `enums`, `format_matrix` to ApiSurface in understanding schema
- Add `limitations`, `workflow_examples`, `install_recipe`, `missing_info`, `confidence` to product_evidence in understanding schema
- Add `api_surface_coverage`, `cross_page_findings` to `evaluation_report.schema.json`

### Out of scope

- Changing any model or worker code
- Adding new schemas

## Inputs

- `src/launcher/models/intake.py` — IntakeBundle definition
- `src/launcher/models/product.py` — ApiSurface, ClassBrief, ProductIdentity
- `src/launcher/models/understanding.py` — ProductEvidence
- `src/launcher/workers/evaluate/worker.py` — evaluate output fields

## Outputs

- Updated `specs/schemas/intake_bundle.schema.json`
- Updated `specs/schemas/understanding_bundle.schema.json`
- Updated `specs/schemas/evaluation_report.schema.json`

## Allowed paths

- plans/taskcards/TC-4016_intake-bundle-schema-sync.md
- specs/schemas/intake_bundle.schema.json
- specs/schemas/understanding_bundle.schema.json
- specs/schemas/evaluation_report.schema.json

### Allowed paths rationale

These are the 3 schemas that need updating to match models added in Phases 1-4.

## Implementation steps

### Step 1: Audit model vs schema mismatch

Run: `python -c "from launcher.models.intake import IntakeBundle; print(list(IntakeBundle.model_fields.keys()))"`
Compare against schema properties list.

### Step 2: Fix intake_bundle.schema.json

Add `runtime_import` string property.

### Step 3: Fix understanding_bundle.schema.json

Add all Phase 1-4 fields to product, api_surface.class_briefs, api_surface, and product_evidence.

### Step 4: Fix evaluation_report.schema.json

Add `api_surface_coverage` and `cross_page_findings` fields.

### Step 5: Verify pilot runs

Run: `.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml --stop-after understand`

## Failure modes

### Failure mode 1: Schema still fails after fix

**Detection**: Pipeline error with "Schema validation failed"
**Resolution**: Run model audit script; add any still-missing fields
**Gate**: Schema validation in graph_builder.py

### Failure mode 2: additionalProperties=false too strict for complex objects

**Detection**: Complex nested objects (MethodSignature, PlatformProfile) fail validation
**Resolution**: Use `"additionalProperties": true` for complex typed sub-objects
**Gate**: Schema validation

### Failure mode 3: Schema regression for downstream workers

**Detection**: planner/generate/evaluate workers fail input schema validation
**Resolution**: Check that understanding_bundle schema changes don't break planner input schema
**Gate**: Pipeline execution end-to-end

## Task-specific review checklist

- [x] `intake_bundle.schema.json` matches `IntakeBundle.model_fields`
- [x] `understanding_bundle.schema.json` product section has `runtime_import` and `platform_profile`
- [x] `understanding_bundle.schema.json` class_briefs has `typed_methods`, `typed_properties`, `enums`
- [x] `understanding_bundle.schema.json` api_surface has `enums` and `format_matrix`
- [x] `understanding_bundle.schema.json` product_evidence has all Phase 1-4 fields
- [x] `evaluation_report.schema.json` has `api_surface_coverage` and `cross_page_findings`
- [x] Pipeline runs end-to-end without schema validation errors

## Deliverables

1. Updated `specs/schemas/intake_bundle.schema.json`
2. Updated `specs/schemas/understanding_bundle.schema.json`
3. Updated `specs/schemas/evaluation_report.schema.json`

## Acceptance checks

- [x] `.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml --stop-after understand` completes without schema error
- [x] Full pipeline run (planner → evaluate) completes without schema error
- [x] Pilot generates 22 pages successfully (run ID: 260310_193521_3d_python_881e)

## Self-review

**What was done**: Audited 3 schemas against current model fields. Added all missing fields introduced by Phases 1-4 of the humming-greeting-kay redesign. Verified by running the full pilot pipeline end-to-end.

**Risk**: Low — adding optional fields to schemas; no existing behavior changes.

**Completeness**: All 3 schemas updated; pilot ran successfully end-to-end (22 pages, evaluate reached).

## E2E verification

```bash
# Verify intake + understand schema pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run \
  configs/pilots/aspose-3d-foss-python.yaml --stop-after understand
# Expected: "Worker understand completed" — no schema validation errors

# Verify full pipeline through evaluate
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run \
  configs/pilots/aspose-3d-foss-python.yaml \
  --resume-from planner --run-id 260310_193521_3d_python_881e \
  --stop-after evaluate
# Expected: "22" pages generated, evaluation_report.json written
```

Both commands ran successfully (run ID: `260310_193521_3d_python_881e`).
22 pages generated and evaluated: A+B=18%, D+F=5%, 0 CRITICAL findings.

**Expected artifacts**:
- `runs/260310_193521_3d_python_881e/understand_checkpoint.json`
- `runs/260310_193521_3d_python_881e/evaluation_report.json`
- `phase_store/pilot_quality_report.md`

## Integration boundary proven

**Upstream integration**: `configs/pilots/aspose-3d-foss-python.yaml` → run_loop → intake_checkpoint.json → understand_checkpoint.json (IntakeBundle and UnderstandingBundle schemas validated).

**Downstream integration**: `understand_checkpoint.json` → planner → generate → evaluate_checkpoint.json (EvaluationReport schema validated). Cross-page findings and api_surface_coverage fields pass through correctly.
