---
id: TC-3868-H2
title: "Fix rollback semantics: rename, document scope, and implement regression guard"
status: Done
priority: P0 / Critical
owner: unassigned
updated: "2026-03-08"
tags: [heal, correctness, rollback, naming, regression]
depends_on: [TC-3868-H4]
allowed_paths:
  - plans/healing/TC-3868-H2-rollback-semantics.md
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_cli.py
  - tests/integration/test_heal_integration.py
---

# TC-3868-H2 — Fix rollback semantics: rename, document scope, implement regression guard

## Status: Not Started

## Gap linkage

- **G-3868-02**: `_restore_rollback_snapshot` is called identically on *both* the regression path
  and the non-regression path — it just deletes the snapshot file in both cases. For a regression
  the intent (per taskcard failure mode 5) is to "restore prior state". The current implementation
  does nothing restorative: no content files are reverted, no checkpoint is unwound. The name
  `_restore_rollback_snapshot` implies restoration but only deletes a JSON file. This is misleading
  and violates the principle of least surprise for any future engineer reading the code.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

**Part A — Rename to match actual behavior:**
Rename `_restore_rollback_snapshot` → `_remove_rollback_snapshot` everywhere. Update both call
sites in `_execute_worker_rerun` (regression path and non-regression path) and update the
function docstring to be honest: "Remove the transient rollback snapshot file. This version does
not restore pipeline artifact state — see TC-3868-H2 for the rollback scope contract."

**Part B — Update `_save_rollback_snapshot` docstring:**
Add a scope contract comment:
```
# Rollback scope (v1): metrics snapshot only. Pipeline artifacts (content files,
# worker checkpoints) are NOT backed up. Restoration of artifact state requires
# a separate mechanism (future work). The snapshot is used for regression detection
# only: compare before_metrics with after_metrics to decide whether to quarantine.
```

**Part C — Separate the two call sites in `_execute_worker_rerun`:**
Replace the current identical calls in both branches:

```python
# BEFORE (both branches call the same thing):
if outcome == "regressed":
    _restore_rollback_snapshot(run_dir, step_idx)
else:
    _restore_rollback_snapshot(run_dir, step_idx)

# AFTER (explicit, named correctly):
if outcome == "regressed":
    logger.warning(
        "[heal] Step %d regressed (df_rate %.3f → %.3f); "
        "artifact rollback not implemented — quarantine will block re-run.",
        step_idx,
        current_metrics.df_rate if current_metrics else 0.0,
        after_metrics.df_rate if after_metrics else 0.0,
    )
_remove_rollback_snapshot(run_dir, step_idx)
```

This eliminates the misleading else-branch and makes clear that the snapshot removal is always
unconditional (it is a transient file), while the regression warning makes the limitation visible
in logs.

**Part D — Update `HealStep.outcome` Literal** (coordinate with TC-3868-H5):
Confirm that `"checkpoint_invalid"` is removed from the Literal (handled in TC-3868-H5). This
task does not change the Literal but must not re-add it.

### Allowed paths:
- `plans/healing/TC-3868-H2-rollback-semantics.md`
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
All existing tests pass. The renamed function compiles without error.

### UI/Web/API:
N/A.

### Tests:
1. `test_remove_rollback_snapshot_removes_file` — renamed unit test that asserts
   `heal_rollback_0.json` is gone after `_remove_rollback_snapshot(tmp_path, 0)` is called.
2. `test_regression_logs_artifact_rollback_warning` — integration test that patches
   `_execute_worker_rerun` to return `("regressed", ...)` and asserts a WARNING is emitted
   (via `caplog`) containing "artifact rollback not implemented".
3. `test_save_rollback_snapshot_is_transient` — asserts that `_remove_rollback_snapshot`
   after `_save_rollback_snapshot` leaves no file behind.
4. Existing `test_save_rollback_creates_file` must still pass (function `_save_rollback_snapshot`
   is unchanged).

### Config respected end-to-end:
N/A — no config gate controls rollback behavior.

### No mock data in production paths:
The regression warning is emitted by real code in `_execute_worker_rerun`; tests must use
`caplog` or `patch("launcher.cli.heal.logger")` to capture it without suppressing it globally.

## Deliverables

1. **`src/launcher/cli/heal.py`** — Full file replacement with:
   - `_restore_rollback_snapshot` → `_remove_rollback_snapshot` (rename + docstring update)
   - `_save_rollback_snapshot` docstring updated with scope contract
   - `_execute_worker_rerun`: regression branch now logs the warning; both branches call
     `_remove_rollback_snapshot` (unconditional, not inside else)
2. **`tests/unit/cli/test_heal_cli.py`** — Rename `test_save_rollback_creates_file`'s
   import to `_remove_rollback_snapshot`; add new tests listed above.
3. **`tests/integration/test_heal_integration.py`** — Add regression-warning test.

Full file replacements — no stubs, no TODOs.

## Hard rules

- Keep public signatures: `run_heal()`, `_execute_worker_rerun()`, `_save_rollback_snapshot()`
  signatures unchanged. Only `_restore_rollback_snapshot` is renamed (it is a private helper).
- Update **all** call sites of the renamed function before completing the task.
- No network in offline tests.
- Deterministic runs: `PYTHONHASHSEED=0`.
- No new deps.
- Keep code/docs/tests in sync: grep for `_restore_rollback_snapshot` must return zero hits
  after the rename.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Correctness | No call site uses the old name; `grep _restore_rollback_snapshot src/` → 0 results |
| Naming/readability | `_remove_rollback_snapshot` accurately describes the action |
| Observability | Regression path emits a WARNING with before/after df_rate in the log |
| Robustness | Future engineer cannot confuse "remove transient file" with "restore state" |
| Minimality | No behavioral changes beyond the rename and the warning log line |
| Testability | Warning is captured with `caplog`, not stdout |
| Documentation | Scope contract in `_save_rollback_snapshot` docstring is unambiguous |

## Now (runbook)

```bash
# 1. Confirm all call sites
grep -n "_restore_rollback_snapshot" src/launcher/cli/heal.py
grep -n "_restore_rollback_snapshot" tests/

# 2. Apply rename in heal.py (function definition + both call sites)
# 3. Add scope contract docstring to _save_rollback_snapshot
# 4. Split the identical if/else in _execute_worker_rerun into unconditional
#    _remove_rollback_snapshot + conditional logger.warning

# 5. Update tests (rename import, add new tests)

# 6. Verify no old name remains
grep -rn "_restore_rollback_snapshot" src/ tests/
# Must return 0 results

# 7. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    tests/integration/test_heal_integration.py \
    -v --tb=short

# 8. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```
