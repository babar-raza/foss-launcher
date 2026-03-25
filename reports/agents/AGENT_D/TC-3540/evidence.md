# TC-3540 Evidence: execution_plan.schema.json Evolution

## Summary

Added 5 new optional properties to `specs/schemas/execution_plan.schema.json` that are produced by
`src/launch/cli/main.py` but were absent from the schema, causing gate_1 validation rejections.

## Field Discovery

### Source: src/launch/cli/main.py lines 476-495

```python
execution_plan = {
    "schema_version": "1.0",
    "baseline_start_worker": decision.start_worker,
    "final_start_worker": final_start_worker,
    "reasons": [...],
    "target_repo_sha": target_repo_sha,
    "hydrate_source": hydrate_source,
    "hydrated_artifact_count": hydrated_count,   # NEW — int
    "llm_planner_used": llm_planner_used,
    "guardrail_applied": guardrail_applied,       # NEW — bool
    "llm_rationale": llm_rationale,              # NEW — str
    "goal": goal,
    "ruleset_version": ...,
    "templates_version": ...,
    "provenance_status": hydrate_source,         # NEW — str
    "timestamp": datetime.now(timezone.utc).isoformat(),  # NEW — str
}
```

### Grep Evidence

Command:
```
grep -n "guardrail_applied\|llm_rationale\|hydrated_artifact_count\|provenance_status\|timestamp" src/launch/cli/main.py
```

Output (relevant lines):
```
430:    guardrail_applied = False
431:    llm_rationale = ""
459:                guardrail_applied = suggestion.guardrail_applied
460:                llm_rationale = suggestion.rationale
486:        "hydrated_artifact_count": hydrated_count,
488:        "guardrail_applied": guardrail_applied,
489:        "llm_rationale": llm_rationale,
493:        "provenance_status": hydrate_source,
494:        "timestamp": datetime.now(timezone.utc).isoformat(),
```

### Real Pilot Confirmation

File: `runs/r_20260227T120454Z_launch_pilot-aspose-cells-foss-python_.../artifacts/execution_plan.json`
```json
{
  "guardrail_applied": false,
  "hydrated_artifact_count": 0,
  "llm_rationale": "",
  "provenance_status": "none",
  "timestamp": "2026-02-27T12:04:54.956982+00:00",
  ...
}
```

File: `runs/r_20260227T151804Z_launch_pilot-aspose-3d-foss-..._/artifacts/execution_plan.json`
```json
{
  "guardrail_applied": false,
  "hydrated_artifact_count": 22,
  "llm_rationale": "",
  "provenance_status": ".foss_state\\3d\\python\\artifacts\\37114723...",
  "timestamp": "2026-02-27T15:18:04.800723+00:00",
  ...
}
```

### LLM Planner Source (guardrail_applied)

File: `src/launch/autopilot/llm_planner.py`
```python
@dataclass(frozen=True)
class PlannerSuggestion:
    guardrail_applied: bool = False  # line 36
    rationale: str = ""              # line 33 (becomes llm_rationale)
```

## Schema Changes

### Before (lines 31-33 of original schema)

```json
    "heal_mode": {"type": "boolean"},
    "llm_planner_used": {"type": "boolean"}
  },
  "additionalProperties": false
```

### After (5 new properties added)

```json
    "heal_mode": {"type": "boolean"},
    "llm_planner_used": {"type": "boolean"},
    "guardrail_applied": {"type": "boolean"},
    "llm_rationale": {"type": ["string", "null"]},
    "hydrated_artifact_count": {"type": ["integer", "null"]},
    "provenance_status": {"type": ["string", "null"]},
    "timestamp": {"type": ["string", "null"]}
  },
  "additionalProperties": false
```

## Files Changed

- `specs/schemas/execution_plan.schema.json` — added 5 properties (lines 32-36)
- `tests/unit/validator/__init__.py` — created (empty)
- `tests/unit/validator/test_gate1_execution_plan_schema.py` — created (23 tests)
- `plans/taskcards/TC-3540_execution_plan_schema_evolution.md` — created (taskcard)
- `plans/taskcards/INDEX.md` — registered TC-3540

## Test Results

### New test file

Command: `.venv/Scripts/python.exe -m pytest tests/unit/validator/test_gate1_execution_plan_schema.py -v`

```
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaBaseline::test_minimal_valid_passes PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaBaseline::test_unknown_field_rejected PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaBaseline::test_missing_required_field_rejected PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_guardrail_applied_true_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_guardrail_applied_false_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_llm_rationale_string_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_llm_rationale_empty_string_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_llm_rationale_null_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_hydrated_artifact_count_integer_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_hydrated_artifact_count_zero_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_hydrated_artifact_count_null_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_provenance_status_string_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_provenance_status_none_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_provenance_status_null_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_timestamp_iso8601_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_timestamp_with_offset_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_timestamp_null_accepted PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_all_new_fields_together PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_pilot_cells_plan_validates PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaNewFields::test_pilot_3d_plan_validates PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaExistingFields::test_reasons_with_evidence_paths PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaExistingFields::test_llm_suggested_start_worker_null PASSED
tests\unit\validator\test_gate1_execution_plan_schema.py::TestExecutionPlanSchemaExistingFields::test_full_realistic_plan_without_new_fields PASSED

23 passed in 1.40s
```

### Full test suite (excluding pre-existing failure in test_heal.py)

Command: `.venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/cli/test_heal.py`

Result: **7679 passed, 13 skipped, 3 xfailed, 47 warnings in 198.89s**

Pre-existing failure confirmed (existed before TC-3540):
- `tests/unit/cli/test_heal.py::TestRunHealLoop::test_max_steps` — FAILED (pre-existing, unrelated to TC-3540)

### Taskcard validation

Command: `.venv/Scripts/python.exe tools/validate_taskcards.py`

Result: `[OK] plans\taskcards\TC-3540_execution_plan_schema_evolution.md`

## Determinism Verification

- The schema is a static JSON file — field definitions are deterministic.
- Tests use `jsonschema.validate()` which is deterministic given fixed schema + input.
- No time-based behavior, random IDs, or environment-dependent outputs introduced.
