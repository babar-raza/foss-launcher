---
id: TC-3775
title: "Fix content_manifest.schema.json — add content_path to page items"
status: Done
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [schema, bugfix, pipeline-blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3775_content_manifest_schema_fix.md
  - specs/schemas/content_manifest.schema.json
  - tests/unit/schemas/test_content_manifest_schema.py
evidence_required:
  - reports/TC-3775/evidence.md
---

# Taskcard TC-3775 — Fix content_manifest.schema.json — add content_path to page items

## Objective

The `content_manifest.schema.json` page items object has `"additionalProperties": false` but is missing the `content_path` field that the `GeneratedPage` pydantic model emits. This causes every pipeline run to crash at the generate→evaluate boundary (output schema validation failure in `graph_builder.py:275`). All 3 pilot runs (3D, Note, Slides) crashed with `run_failed` due to this.

## Required spec references

- `specs/schemas/content_manifest.schema.json` (page items definition)
- `src/launcher/models/content.py` (GeneratedPage model — authoritative field list)

## Scope

### In scope
- Add `content_path` property to page items in `content_manifest.schema.json`
- Verify schema matches all fields in `GeneratedPage` pydantic model

### Out of scope
- Changing `GeneratedPage` model (it's correct)
- Changing graph_builder validation logic (it's correct — schemas should be accurate)

## Inputs

- `src/launcher/models/content.py` — GeneratedPage model fields
- `specs/schemas/content_manifest.schema.json` — current schema (missing content_path)

## Outputs

- Updated `specs/schemas/content_manifest.schema.json` with content_path field

## Allowed paths

- plans/taskcards/TC-3775_content_manifest_schema_fix.md
- specs/schemas/content_manifest.schema.json
- tests/unit/schemas/test_content_manifest_schema.py

### Allowed paths rationale
- Taskcard itself
- The schema file that needs the fix
- Optional: test to validate schema/model alignment

## Implementation steps

### Step 1: Add content_path to schema

Add `"content_path": { "type": "string", "default": "", "description": "Hierarchical content path for file layout." }` to the page items properties in `content_manifest.schema.json`.

### Step 2: Verify all GeneratedPage fields are in schema

Cross-reference `GeneratedPage` model fields with schema properties to ensure no other fields are missing.

### Step 3: Run tests

Run existing tests to confirm no regressions.

## Failure modes

### Failure mode 1: Other missing fields in schema

**Detection**: Compare GeneratedPage model fields to schema properties
**Resolution**: Add any other missing fields
**Gate**: Output schema validation in graph_builder.py

### Failure mode 2: Schema change breaks evaluate input validation

**Detection**: Run pipeline and check evaluate worker starts
**Resolution**: Ensure evaluate's input schema (content_manifest.schema.json) matches updated output schema
**Gate**: Input schema validation at evaluate worker boundary

### Failure mode 3: Test regressions

**Detection**: pytest failures
**Resolution**: Update test assertions to include new field
**Gate**: CI test suite

## Task-specific review checklist

1. [ ] content_path added to schema page items properties
2. [ ] All GeneratedPage fields present in schema
3. [ ] additionalProperties remains false (schema is strict)
4. [ ] Field type matches pydantic model (string, default "")
5. [ ] Existing tests still pass
6. [ ] Schema validates against a real generate checkpoint

## Deliverables

1. Updated `specs/schemas/content_manifest.schema.json`
2. Evidence: test pass log

## Acceptance checks

1. [ ] Schema includes content_path field
2. [ ] All GeneratedPage model fields have schema counterparts
3. [ ] Tests pass
4. [ ] A generate checkpoint from a previous run validates against the updated schema

## Self-review

### Verification results
- [ ] Tests: PASS
- [ ] Validation: schema validates real checkpoint
- [ ] Evidence captured

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v -k "manifest or schema"
```

**Expected results**:
- All tests pass
- No schema validation errors

## Integration boundary proven

**Upstream**: Generate worker produces ContentManifest with content_path field
**Downstream**: graph_builder.py validates output against content_manifest.schema.json, then evaluate reads it
**Contract**: JSON schema at specs/schemas/content_manifest.schema.json must match GeneratedPage model exactly
