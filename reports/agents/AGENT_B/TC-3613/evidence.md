# TC-3613 — Evidence

**Date**: 2026-02-28
**Agent**: agent_b

## What was built

- `HealStep.to_dict()` — defensive serialization, coerces non-dict triage_snapshot entries
- `HealResult.to_dict()` — stable-key method delegating to step.to_dict()
- `HealResult.initial_failed_gate_count: int = -1` — baseline for non-regressive exit code
- `write_heal_plan()` made defensive: try/except, returns None on failure, never raises
- `run_heal_loop()` sets `result.initial_failed_gate_count = failed_count` before main loop
- `heal` CLI exit code: non-regressive branch (final ≤ initial → exit 0)
- `drive --heal` exit code: same non-regressive contract
- `heal_plan.schema.json`: optional `initial_failed_gate_count` + `outcome` on step
- 19 new regression tests in `tests/unit/cli/test_tc3613_heal_exit_code.py`

## Test results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_tc3613_heal_exit_code.py -v
19 passed
```

## Prior failure mode reproduced + proven fixed

`TestWriteHealPlanDefensive::test_write_heal_plan_survives_serialization_error`:
- Patches `atomic_write_json` to raise `TypeError("simulated shape mismatch")`
- Verifies `write_heal_plan()` returns `None` (not raises)
- Verifies warning is logged containing "heal_plan.json"

`TestWriteHealPlanDefensive::test_write_heal_plan_with_non_dict_snapshot_does_not_crash`:
- Creates `HealStep` with non-dict `triage_snapshot` entries
- Verifies `write_heal_plan()` succeeds and coerces entries to `{"_raw": ...}`

## Non-regressive exit code proven

`TestExitCodeLogic::test_partial_improvement_exit_0`:
- initial=5, final=3, stop_reason=max_steps → exit code 0

`TestExitCodeLogic::test_stuck_at_baseline_exit_0`:
- initial=4, final=4, stop_reason=stuck → exit code 0

`TestExitCodeLogic::test_unknown_initial_exit_1`:
- initial=-1 (resume_failed) → exit code 1

## Ops report

`reports/ops/tc3613_heal_exit_code_20260228_1200.md`
