---
id: TC-3905
title: "Add code_evidence_sparse to understanding_bundle schema"
status: Done
priority: Critical
owner: "agent"
updated: "2026-03-09"
tags: [schema, bug, tc3903-followup]
depends_on: [TC-3903]
allowed_paths:
  - plans/taskcards/TC-3905_schema_code_evidence_sparse.md
  - specs/schemas/understanding_bundle.schema.json
---

## Objective

TC-3903 added `code_evidence_sparse: bool` to `RichnessResult` in `product.py` and
`surface_classifier.py` but did not update `specs/schemas/understanding_bundle.schema.json`.
The schema has `"additionalProperties": false` in the `richness_tier` object, so the
pipeline crashes with `SchemaValidationError` when understand worker emits the new field.

## Scope

### In scope
- Add `code_evidence_sparse` boolean property to `richness_tier` in `understanding_bundle.schema.json`

### Out of scope
- Any code changes — schema only

## Allowed paths
- specs/schemas/understanding_bundle.schema.json

## Implementation steps

Add `"code_evidence_sparse"` to the `richness_tier.properties` block and to `required`.

## Acceptance checks

1. [ ] `code_evidence_sparse` present in `richness_tier.properties`
2. [ ] All tests pass
3. [ ] Fresh pilot run proceeds past understand worker
