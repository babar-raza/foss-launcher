---
id: TC-3868-H6
title: "Fill test coverage gaps: cross-step metrics, fallback path, end-to-end diagnose"
status: Done
priority: P1 / High
owner: unassigned
updated: "2026-03-08"
tags: [heal, testing, coverage, regression-guard]
depends_on: [TC-3868-H1, TC-3868-H2, TC-3868-H3, TC-3868-H5]
allowed_paths:
  - plans/healing/TC-3868-H6-test-coverage.md
  - tests/unit/cli/test_heal_cli.py
  - tests/integration/test_heal_integration.py
---

# TC-3868-H6 — Fill test coverage gaps: cross-step metrics, fallback path, end-to-end diagnose

## Status: Not Started

## Gap linkage

- **G-3868-09**: Three critical paths are untested:
  1. Cross-step `current_metrics` update — the G-3868-01 bug was invisible because no test
     asserted that `step[i+1].before_metrics == step[i].after_metrics`.
  2. `worker` → `full` checkpoint-invalid fallback — `executed_mode == "full"` when
     `load_worker_checkpoint` returns `None` was never exercised.
  3. End-to-end CLI `--mode diagnose` path — the integration test calls `_write_diagnosis()`
     manually rather than exercising the CLI command's own `_write_diagnosis` call, meaning
     the CLI entrypoint's diagnose branch is unverified.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

This TC is **tests only**. It adds regression guards for all three gap paths identified above.
No production code is changed. All test additions assume the fixes from H1, H2, H3, and H5
are already applied.

**Group 1 — Cross-step metrics update (unit, `TestHealModes`)**

Test: `test_current_metrics_advances_per_step`
- Setup: write a valid `evaluate_checkpoint.json` with 5 D-grade pages.
- Mock `_execute_worker_rerun` as an async function that returns a progressively improving
  `ReportMetrics` on each call:
  - Call 0: df_rate=0.80, outcome="improved"
  - Call 1: df_rate=0.60, outcome="improved"
  - Call 2: df_rate=0.40, outcome="improved"
- Mock `_call_llm_sync` to return `_VALID_DECISION_JSON`.
- Run `run_heal(run_dir, max_steps=3, mode="worker")`.
- Assert:
  - `result.steps[0].before_metrics.df_rate == approx(1.0)` (initial)
  - `result.steps[1].before_metrics.df_rate == approx(0.80)` (after step 0)
  - `result.steps[2].before_metrics.df_rate == approx(0.60)` (after step 1)
  - `result.final_metrics.df_rate == approx(0.40)` (after step 2)

Test: `test_diagnose_mode_metrics_do_not_advance`
- Same setup but `mode="diagnose"`.
- Mock `_call_llm_sync` to return `_VALID_DECISION_JSON` (2 steps).
- Assert all steps have `before_metrics.df_rate == approx(initial_df_rate)`.
  (diagnose returns `None` after_metrics, so `current_metrics` must not update.)

**Group 2 — Worker → full checkpoint fallback (unit, `TestHealModes`)**

Test: `test_worker_falls_back_to_full_on_invalid_checkpoint`
- Write `run_config.yaml` (minimal valid) and `evaluate_checkpoint.json` to `tmp_path`.
- Patch `launcher.resilience.checkpoint.load_worker_checkpoint` to return `None`.
- Patch `launcher.orchestrator.run_loop.execute_run` as `AsyncMock` returning `None`.
- Call `_execute_worker_rerun` directly with `mode="worker"` and a non-empty `checkpoint_id`.
- Assert returned 4-tuple has:
  - `fallback_reason == "checkpoint_invalid"`
  - `executed_mode == "full"` (after H3 is applied)
  - `outcome == "unchanged"` (because `execute_run` returned `None`)

Test: `test_worker_mode_no_fallback_when_checkpoint_valid`
- Same setup but patch `load_worker_checkpoint` to return a valid `WorkerCheckpoint` object
  and `restore_worker_checkpoint` to return `True`.
- Patch `execute_run` as `AsyncMock` returning `None`.
- Assert `fallback_reason is None` and `executed_mode == "worker"`.

**Group 3 — End-to-end CLI diagnose path (integration, `TestHealModeFlag`)**

Test: `test_cli_diagnose_mode_writes_heal_diagnosis_without_manual_call`
- Context: the existing `test_diagnose_mode_writes_heal_diagnosis_json` calls `_write_diagnosis`
  manually. This test replaces it with an end-to-end verification.
- Use `typer.testing.CliRunner` to invoke the `heal` CLI command with `--mode diagnose` on a
  `tmp_path` run directory that has a valid `evaluate_checkpoint.json`.
- Patch `_call_llm_sync` to return a valid decision JSON.
- Assert:
  - `runner.exit_code` is 0 or 2 (0 if no failing pages, 2 if df_rate > 0)
  - `(run_dir / "heal_diagnosis.json").exists()` is True
  - `json.loads(...)["actions"]` is a list
  - `_write_diagnosis` was NOT called manually by the test — the CLI invocation triggers it.

Test: `test_cli_invalid_mode_exits_nonzero`
- Use `CliRunner` to invoke `heal --mode bogus <run_dir>`.
- Assert `runner.exit_code != 0` and the output contains the expected error message.

### Allowed paths:
- `plans/healing/TC-3868-H6-test-coverage.md`
- `tests/unit/cli/test_heal_cli.py`
- `tests/integration/test_heal_integration.py`

### Forbidden: any other file/path (no production code changes)

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py::TestHealModes \
    tests/integration/test_heal_integration.py::TestHealModeFlag \
    -v --tb=short
```
All 7 new tests pass. All existing tests pass.

### UI/Web/API:
N/A.

### Tests:
All 7 tests defined above must pass. Specifically verify:

| Test name | Verifies |
|-----------|----------|
| `test_current_metrics_advances_per_step` | G-3868-01 fix is regression-guarded |
| `test_diagnose_mode_metrics_do_not_advance` | None-guard for diagnose mode |
| `test_worker_falls_back_to_full_on_invalid_checkpoint` | G-3868-03/04 fallback path |
| `test_worker_mode_no_fallback_when_checkpoint_valid` | Non-fallback happy path |
| `test_cli_diagnose_mode_writes_heal_diagnosis_without_manual_call` | E2E CLI diagnose |
| `test_cli_invalid_mode_exits_nonzero` | CLI mode validation |
| (existing) `test_mode_field_in_steps` | Still passes (no regression) |

### Config respected end-to-end:
`mode` is read from the CLI `--mode` flag and threaded through `run_heal()` → `_execute_worker_rerun()`.
The end-to-end test must pass the flag via `CliRunner.invoke`, not by calling `run_heal()` directly.

### No mock data in production paths:
`_call_llm_sync` is patched in all tests. `execute_run` is patched via `AsyncMock`.
`load_worker_checkpoint` / `restore_worker_checkpoint` are patched at the `launcher.resilience`
module level, not via monkeypatching the imported name in `heal.py`.

## Deliverables

1. **`tests/unit/cli/test_heal_cli.py`** — Add Group 1 (2 tests) and Group 2 (2 tests) to
   `TestHealModes`. Add necessary helpers (`_make_budget_with_remaining` with
   `remaining_runtime_s >= 60` for Group 2 tests that need to reach the execute path).
2. **`tests/integration/test_heal_integration.py`** — Add Group 3 (2 tests) to
   `TestHealModeFlag`. Import `typer.testing.CliRunner` and `heal_app` from `launcher.cli.heal`.

Full file replacements — no stubs, no TODOs.
New/updated tests cover happy path + at least one failure path per group.

## Hard rules

- No production code changes in this TC.
- `load_worker_checkpoint` and `restore_worker_checkpoint` must be patched at the
  `launcher.resilience.checkpoint` module, not at the heal.py import site, to ensure the
  deferred-import pattern is exercised correctly.
- Use `AsyncMock` (not `MagicMock`) for `execute_run`.
- CLI tests must use `typer.testing.CliRunner`, not `subprocess`.
- Deterministic runs: `PYTHONHASHSEED=0`.
- No new deps: `typer.testing` is part of typer's existing install.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Correctness | All 3 previously-uncovered paths now have an assertion that would have caught the original bugs |
| Thoroughness | Both the happy and failure sub-paths of each group are tested |
| Regression guard | `test_current_metrics_advances_per_step` fails if H1 fix is reverted |
| Integration fit | CLI test uses real Typer invocation, not internal function calls |
| Testability | `AsyncMock` for `execute_run` prevents real I/O; `tmp_path` isolates files |
| Minimality | Only test files change; no new test utilities beyond what is already in the file |
| No mock data in prod | Patches are at the correct module boundary |

## Now (runbook)

```bash
# 1. Verify typer.testing is available
.venv/Scripts/python.exe -c "from typer.testing import CliRunner; print('OK')"

# 2. Check that heal_app is importable from the cli module
.venv/Scripts/python.exe -c "from launcher.cli.heal import heal_app; print(heal_app)"

# 3. Check existing helper functions in test file (reuse _make_budget_with_remaining etc.)
grep -n "def _make_" tests/unit/cli/test_heal_cli.py

# 4. Write Group 1 tests (cross-step metrics)
#    - patch _execute_worker_rerun at launcher.cli.heal._execute_worker_rerun
#    - patch _call_llm_sync at launcher.cli.heal._call_llm_sync

# 5. Write Group 2 tests (checkpoint fallback)
#    - patch load_worker_checkpoint at launcher.resilience.checkpoint.load_worker_checkpoint
#    - patch restore_worker_checkpoint at launcher.resilience.checkpoint.restore_worker_checkpoint
#    - patch execute_run at launcher.orchestrator.run_loop.execute_run

# 6. Write Group 3 tests (CLI end-to-end)
#    - from typer.testing import CliRunner
#    - from launcher.cli.heal import heal_app
#    - runner = CliRunner()
#    - result = runner.invoke(heal_app, [str(run_dir), "--mode", "diagnose"])

# 7. Run all new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py::TestHealModes \
    tests/integration/test_heal_integration.py::TestHealModeFlag \
    -v --tb=short

# 8. Full suite — must pass >= prior count
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```
