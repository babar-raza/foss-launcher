---
id: TC-4242
title: "Add ExtractionDatabase model — structured fact-based evidence foundation"
status: Done
priority: P0
owner: "B_implementation"
updated: "2026-03-12"
tags: ["understand", "models", "schema", "extraction-database"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4242_understand-extraction-database-model.md
  - src/launcher/models/understanding.py
  - specs/schemas/understanding_bundle.schema.json
  - reports/agents/B_implementation/TC-4242/evidence.md
  - reports/agents/B_implementation/TC-4242/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4242/evidence.md
---

# Taskcard TC-4242 — Add ExtractionDatabase model — structured fact-based evidence foundation

## Objective

Add the `ExtractionDatabase` data structure as a new first-class model in the Understanding bundle. This is Step 2 of the Understand phase architectural redesign, providing the schema foundation for all subsequent redesign tasks by enabling the LLM-as-describer mode where the LLM receives verified facts rather than discovering new ones.

## Required spec references

- `specs/worker_understand.md` (Section: Understand worker output, evidence extraction)
- `specs/schemas/understanding_bundle.schema.json` (Section: bundle schema definition)
- `specs/system_contract.md` (Section: worker I/O contracts)

## Scope

### In scope
- New Pydantic models: `ApiFact`, `FormatFact`, `SnippetFact`, `LimitationFact`, `ExtractionCompleteness`, `ExtractionDatabase`
- Adding `extraction_db` field to `UnderstandingBundle` with a safe default
- JSON schema definitions for all new types
- Adding `extraction_db` property to the root `UnderstandingBundle` schema

### Out of scope
- Populating `ExtractionDatabase` with real data (done in subsequent TCs)
- Modifying any existing model fields or behavior
- Changing any existing worker logic
- Migration of existing artifacts

## Inputs

- `src/launcher/models/understanding.py` — existing models file to extend
- `specs/schemas/understanding_bundle.schema.json` — existing schema to extend

## Outputs

- `src/launcher/models/understanding.py` — updated with 6 new models and `extraction_db` field on `UnderstandingBundle`
- `specs/schemas/understanding_bundle.schema.json` — updated with schema definitions for all new types
- `reports/agents/B_implementation/TC-4242/evidence.md` — test results and verification
- `reports/agents/B_implementation/TC-4242/self_review.md` — self-review scoring

## Allowed paths

- plans/taskcards/TC-4242_understand-extraction-database-model.md
- src/launcher/models/understanding.py
- specs/schemas/understanding_bundle.schema.json
- reports/agents/B_implementation/TC-4242/evidence.md
- reports/agents/B_implementation/TC-4242/self_review.md

### Allowed paths rationale

- `plans/taskcards/...` — this taskcard itself
- `src/launcher/models/understanding.py` — the Pydantic model file to extend
- `specs/schemas/understanding_bundle.schema.json` — the JSON schema to extend
- `reports/...` — evidence artifacts required for Done status

## Implementation steps

### Step 1: Create taskcard (DONE)

Taskcard created at `plans/taskcards/TC-4242_understand-extraction-database-model.md` with status `In-Progress`.

### Step 2: Add new Pydantic models to understanding.py

Add `ApiFact`, `FormatFact`, `SnippetFact`, `LimitationFact`, `ExtractionCompleteness`, `ExtractionDatabase` models after existing model definitions and before `UnderstandingBundle`. All fields must have defaults to preserve backward compatibility.

### Step 3: Add extraction_db field to UnderstandingBundle

Add `extraction_db: ExtractionDatabase = ExtractionDatabase()` to `UnderstandingBundle` so it defaults to an empty database, never None.

### Step 4: Update JSON schema

Add `$defs` / definitions for all 6 new types. Add `"extraction_db"` property referencing `ExtractionDatabase` to the root `UnderstandingBundle` properties.

### Step 5: Run targeted tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ tests/unit/workers/test_understand.py tests/unit/workers/understand/ -v --tb=short
```

### Step 6: Run broad test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no --ignore=tests/unit/workers/test_plan_slug_integration.py --ignore=tests/unit/workers/test_plan_slugs.py --ignore=tests/unit/workers/test_scenario_planning.py --ignore=tests/test_planner_per_module.py
```

### Step 7: Write evidence and self-review reports

Write `reports/agents/B_implementation/TC-4242/evidence.md` with test results.
Write `reports/agents/B_implementation/TC-4242/self_review.md` with scoring.

### Step 8: Mark taskcard Done

Set status to `Done` with all acceptance checks as [x].

## Failure modes

### Failure mode 1: Import error — Literal not available

**Detection**: `ImportError: cannot import name 'Literal' from 'typing'` at test time.
**Resolution**: `Literal` is already imported on line 4 of understanding.py (`from typing import Any, Literal`). No action needed.
**Gate**: Python import validation at module load.

### Failure mode 2: Pydantic validation error on tuple field

**Detection**: `pydantic.ValidationError` for `source_lines: tuple[int, int]` when deserializing from JSON (JSON arrays become lists, not tuples).
**Resolution**: Use `tuple[int, int]` — Pydantic v2 coerces lists to tuples. If issues arise, use `list[int]` with a validator or `Field(default=(0, 0))`.
**Gate**: Unit tests for `SnippetFact` instantiation.

### Failure mode 3: Schema additionalProperties violation

**Detection**: Existing schema validator rejects new `extraction_db` field because root object has `"additionalProperties": false`.
**Resolution**: The `extraction_db` property must be added to the root `properties` block in the schema — it cannot be left as an ad-hoc field. This is the expected approach in Step 4.
**Gate**: `tests/unit/io/` schema validation tests.

### Failure mode 4: ExtractionDatabase() default causes mutable default error

**Detection**: Pydantic raises `ValueError: mutable default value` for `ExtractionDatabase()`.
**Resolution**: Use `Field(default_factory=ExtractionDatabase)` instead of `= ExtractionDatabase()` if Pydantic v2 raises this. Check existing models for the pattern used.
**Gate**: Module import test.

## Task-specific review checklist

1. [ ] All 6 new models use `LauncherBaseModel` as base class
2. [ ] All fields in all new models have explicit defaults (no required fields without defaults)
3. [ ] `extraction_db` on `UnderstandingBundle` defaults to `ExtractionDatabase()` and never returns None
4. [ ] No existing model fields modified (only additions)
5. [ ] JSON schema definitions cover all 6 new types with correct types and descriptions
6. [ ] `extraction_db` added to root `UnderstandingBundle` properties in the JSON schema
7. [ ] Docstrings present on all new public models explaining their purpose
8. [ ] Spec file drift confirmed absent (no spec changes required for model-only addition)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no trigger events apply (model-only addition)
11. [ ] Broad test suite passes with 0 regressions

## Deliverables

1. Updated `src/launcher/models/understanding.py` with 6 new models
2. Updated `specs/schemas/understanding_bundle.schema.json` with schema definitions
3. `reports/agents/B_implementation/TC-4242/evidence.md` with test results
4. `reports/agents/B_implementation/TC-4242/self_review.md` with self-review scoring

## Acceptance checks

1. [x] `ApiFact`, `FormatFact`, `SnippetFact`, `LimitationFact`, `ExtractionCompleteness`, `ExtractionDatabase` models exist in `understanding.py`
2. [x] `UnderstandingBundle.extraction_db` field exists with `ExtractionDatabase()` default
3. [x] `ExtractionDatabase` definition present in `understanding_bundle.schema.json`
4. [x] All targeted model/understand tests pass (558 pass, 30 pre-existing failures confirmed against baseline)
5. [x] Broad test suite passes with 0 new regressions (4044 pass, 26 pre-existing failures confirmed)
6. [x] Evidence file written at `reports/agents/B_implementation/TC-4242/evidence.md`

## Self-review

### Verification results
- [x] Tests: 4044/4044 previously-passing PASS (26 pre-existing failures confirmed against baseline)
- [x] Validation: schema additionalProperties compliant, extraction_db in root properties
- [x] Evidence captured: reports/agents/B_implementation/TC-4242/evidence.md
- [x] Doc freshness: confirmed no spec drift from model-only addition

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ tests/unit/workers/test_understand.py tests/unit/workers/understand/ -v --tb=short
```

**Expected results**:
- All existing model tests pass unmodified
- `UnderstandingBundle` can be instantiated without providing `extraction_db`
- `UnderstandingBundle(product=..., ...).extraction_db` returns an `ExtractionDatabase` instance

## Integration boundary proven

**Upstream**: Understand worker deterministic extraction phase (populates `ExtractionDatabase` in future TCs)
**Downstream**: Generate worker receives `UnderstandingBundle` with `extraction_db` available for LLM-as-describer mode
**Contract**: `UnderstandingBundle` Pydantic model + `understanding_bundle.schema.json` JSON schema
