---
id: TC-4220
title: "Fix evaluate output schema drift — hallucination_rate + GateResult.mode + issues type"
status: Done
priority: Critical
owner: "orchestrator"
updated: "2026-03-12"
tags: [evaluate, schema, bugfix]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4220_evaluate-schema-drift.md
  - specs/schemas/evaluation_report.schema.json
evidence_required:
  - reports/agents/B/TC-4220/evidence.md
---

# Taskcard TC-4220 — Fix evaluate output schema drift

## Objective

The Evaluate worker crashes at the pipeline boundary with `Schema validation failed:
Additional properties are not allowed ('hallucination_rate' was unexpected)`.
Three fields present in the `EvaluationReport` pydantic model are absent or wrong in
`evaluation_report.schema.json`, making the evaluate→publish handoff permanently broken.

## Required spec references

- `specs/schemas/evaluation_report.schema.json` (the schema being fixed)
- `src/launcher/models/evaluation.py` (the authoritative pydantic model)

## Scope

### In scope
- Add `hallucination_rate` property to root of `evaluation_report.schema.json`
- Add `mode` property to `gates.items` in the schema
- Fix `gates.items.issues.items` type from `string` to `object` (matches `Finding` model)

### Out of scope
- Changes to `evaluation.py` — the model is correct; schema must catch up
- Changes to the evaluate worker logic

## Inputs

- `specs/schemas/evaluation_report.schema.json` (current, missing 3 fields)
- `src/launcher/models/evaluation.py` (authoritative source of truth)

## Outputs

- Updated `specs/schemas/evaluation_report.schema.json` with all 3 fixes applied

## Allowed paths

- plans/taskcards/TC-4220_evaluate-schema-drift.md
- specs/schemas/evaluation_report.schema.json

### Allowed paths rationale
- Schema file is the only file needing change; pydantic model is already correct

## Implementation steps

### Step 1: Add `hallucination_rate` to root schema properties

In `evaluation_report.schema.json`, before the closing of the root `"properties"` block
(after `cross_page_findings`), add:

```json
"hallucination_rate": {
  "type": "number",
  "minimum": 0,
  "maximum": 1,
  "description": "TC-HAL-09: ratio of low-confidence claims (<0.5) used across all pages (0.0-1.0).",
  "default": 0.0
}
```

### Step 2: Add `mode` to `gates.items` schema

In `gates.items.properties`, after `"severity"`, add:

```json
"mode": {
  "type": "string",
  "description": "Gate evaluation mode (safety_critical or compensating).",
  "default": "safety_critical"
}
```

Also add `"mode"` to the `required` array... actually `mode` has a default so it should NOT be required.
Just add to `properties`, do NOT add to `required`.

### Step 3: Fix `gates.items.issues.items` type

Currently `"issues": { "type": "array", "items": { "type": "string" } }`.
Change to match `list[Finding]` — a Finding has `check, severity, message, location, section_id`:

```json
"issues": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "check": { "type": "string" },
      "severity": { "type": "string", "enum": ["critical", "high", "medium", "low"] },
      "message": { "type": "string" },
      "location": { "type": "string" },
      "section_id": { "type": ["string", "null"] }
    },
    "additionalProperties": false
  },
  "description": "List of Finding objects for this gate."
}
```

## Failure modes

### Failure mode 1: Schema edit misses a field

**Detection**: `pytest tests/unit/workers/test_evaluate.py -v` fails with schema validation error
**Resolution**: Compare `EvaluationReport.model_fields` against schema properties; add missing field
**Gate**: Schema validation gate in `graph_builder.py`

### Failure mode 2: Evaluate still crashes after fix

**Detection**: Pipeline run with `--stop-after evaluate` still shows `Schema validation failed`
**Resolution**: Check `schema_validation.py` for which field is rejected; add to schema
**Gate**: Live pipeline run

### Failure mode 3: New required fields break existing test fixtures

**Detection**: Test failures in `test_evaluate.py` referencing old fixture shapes
**Resolution**: Update fixtures to include new optional fields (with defaults)
**Gate**: Full test suite

## Task-specific review checklist

1. [ ] `hallucination_rate` added to root `properties` with type=number, min=0, max=1
2. [ ] `mode` added to `gates.items.properties` (not to required)
3. [ ] `gates.items.issues.items` changed from `{type: string}` to `Finding` object shape
4. [ ] Schema is valid JSON (no parse errors)
5. [ ] `pytest tests/unit/workers/test_evaluate.py -v` — all pass
6. [ ] `pytest -x -q` — no new failures
7. [ ] Docstrings: schema has `"description"` for all 3 new/changed properties
8. [ ] No model changes made (schema catches up to model, not reverse)

## Deliverables

1. Updated `specs/schemas/evaluation_report.schema.json`
2. Evidence at `reports/agents/B/TC-4220/evidence.md`

## Acceptance checks

1. [x] Schema parses as valid JSON
2. [x] `pytest tests/unit/workers/test_evaluate.py -v` — 219/219 PASS
3. [x] `pytest -x -q` — 4150 passed, 0 new failures
4. [x] Live pipeline `--stop-after evaluate` reaches `[evaluate] done` without schema crash (523s, Verdict: NO_GO on content quality)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-4220/evidence.md
- [ ] Doc freshness: schema updated to match model — no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -5
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml \
  --stop-after evaluate --resume-from generate \
  --run-id 260311_190711_cells_python_6882
```

**Expected results**:
- `test_evaluate.py` all pass
- Full suite: 0 new failures
- Live run: `[evaluate] done` without schema crash

## Integration boundary proven

**Upstream**: Evaluate worker produces `EvaluationReport` via pydantic model_dump()
**Downstream**: `graph_builder.py` validates output against `evaluation_report.schema.json` before handing to publish
**Contract**: Schema must accept every field pydantic serializes — model is source of truth
