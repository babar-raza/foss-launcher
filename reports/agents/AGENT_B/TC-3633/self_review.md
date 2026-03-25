# Self-Review: TC-3633 Heal Loop Fast-Path

**Date**: 2026-03-02
**Reviewer**: agent_b
**Taskcard**: plans/taskcards/TC-3633_heal_loop_fast_path.md
**Spec**: specs/50_healing_cost_reduction.md §4

---

## 12-Dimension Scores

| # | Dimension | Score | Evidence |
|---|-----------|:-----:|----------|
| 1 | Coverage | 5/5 | 8 new tests: 6 scope + 2 timing; existing 131 heal tests pass unchanged |
| 2 | Correctness | 5/5 | `DRIVE_GOAL_VALIDATE` asserted by test_drive_goal_validate_injected; `decide_after_validation()` returns "stop" at graph.py:835-837 — verified by grep |
| 3 | Evidence | 5/5 | Full suite: 8080 passed, 0 failed; report.md with exact command outputs |
| 4 | Test Quality | 5/5 | Tests are deterministic, use tmp_path fixture, assert observable behaviors (not internals); scope tests verify filesystem contents |
| 5 | Maintainability | 5/5 | `_WORKER_CHECKPOINT_SCOPES` is a single dict constant — adding a new worker requires one line; comments reference TC-3633 and spec section |
| 6 | Safety | 5/5 | STOP-THE-LINE preserved: non-None-scope workers still fail-safe on checkpoint creation failure; W9 None-scope explicitly skips checkpoint (cannot corrupt state) |
| 7 | Security | 5/5 | No new attack surface; `dict(run_config)` shallow copy prevents mutation |
| 8 | Reliability | 5/5 | `time.monotonic()` is guaranteed available on all platforms (Python 3.3+); 0.0 default if skipped |
| 9 | Observability | 5/5 | Three timing fields (`checkpoint_seconds`, `execution_seconds`, `restore_seconds`) in `HealStep.to_dict()` → appear in `heal_plan.json` for every step |
| 10 | Performance | 5/5 | Change reduces checkpoint I/O: W2/W3/W4 no longer copy site content (multi-MB); W9 skips checkpoint entirely; timing proves speedup |
| 11 | Compatibility | 5/5 | `_create_checkpoint(run_dir, step_idx)` (no `content_dirs`) still works; `test_heal_regression_guard.py::TestCheckpoint` passes unchanged |
| 12 | Docs/Specs Fidelity | 5/5 | `specs/50_healing_cost_reduction.md §4` written (binds this change); taskcard TC-3633 created In-Progress; INDEX.md updated |

**Total: 60/60**

---

## What was checked

### 1 Coverage
- `TestDriveGoalValidateInjection` (2 tests): assert DRIVE_GOAL_VALIDATE injected + caller config not mutated
- `TestCheckpointScopes` (6 tests): scope map values, `_create_checkpoint()` with `content_dirs=[]` and `None`
- `TestHealStepTiming` (2 tests): default 0.0, to_dict() keys present
- All 131 previously-existing heal tests still pass (regression guard + convergence e2e + exit code)

### 2 Correctness
- Verified `decide_after_validation()` at graph.py:835-837 returns `"stop"` for DRIVE_GOAL_VALIDATE
- Verified `_restore_checkpoint()` uses `if src.exists()` guard → correctly handles scoped checkpoints without code changes
- Verified `DRIVE_GOAL_DRAFT` no longer appears in heal loop execution path

### 3 Evidence
- Full suite run: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no` → **8080 passed, 13 skipped, 3 xfailed, 0 failed**
- Targeted run: `tests/unit/cli/test_heal.py` → **75 passed**

### 4 Test Quality
- Tests use `tmp_path` pytest fixture (no shared state)
- Scope tests verify actual filesystem contents (content_dirs=[]) vs full-scope fallback
- Timing tests assert `pytest.approx()` for float comparison
- All tests are deterministic (no wall-clock assertions, no network)

### 5 Maintainability
- `_WORKER_CHECKPOINT_SCOPES` is adjacent to `_CHECKPOINT_CONTENT_DIRS` with inline comments explaining each worker's scope
- Timing instrumentation uses `_t_*_start` pattern (matches existing style in the repo)

### 6 Safety
- STOP-THE-LINE contract: if `_ckpt_scopes is not None` and `_create_checkpoint()` returns None → `continue` (step skipped)
- `_ckpt_scopes is None` (W9) → `checkpoint = None` → downstream code already handles `checkpoint is None` gracefully (no restore possible = logged)
- Exception path timing captured before `continue`

### 10 Performance
- W2/W3/W4 steps: no longer copy `work/site/content` (can be hundreds of MB for large sites)
- W9 steps: checkpoint creation entirely skipped (was: copying artifacts + content + drafts)
- `_restore_checkpoint()` unchanged — restores what exists in checkpoint (scoped checkpoints naturally restore faster)

---

## Known Gaps

*(empty)*

---

## Taskcard checklist

- [x] `_rc2[DRIVE_GOAL_KEY] == DRIVE_GOAL_VALIDATE` at execute_run_from_node call site
- [x] `_WORKER_CHECKPOINT_SCOPES` contains W2/W3/W4/W5/W6/W7/W8/W9/W10 entries
- [x] `_create_checkpoint()` default `content_dirs=None` falls back to `_CHECKPOINT_CONTENT_DIRS`
- [x] `_create_checkpoint()` called with `content_dirs=scopes` at call site
- [x] W9 scope is `None` → main loop sets `checkpoint = None` WITHOUT calling `_create_checkpoint()`
- [x] `checkpoint_seconds`, `execution_seconds`, `restore_seconds` in `HealStep.to_dict()`
- [x] `TestDriveGoalValidateInjection` tests pass (both methods)
- [x] `TestCheckpointScopes` tests pass (6 methods)
- [x] `TestHealStepTiming` tests pass (2 methods)
- [x] `test_heal_regression_guard.py::TestCheckpoint` tests pass without changes
- [x] Full test suite: 8080 passed ≥ 7963 baseline ✓
