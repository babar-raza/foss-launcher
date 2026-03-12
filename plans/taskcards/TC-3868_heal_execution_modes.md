---
id: TC-3868
title: "Heal Execution Modes (worker / full / diagnose)"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-08"
tags: [heal, cli, execution-modes]
depends_on: [TC-3851, TC-3852c]
allowed_paths:
  - plans/taskcards/TC-3868_heal_execution_modes.md
  - src/launcher/cli/heal.py
  - src/launcher/models/evaluation.py
  - tests/unit/cli/test_heal_cli.py
  - tests/integration/test_heal_integration.py
  - reports/agents/B/TC-3868/evidence.md
  - reports/agents/B/TC-3868/self_review.md
  - plans/from_chat/20260308_000000_from_chat_heal_modes.md
evidence_required:
  - reports/agents/B/TC-3868/evidence.md
---

# Taskcard TC-3868 — Heal Execution Modes (worker / full / diagnose)

## Objective

Replace the stub in `heal.py` (lines 444-447) that records every step as
"unchanged" with three selectable execution modes: `worker` (targeted
re-run with checkpoint validation), `full` (full pipeline re-run with
rollback), and `diagnose` (no execution, writes `heal_diagnosis.json`).
This enables heal to actually improve content quality, not just diagnose.

## Required spec references

- `specs/11_state_and_events.md` (Section: state recovery / checkpoints)
- `specs/09_resilience.md` (Section: budget gates, retry policy)

## Scope

### In scope
- Three execution modes for `_execute_worker_rerun()`: `worker`, `full`, `diagnose`
- `--mode` CLI flag on the `heal` typer command
- `HealStep.mode` and `HealStep.fallback_reason` fields in `evaluation.py`
- Expanded `HealStep.outcome` Literal: `budget_exceeded`, `checkpoint_invalid`, `diagnose_only`
- Helper functions: `_save_rollback_snapshot`, `_restore_rollback_snapshot`, `_write_diagnosis`, `_load_run_config`
- Unit tests (5 new) and integration tests (2 new)
- Evidence files and self-review

### Out of scope
- Actual LLM-driven content improvement in integration tests (execute_run mocked)
- Changes to run_loop.py execute_run signature
- Rollback of generate worker output files (only metrics are rolled back)

## Inputs

- `run_dir/evaluate_checkpoint.json` (EvaluationReport)
- `run_dir/run_config.yaml` (RunConfig for worker/full mode)
- `run_dir/worker_checkpoints/<checkpoint_id>.json` (for worker mode validation)
- `decision.action.worker` (str, which worker to re-run)

## Outputs

- `run_dir/heal_plan.json` (HealResult with mode/fallback_reason in each step)
- `run_dir/heal_diagnosis.json` (for --mode diagnose)
- `run_dir/heal_rollback_{step_idx}.json` (transient, removed after confirmation)
- `reports/agents/B/TC-3868/evidence.md`
- `reports/agents/B/TC-3868/self_review.md`

## Allowed paths

- plans/taskcards/TC-3868_heal_execution_modes.md
- src/launcher/cli/heal.py
- src/launcher/models/evaluation.py
- tests/unit/cli/test_heal_cli.py
- tests/integration/test_heal_integration.py
- reports/agents/B/TC-3868/evidence.md
- reports/agents/B/TC-3868/self_review.md
- plans/from_chat/20260308_000000_from_chat_heal_modes.md

### Allowed paths rationale
- `heal.py` — primary implementation file for the three modes
- `evaluation.py` — HealStep model needs `mode` and `fallback_reason` fields
- Test files — new test classes must be added
- Evidence files — required by governance

## Implementation steps

### Step 1: Create taskcard (this file)

Set status to In-Progress before touching protected paths.

### Step 2: Update evaluation.py

Add `mode: str = "worker"` and `fallback_reason: str | None = None` to `HealStep`.
Expand `outcome` Literal with `"budget_exceeded"`, `"checkpoint_invalid"`, `"diagnose_only"`.

### Step 3: Add helpers and `_execute_worker_rerun()` to heal.py

Add `_save_rollback_snapshot`, `_restore_rollback_snapshot`, `_write_diagnosis`,
`_load_run_config`, and `_execute_worker_rerun()` async helper before `run_heal()`.

### Step 4: Replace the stub

Replace lines 444-447 with a call to `_execute_worker_rerun()` and update
HealStep creation to include `mode` and `fallback_reason`.

### Step 5: Add `--mode` CLI flag

Add `mode: str = typer.Option("worker", "--mode", ...)` to `heal()` command.
Add validation and pass `mode` to `run_heal()`.

### Step 6: Write tests

5 unit tests in `TestHealModes`, 2 integration tests in `TestHealModeFlag`.

### Step 7: Run tests and verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py tests/integration/test_heal_integration.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```

### Step 8: Write evidence files

Write `reports/agents/B/TC-3868/evidence.md` and `self_review.md`.

### Step 9: Mark taskcard Done

Update status and fill acceptance checkboxes.

## Failure modes

### Failure mode 1: Circular import from `execute_run`

**Detection**: `ImportError: cannot import name 'execute_run'` or circular import traceback
**Resolution**: Defer the import inside `_execute_worker_rerun()` body rather than at module top
**Gate**: Import guard in `_execute_worker_rerun`

### Failure mode 2: RunConfig not found in run_dir

**Detection**: `_load_run_config()` returns None; `run_config.yaml` absent from run_dir
**Resolution**: Log warning and return `outcome="unchanged"` with `fallback_reason="config_not_found"`; tests pass because run_dir is a tmp_path without run_config
**Gate**: Graceful fallback — no exception propagated

### Failure mode 3: Budget gate returns zero remaining_runtime_s

**Detection**: `budget.remaining_for_step()["remaining_runtime_s"] < 60` is True
**Resolution**: Return `outcome="budget_exceeded"` without calling `execute_run()`
**Gate**: Budget check in `_execute_worker_rerun` before any I/O

### Failure mode 4: Checkpoint hash mismatch triggers infinite fallback loop

**Detection**: `fallback_reason="checkpoint_invalid"` appears in every step's HealStep
**Resolution**: `actual_mode` falls back to `"full"` once — not recursively; the budget gate then limits steps
**Gate**: `actual_mode` set once, not re-evaluated in same call

### Failure mode 5: Regression after re-run destroys metrics

**Detection**: `outcome == "regressed"` in step; `_restore_rollback_snapshot` called
**Resolution**: Snapshot is saved before `execute_run()`; restored and quarantine entry added on regression
**Gate**: Rollback snapshot file checked for existence before restore

## Task-specific review checklist

1. [ ] `_execute_worker_rerun` returns correct 3-tuple `(after_metrics, outcome, fallback_reason)` in all branches
2. [ ] `diagnose` mode returns `(None, "diagnose_only", None)` without touching execute_run
3. [ ] Budget gate returns `"budget_exceeded"` when remaining_runtime_s < 60
4. [ ] `HealStep` model validates with new `mode` and `fallback_reason` fields (old tests pass)
5. [ ] `--mode` flag present in `heal --help` output (typer registration)
6. [ ] Invalid mode (e.g., `--mode bogus`) raises `typer.BadParameter`
7. [ ] `heal_diagnosis.json` written in diagnose mode with `actions` key
8. [ ] Rollback snapshot `heal_rollback_{step_idx}.json` cleaned up after non-regression
9. [ ] All 5 unit tests in `TestHealModes` pass
10. [ ] All 2 integration tests in `TestHealModeFlag` pass
11. [ ] Existing 457-line unit test file unchanged (no deletions)
12. [ ] Full test suite >= 2899 passed

## Deliverables

1. `src/launcher/cli/heal.py` — three execution modes implemented
2. `src/launcher/models/evaluation.py` — HealStep with mode/fallback_reason
3. `tests/unit/cli/test_heal_cli.py` — 5 new tests in TestHealModes
4. `tests/integration/test_heal_integration.py` — 2 new tests in TestHealModeFlag
5. `reports/agents/B/TC-3868/evidence.md` — test counts and pass confirmation
6. `reports/agents/B/TC-3868/self_review.md` — 12-dimension self-review

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no` >= 2899 passed — 2936 passed
2. [x] `mode="diagnose"` returns `outcome=="diagnose_only"` and `after_metrics is None` — CONFIRMED by test_diagnose_mode_returns_diagnose_only
3. [x] `--mode` option registered in heal CLI (`heal --help` shows it) — typer.Option registered
4. [x] `heal_diagnosis.json` written when mode=diagnose — CONFIRMED by test_diagnose_mode_writes_heal_diagnosis_json
5. [x] HealStep serializes with `mode` and `fallback_reason` fields without breaking old tests — CONFIRMED (defaults backward-compatible)

## Self-review

### Verification results
- [x] Tests: 2936/2936 PASS
- [x] Validation: HealStep schema PASS (mode/fallback_reason default fields, expanded outcome Literal)
- [x] Evidence captured: reports/agents/B/TC-3868/evidence.md
- [x] Doc freshness: no spec drift (heal spec covers this)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py tests/integration/test_heal_integration.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```

**Expected results**:
- All new tests in TestHealModes and TestHealModeFlag pass
- Full suite >= 2899 passed
- No regressions in existing heal tests

## Integration boundary proven

**Upstream**: `evaluate_checkpoint.json` (EvaluationReport) and `run_config.yaml`
**Downstream**: `heal_plan.json` (HealResult) and optionally `heal_diagnosis.json`
**Contract**: HealStep.mode and HealStep.fallback_reason fields added with defaults so old deserialization is backward-compatible
