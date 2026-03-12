---
id: TC-3868-H1
title: "Fix current_metrics update across heal loop steps"
status: Done
priority: P0 / Critical
owner: unassigned
updated: "2026-03-08"
tags: [heal, correctness, loop-logic, metrics]
depends_on: [TC-3868-H4]
allowed_paths:
  - plans/healing/TC-3868-H1-current-metrics-update.md
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_cli.py
  - tests/integration/test_heal_integration.py
---

# TC-3868-H1 — Fix `current_metrics` update across heal loop steps

## Status: Not Started

## Gap linkage

- **G-3868-01**: `current_metrics` is set once to `initial_metrics` (line 483 of `heal.py`) and
  never reassigned inside the `for step_idx in range(max_steps)` loop. Every `HealStep` therefore
  records `before_metrics == initial_metrics` regardless of what prior steps achieved.
  `HealResult.final_metrics` always equals `initial_metrics`, making the session summary
  meaningless and the improvement-detection comparisons always relative to the original baseline
  rather than the evolving state.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

Inside `run_heal()`, after each successful step that produces non-None `after_metrics_raw`,
reassign `current_metrics = after_metrics_raw`. This must happen *before* building the next
iteration's `HealStep` so that the next step's `before_metrics` reflects the actual post-step
state.

Specifically, at the end of the per-step block (after `steps.append(step)` and after updating
quarantine), add:

```python
# Advance rolling baseline for next step
if after_metrics_raw is not None:
    current_metrics = after_metrics_raw
```

Also update the `_write_heal_plan` call in the `finally` block to use `current_metrics` (it
already does), but confirm the `HealResult` returned at the end of `run_heal()` also uses the
*final* `current_metrics` value, not the object captured at loop entry.

No other files need changes for this fix. The model (`evaluation.py`) is unchanged.

### Allowed paths:
- `plans/healing/TC-3868-H1-current-metrics-update.md`
- `src/launcher/cli/heal.py`
- `tests/unit/cli/test_heal_cli.py`
- `tests/integration/test_heal_integration.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    tests/integration/test_heal_integration.py \
    -v --tb=short
```
All existing tests pass. New tests (see Deliverables) pass.

### UI/Web/API:
N/A — heal is a CLI-only workflow.

### Tests:
1. A new unit test `test_current_metrics_advances_across_steps` in `TestHealModes`:
   - Runs `run_heal()` for 3 steps with `_execute_worker_rerun` mocked to return
     successively improving metrics (`df_rate` decreasing by 0.1 each step).
   - Asserts `result.steps[1].before_metrics.df_rate == result.steps[0].after_metrics.df_rate`.
   - Asserts `result.steps[2].before_metrics.df_rate == result.steps[1].after_metrics.df_rate`.
   - Asserts `result.final_metrics.df_rate == result.steps[-1].after_metrics.df_rate`.
2. A new unit test `test_diagnose_mode_current_metrics_unchanged`:
   - Runs `run_heal()` for 2 steps in `mode="diagnose"`.
   - Confirms `before_metrics` on step 1 equals `before_metrics` on step 0 (diagnose never
     updates metrics since `after_metrics_raw is None`).
3. All 12 acceptance checks in TC-3868 taskcard still pass (no regressions).

### Config respected end-to-end:
`current_metrics` update only occurs when `after_metrics_raw is not None`; `mode="diagnose"` path
(which returns `None`) must not trigger the update.

### No mock data in production paths:
`_execute_worker_rerun` is only mocked in tests; the live path uses real `execute_run`.

## Deliverables

1. **`src/launcher/cli/heal.py`** — Full file replacement. Change: add
   `if after_metrics_raw is not None: current_metrics = after_metrics_raw` after
   `steps.append(step)`. No other behavioral changes.
2. **`tests/unit/cli/test_heal_cli.py`** — Add `test_current_metrics_advances_across_steps` and
   `test_diagnose_mode_current_metrics_unchanged` to `TestHealModes`.
3. **`tests/integration/test_heal_integration.py`** — Add
   `test_three_step_final_metrics_matches_last_step` to `TestHealMultiStep` that asserts
   `result.final_metrics` is not `result.initial_metrics` when at least one step improved.

Full file replacements — no stubs, no TODOs.

If contracts/schemas change: N/A — model is unchanged.

## Hard rules

- Keep public signatures: `run_heal()`, `_execute_worker_rerun()` signatures unchanged.
- No network in offline tests: `_call_llm_sync` and `_execute_worker_rerun` must be patched.
- Deterministic runs: `PYTHONHASHSEED=0` required for all test invocations.
- No new deps: only stdlib + existing project modules.
- Keep code/docs/tests in sync: update docstring on `run_heal()` to document the rolling-baseline
  contract ("current_metrics advances after each non-diagnose step").

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Correctness | `result.steps[i+1].before_metrics == result.steps[i].after_metrics` for all non-diagnose steps |
| Thoroughness | Both the advancing-path and the non-advancing (diagnose) path are tested |
| Production grading | A 10-step heal session shows real metric progression in `heal_plan.json` |
| Robustness | `None`-guard prevents update when step produced no metrics |
| Minimality | Change is ≤5 lines of code; no unrelated modifications |
| Testability | New tests are deterministic, offline, and use `tmp_path` |
| Observability | `final_metrics` in `heal_plan.json` reflects true end state |

## Now (runbook)

```bash
# 1. Read current heal.py to find the exact insertion point
grep -n "steps.append(step)" src/launcher/cli/heal.py

# 2. Verify current_metrics is never reassigned in the loop (confirm the bug)
grep -n "current_metrics" src/launcher/cli/heal.py

# 3. Apply the fix: after steps.append(step), add:
#    if after_metrics_raw is not None:
#        current_metrics = after_metrics_raw

# 4. Add tests to TestHealModes (unit) and TestHealMultiStep (integration)

# 5. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py::TestHealModes \
    tests/integration/test_heal_integration.py::TestHealMultiStep \
    -v --tb=short

# 6. Run full suite — must be >= prior passing count
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```
