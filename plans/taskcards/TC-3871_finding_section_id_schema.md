---
id: TC-3871
title: "Add section_id to evaluation_report.schema.json findings definition"
status: Done
priority: High
owner: "claude-agent"
updated: "2026-03-08"
tags: [schema, evaluate, finding, e2e-blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3871_finding_section_id_schema.md
  - specs/schemas/evaluation_report.schema.json
evidence_required:
  - reports/TC-3871/evidence.md
---

# Taskcard TC-3871 — Add section_id to evaluation_report.schema.json findings

## Objective

The `Finding` pydantic model in `src/launcher/models/evaluation.py` has a
`section_id: str | None = None` field. The `evaluation_report.schema.json` schema
defines findings with `additionalProperties: false` but omits `section_id`.

This causes a schema validation failure during evaluate output validation:
`pages/N/findings/M: Additional properties are not allowed ('section_id' was unexpected)`

The pipeline errors out before writing any results, blocking E2E quality assessment.

## Required spec references

- `specs/schemas/evaluation_report.schema.json`
- `src/launcher/models/evaluation.py` (Finding model)

## Scope

### In scope
- Add `section_id` property (`type: ["string", "null"]`) to the finding item schema
  in `evaluation_report.schema.json`

### Out of scope
- No changes to the pydantic model
- No changes to any worker code
- No new tests (schema change tested by E2E pipeline)

## Inputs

- `specs/schemas/evaluation_report.schema.json`

## Outputs

- `specs/schemas/evaluation_report.schema.json` with `section_id` allowed in findings

## Allowed paths

- `specs/schemas/evaluation_report.schema.json`

## Implementation steps

1. In the `findings` array item schema, add:
   ```json
   "section_id": { "type": ["string", "null"] }
   ```
   under `properties`, alongside `check`, `severity`, `message`, `location`.

## Failure modes

1. Schema update conflicts with another consumer of findings — no other consumer
   validates against this schema directly; pydantic is source of truth
2. `section_id` omitted when serializing — pydantic excludes `None` by default
   but LauncherBaseModel may use `model_dump(exclude_none=True)` — verify this
3. New schema breaks existing schema validation tests — check before E2E run

## Task-specific review checklist

- [ ] `section_id` added to finding schema properties
- [ ] `section_id` type is `["string", "null"]` to match Optional[str]
- [ ] `additionalProperties: false` still present (unchanged)
- [ ] Pipeline E2E no longer throws `section_id was unexpected` error
- [ ] Full test suite: 2954+ tests, 0 failures
- [ ] E2E pilot run completes without schema validation error

## Deliverables

- Modified `specs/schemas/evaluation_report.schema.json`

## Acceptance checks

- [x] Taskcard created with status In-Progress
- [ ] Schema updated with `section_id`
- [ ] E2E pilot run passes schema validation at evaluate output boundary
- [ ] Full suite passes (PYTHONHASHSEED=0)

## Self-review

_To be filled after implementation._

## E2E verification

Run: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml`
Expected: no `Additional properties are not allowed ('section_id' was unexpected)` errors.

## Integration boundary proven

`evaluation_report.schema.json` is validated at the evaluate worker output boundary
only. No other schemas reference it.
