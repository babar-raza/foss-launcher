---
id: TC-4253
title: "BUG: Add important_files_skipped to understanding_bundle schema (TC-4236 drift)"
status: Done
priority: Critical
owner: "Agent"
updated: "2026-03-12"
tags: [schema, understand, scout, bugfix, drift]
depends_on: [TC-4236]
allowed_paths:
  - plans/taskcards/TC-4253_schema-add-important-files-skipped.md
  - specs/schemas/understanding_bundle.schema.json
  - tests/unit/test_understanding_bundle_schema.py
evidence_required:
  - reports/TC-4253/evidence.md
---

# Taskcard TC-4253 — Add important_files_skipped to understanding_bundle schema

## Objective

TC-4236 added `important_files_skipped: int` to `RepoInventory` (the `repo`
field of `UnderstandingBundle`), but did not update
`understanding_bundle.schema.json`. The schema has `additionalProperties: false`
on `repo`, so any output with this field fails JSON schema validation and crashes
the pipeline. Add the field to the schema.

## Allowed paths

- plans/taskcards/TC-4253_schema-add-important-files-skipped.md
- specs/schemas/understanding_bundle.schema.json
- tests/unit/test_understanding_bundle_schema.py

## Implementation steps

### Step 1: Read current repo section of schema

Confirm `skipped_paths` is the last property in `repo.properties`.

### Step 2: Add `important_files_skipped`

Add after `skipped_paths`:
```json
"important_files_skipped": {
  "type": "integer",
  "description": "TC-4236: Count of files with importance rank >= 4 skipped due to budget exhaustion.",
  "default": 0
}
```

### Step 3: Add regression coverage

Add `tests/unit/test_understanding_bundle_schema.py` that validates a minimal
`UnderstandingBundle` payload containing `repo.important_files_skipped` against
`specs/schemas/understanding_bundle.schema.json`. This must fail without the
schema fix and pass with it.

## Acceptance checks

1. [ ] Schema validates: pilot run past Understand without ValueError
2. [ ] `important_files_skipped` in `understanding_bundle.schema.json`
3. [ ] Regression test validates schema acceptance for `repo.important_files_skipped`

## Self-review

### Verification results
- [x] Pilot run past understand: PASS (previous crash was due to missing field; now fixed)
- [x] Schema updated — `important_files_skipped` in `repo.properties` at line 232
- [x] Regression test added and passing — 2/2 tests pass in `tests/unit/test_understanding_bundle_schema.py`
