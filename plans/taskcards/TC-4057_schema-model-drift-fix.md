---
id: TC-4057
title: "Fix schema-model drift: FormatRecord + Claim in understanding_bundle schema"
status: In-Progress
priority: Critical
owner: "claude-sonnet-4-6"
updated: "2026-03-11"
tags: [schema, understand, hotfix, e2e-blocker]
depends_on: [TC-4056]
allowed_paths:
  - plans/taskcards/TC-4057_schema-model-drift-fix.md
  - specs/schemas/understanding_bundle.schema.json
evidence_required:
  - reports/TC-4057/evidence.md
---

# Taskcard TC-4057 — Fix schema-model drift: FormatRecord + Claim

## Objective

The pilot e2e run fails at the `understand.output` schema validation boundary.
`specs/schemas/understanding_bundle.schema.json` was not updated when `FormatRecord`
and `Claim` Pydantic models gained new fields. Fix the schema to match the models.

## Required spec references

- `specs/worker_understand.md` (output contract: understanding_bundle.json)
- `specs/system_contract.md` (Rule: schema must be kept in sync with Pydantic model)

## Scope

### In scope
- `FormatRecord` in `understanding_bundle.schema.json`:
  - Add missing fields: `extension` (string), `caveats` (array of strings), `source_evidence` (string)
  - Remove stale fields not in model: `extensions` (plural array), `confidence` (string), `source_file` (string)
- `Claim` in `understanding_bundle.schema.json`:
  - Add missing field: `claim_source` (string enum: llm | deterministic | docstring | llm_fallback)

### Out of scope
- Any model-side changes (models are correct; schema lags behind)
- Other schemas not in the e2e error trace

## Inputs

- `src/launcher/models/claims.py` — `Claim.claim_source` field definition
- `src/launcher/models/product.py` — `FormatRecord` field definitions
- `specs/schemas/understanding_bundle.schema.json` — schema to update
- E2e error trace: 2 violation categories (format_matrix + claims)

## Outputs

- `specs/schemas/understanding_bundle.schema.json` updated
- `reports/TC-4057/evidence.md` with e2e pilot run result confirming fix

## Allowed paths

- `plans/taskcards/TC-4057_schema-model-drift-fix.md`
- `specs/schemas/understanding_bundle.schema.json`

### Allowed paths rationale
Only the schema file needs to change. No model, worker, or test changes required.

## Implementation steps

### Step 1: Fix FormatRecord item schema

Current `format_matrix.items` properties:
```json
{
  "name": ...,
  "can_import": ...,
  "can_export": ...,
  "extensions": { "type": "array", "items": {"type": "string"} },  <- WRONG (plural, not in model)
  "confidence": { "type": "string" },  <- WRONG (not in FormatRecord)
  "source_file": { "type": "string" }, <- WRONG (not in FormatRecord)
  "test_count": ...
}
```

Correct model fields (`src/launcher/models/product.py FormatRecord`):
- `name: str`
- `extension: str = ""`           — singular, default empty
- `can_import: bool = False`
- `can_export: bool = False`
- `caveats: list[str] = []`       — list of strings
- `test_count: int = 0`
- `source_evidence: str = ""`     — "file:line" provenance string

**Change**: replace stale properties (`extensions`, `confidence`, `source_file`) with
correct properties (`extension`, `caveats`, `source_evidence`).

### Step 2: Fix Claim item schema

Current `claims.items` properties do not include `claim_source`.

Correct model field (`src/launcher/models/claims.py Claim`):
- `claim_source: Literal["llm", "deterministic", "docstring", "llm_fallback"] = "llm"`

**Change**: add `claim_source` property with enum type to `claims.items.properties`.

### Step 3: Verify

Re-run pilot with `--stop-after understand`. Should complete with no schema errors.

## Failure modes

### Failure mode 1: Additional stale fields exist beyond the two identified

**Detection**: Schema validation still fails after fix with new property names.
**Resolution**: Diff full model field list against schema properties.
**Gate**: Zero schema validation errors from `understand.output` validation.

### Failure mode 2: Other schemas also lag behind models

**Detection**: Pipeline fails at a later worker boundary (planner, generate, etc.)
**Resolution**: Treat each boundary failure as a separate hotfix.
**Gate**: This taskcard only covers `understand.output`; other workers are out of scope.

### Failure mode 3: Schema change breaks existing snapshot/golden tests

**Detection**: `pytest tests/unit/` fails on snapshot comparison tests.
**Resolution**: Inspect failing tests — `additionalProperties: false` change may affect
existing test fixtures. Update fixture snapshots if needed.
**Gate**: All unit tests pass after schema update.

## Task-specific review checklist

1. [ ] `FormatRecord.extension` (singular) in schema properties
2. [ ] `FormatRecord.caveats` as array of strings in schema properties
3. [ ] `FormatRecord.source_evidence` as string in schema properties
4. [ ] Stale `extensions`, `confidence`, `source_file` removed from FormatRecord schema
5. [ ] `Claim.claim_source` as string enum in schema properties
6. [ ] `additionalProperties: false` preserved on both objects
7. [ ] Pilot `--stop-after understand` completes without schema error

## Deliverables

1. `specs/schemas/understanding_bundle.schema.json` corrected
2. `reports/TC-4057/evidence.md` with pilot run output confirming no schema errors

## Acceptance checks

1. [ ] Pilot run `--stop-after understand` exits cleanly (no ValueError: Schema validation failed)
2. [ ] `FormatRecord` schema properties match `src/launcher/models/product.py FormatRecord` exactly
3. [ ] `Claim` schema properties match `src/launcher/models/claims.py Claim` exactly
4. [ ] `PYTHONHASHSEED=0 pytest tests/unit/ -q` — all pass

## Self-review

### Verification results
- [ ] Tests: TBD
- [ ] Validation: TC-4057 acceptance checks TBD
- [ ] Evidence captured: reports/TC-4057/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml --stop-after understand --stream
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --deselect=tests/unit/workers/test_publish.py::TestDeployIntegration
```

## Integration boundary proven

**Before**: `understand.output` schema validation raises `ValueError` on every pilot run
**After**: `understand.output` passes schema validation; pipeline continues to planner
