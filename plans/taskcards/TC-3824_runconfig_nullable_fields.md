---
id: TC-3824
title: "Fix run_config.schema.json — nullable telemetry/budgets fields"
status: Done
priority: Critical
owner: "agent"
updated: "2026-03-08"
tags: [schema, bug, pilot-blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3824_runconfig_nullable_fields.md
  - specs/schemas/run_config.schema.json
  - tests/unit/io/test_run_config_schema_nullable.py
evidence_required:
  - tests/unit/io/test_run_config_schema_nullable.py (passing)
---

# Taskcard TC-3824 — Fix run_config.schema.json nullable fields

## Objective

Fix a pre-existing schema bug that causes every pilot run to crash before any worker
executes. `RunConfig.telemetry` is `TelemetryConfig | None = None`; Pydantic serializes
it as `null` in the graph state, but `run_config.schema.json` declares `"type": "object"`,
which JSON Schema Draft 2020-12 does not allow `null` for. Intake worker input validation
fires first and raises immediately.

Post-implementation self-review (SR-02) also reverted an incorrect `output` nullable change
and hardened the regression tests. See `plans/healing/SR_schema_null_fix_healing.md`.

## Required spec references

- `specs/schemas/run_config.schema.json` (defines the contract validated at intake.input)

## Scope

### In scope
- Change `"type": "object"` → `"type": ["object", "null"]` for `telemetry` and `budgets`
  in `specs/schemas/run_config.schema.json`
- `output` left as `"type": "object"` (not Optional in RunConfig — SR-01 corrected an
  overly broad initial patch)
- Add a regression test that validates a default `RunConfig` serialization against the
  real schema (hardened in SR-02)

### Out of scope
- Changes to Pydantic models (already correct)
- Changes to the loader or validation engine
- Changes to any other schema file

## Inputs

- `specs/schemas/run_config.schema.json` (current, broken)
- `src/launcher/models/run_config.py` (defines RunConfig with nullable fields)

## Outputs

- `specs/schemas/run_config.schema.json` (patched — 2 type arrays changed: telemetry, budgets)
- `tests/unit/io/test_run_config_schema_nullable.py` (regression tests — hardened by SR-02)

## Allowed paths

- plans/taskcards/TC-3824_runconfig_nullable_fields.md
- specs/schemas/run_config.schema.json
- tests/unit/io/test_run_config_schema_nullable.py

### Allowed paths rationale

- Schema file: the root-cause location of the bug
- Test file: regression coverage for the fix

## Implementation steps

### Step 1: Patch the schema

In `specs/schemas/run_config.schema.json`, change two fields:

| Field | Before | After |
|-------|--------|-------|
| `budgets` | `"type": "object"` | `"type": ["object", "null"]` |
| `telemetry` | `"type": "object"` | `"type": ["object", "null"]` |

Note: `llm` already `["object", "null"]`. `output` left as `"object"` (not Optional in model).

### Step 2: Add regression tests (hardened by SR-02)

See `tests/unit/io/test_run_config_schema_nullable.py` for the final hardened version
with 2 tests covering both the model serialization path and the YAML-loading path.

### Step 3: Verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_nullable.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Failure modes

### Failure mode 1: Additional nullable fields missed

**Detection**: `validate()` raises with a different field name than `telemetry`
**Resolution**: Run SR-04 schema-model alignment audit; apply `["object", "null"]` to
any field where the model allows `None`
**Gate**: Schema validation at `graph_builder.py:218`

### Failure mode 2: jsonschema version doesn't support type arrays

**Detection**: `TypeError` or unexpected behavior when parsing `["object", "null"]`
**Resolution**: Verify `jsonschema>=4.0` is installed; type arrays are valid Draft 2020-12
**Gate**: `schema_validation.py` uses `Draft202012Validator`

### Failure mode 3: Test schema file path drifts

**Detection**: Test raises `pytest.fail` "Schema file not found" (SR-02 hardening)
**Resolution**: Update `_REPO_ROOT` resolution in the test (3 parents from `tests/unit/io/`)
**Gate**: Hard-fail assertion in both test functions

## Task-specific review checklist

1. [x] `telemetry` changed to `["object", "null"]` in schema
2. [x] `budgets` changed to `["object", "null"]` in schema
3. [x] `output` left as `"object"` — SR-01 reverted an overly broad initial patch
4. [x] `llm` left unchanged (already correct)
5. [x] Regression tests load the real schema file (not a mock) — hardened by SR-02
6. [x] Full test suite passes with no regressions

## Deliverables

1. `specs/schemas/run_config.schema.json` — 2 type values changed (telemetry, budgets)
2. `tests/unit/io/test_run_config_schema_nullable.py` — 2 regression tests (hardened)

## Acceptance checks

1. [x] `test_default_runconfig_serialization_passes_schema` PASSES
2. [x] `test_yaml_with_null_telemetry_passes_schema` PASSES (SR-02)
3. [x] Full test suite: 0 failures, 0 errors (2224 passed after SR-02)
4. [x] Schema diff: telemetry and budgets nullable; output correctly non-nullable

## Self-review

### Verification results
- [x] Tests: 2224/2224 PASS (2 tests in nullable file + 2222 others)
- [x] Validation: schema parse PASS — both regression tests PASSED
- [x] Evidence captured: pytest output — 2 passed in 0.31s (nullable file); full suite pass

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_nullable.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 2 tests PASSED in nullable file
- All existing tests continue to pass

## Integration boundary proven

**Upstream**: `run_loop.py:147` serializes `RunConfig` → `state["config"]` dict
**Downstream**: `graph_builder.py:218` validates `state["config"]` against `run_config.schema.json` before intake worker runs
**Contract**: Fields that Pydantic serializes as `null` must have `["object", "null"]` in the schema; fields with default factories (not Optional) must keep `"object"` only
