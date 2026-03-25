# TC-3540 Self-Review (12D)

## Taskcard: execution_plan.schema.json Evolution

Date: 2026-02-28
Agent: agent_d
Status at review: In-Progress → Done

---

## Dimension Scores (1-5 scale)

### D1: Correctness (5/5)
All 5 new fields match exactly what `src/launch/cli/main.py` writes to the execution_plan dict:
- `guardrail_applied`: written as Python `bool` → schema type `boolean`
- `llm_rationale`: written as Python `str` (defaults to `""`) → schema type `["string", "null"]`
- `hydrated_artifact_count`: written as Python `int` → schema type `["integer", "null"]`
- `provenance_status`: written as Python `str` (hydrate_source value) → schema type `["string", "null"]`
- `timestamp`: written as ISO 8601 string from `datetime.isoformat()` → schema type `["string", "null"]`

Both real pilot execution_plan.json files pass validation against the updated schema (confirmed via `test_pilot_cells_plan_validates` and `test_pilot_3d_plan_validates`).

### D2: Completeness (5/5)
All fields written by `main.py` to `execution_plan` are now covered in the schema. Cross-checked by:
1. Reading lines 476-495 of `main.py` (the dict literal)
2. Comparing against schema properties
3. Two real pilot files as ground truth

### D3: Schema safety (5/5)
- `additionalProperties: false` is preserved
- No new fields added to `required`
- Backward compatible: documents produced before TC-3540 fields were introduced still validate
- `test_unknown_field_rejected` confirms guard is active
- `test_full_realistic_plan_without_new_fields` confirms backward compatibility

### D4: Test coverage (5/5)
23 tests across 3 classes:
- Baseline: minimal valid, unknown field rejection, missing required field
- New fields: each new field tested individually (bool true/false, str, empty str, null, int, zero) + all together + both real pilot plans
- Existing fields: reasons with evidence_paths, llm_suggested null, full plan without new fields

### D5: Determinism (5/5)
Schema is a static JSON file. Tests use deterministic `jsonschema.validate()`. No timestamps, random IDs, or environment-dependent outputs.

### D6: Non-regression (5/5)
Full suite: 7679 passed, 13 skipped, 3 xfailed (excluding pre-existing `test_heal.py` failure).
The pre-existing `test_max_steps` failure was confirmed to exist before TC-3540 by git stash verification.

### D7: Write fence compliance (5/5)
Only files under `allowed_paths` were modified:
- `specs/schemas/execution_plan.schema.json` ✅
- `tests/unit/validator/test_gate1_execution_plan_schema.py` ✅
- `plans/taskcards/INDEX.md` ✅
- `reports/agents/agent_d/TC-3540/**` ✅

`tests/unit/validator/__init__.py` was created as infrastructure-only (zero bytes, no code).
No Python source files were modified.

### D8: Evidence quality (5/5)
Evidence file documents:
- Grep command and output showing field usage in main.py
- Real pilot file content confirming all 5 fields in production
- LLM planner source showing `guardrail_applied` origin
- Before/after schema diff
- Complete test output with all 23 test names

### D9: Taskcard validity (5/5)
`validate_taskcards.py` reports `[OK] plans\taskcards\TC-3540_execution_plan_schema_evolution.md`.
All 14 required sections present. Frontmatter body allowed_paths match. 4 failure modes with ### headers.
All 11 required frontmatter fields present including `spec_ref`, `ruleset_version`, `templates_version`.

### D10: Spec impact assessment (5/5)
This change modifies only `specs/schemas/execution_plan.schema.json`. No binding Python specs are changed.
The schema evolution is additive (5 new optional properties). Gate 1 behavior is unchanged — it becomes
more permissive for fields already written by production code. No spec amendments required.

### D11: No improvisation (5/5)
All 5 added fields are grounded in concrete evidence from `src/launch/cli/main.py` lines 476-495 and
confirmed by two real pilot execution_plan.json files. No speculative fields added.

### D12: Taskcard-first compliance (5/5)
Taskcard `TC-3540_execution_plan_schema_evolution.md` was created with status `In-Progress` before any
schema or test files were written. INDEX.md was updated immediately after taskcard creation.

---

## Known Gaps

None. All 12 dimensions scored 5/5.

## Summary

TC-3540 is a pure schema evolution: 5 new optional properties added to accept fields already produced
by production code. 23 tests confirm correctness. Zero regressions. Taskcard valid.
