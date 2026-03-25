# TC-3633 Implementation Report — Heal Loop Fast-Path

**Date**: 2026-03-02
**Author**: agent_b (orchestrator session: pure-puzzling-ullman)
**Status**: Done
**Spec ref**: specs/50_healing_cost_reduction.md §4

---

## Changes Made

### 1. `src/launch/cli/heal.py`

#### 1a. Added `import time` (line 20)
```python
import time
```
Required for `time.monotonic()` timing calls.

#### 1b. Added `_WORKER_CHECKPOINT_SCOPES` constant (after line 44)
```python
_WORKER_CHECKPOINT_SCOPES: Dict[str, Optional[List[str]]] = {
    "W2": [],       # facts/evidence: only writes artifacts/
    "W3": [],       # snippets: only writes artifacts/
    "W4": [],       # ia_planner: only writes artifacts/
    "W5": ["drafts"],
    "W6": ["work/site/content"],
    "W7": ["drafts"],
    "W8": ["work/site/content"],
    "W9": None,     # validator: read-only
    "W10": ["work/site/content"],
}
```

#### 1c. Added timing fields to `HealStep` dataclass
```python
checkpoint_seconds: float = 0.0
execution_seconds: float = 0.0
restore_seconds: float = 0.0
```

#### 1d. Updated `HealStep.to_dict()` to include timing fields
Three new keys added: `checkpoint_seconds`, `execution_seconds`, `restore_seconds`.

#### 1e. Modified `_create_checkpoint()` signature
```python
def _create_checkpoint(
    run_dir: Path,
    step_idx: int,
    content_dirs: Optional[List[str]] = None,
) -> Optional[Path]:
```
When `content_dirs is None`, falls back to `_CHECKPOINT_CONTENT_DIRS` (backward compat).

#### 1f. Updated checkpoint call site in `run_heal_loop()`
```python
_t_ckpt_start = time.monotonic()
_ckpt_scopes = _WORKER_CHECKPOINT_SCOPES.get(worker, _CHECKPOINT_CONTENT_DIRS)
if _ckpt_scopes is None:
    checkpoint: Optional[Path] = None
else:
    checkpoint = _create_checkpoint(run_dir, step_idx, content_dirs=_ckpt_scopes)
    if checkpoint is None:
        continue  # STOP-THE-LINE
step.checkpoint_seconds = time.monotonic() - _t_ckpt_start
```

#### 1g. Switched drive goal: `DRIVE_GOAL_DRAFT` → `DRIVE_GOAL_VALIDATE`
```python
_rc2[DRIVE_GOAL_KEY] = DRIVE_GOAL_VALIDATE
```
Added import of `DRIVE_GOAL_VALIDATE` from `launch.orchestrator.graph` (line 739 inside function).

**Why**: `decide_after_validation()` returns `"stop"` immediately when
`drive_goal == DRIVE_GOAL_VALIDATE` (graph.py:835-837). This eliminates the
orchestrator's internal fix sub-loop that previously fired when `goal=draft` and
fixable issues existed, triggering repeated W10 passes inside one heal step.

#### 1h. Added execution timing
```python
_t_exec_start = time.monotonic()
try:
    run_result = execute_run_from_node(...)
    ...
except Exception as e:
    ...
    step.execution_seconds = time.monotonic() - _t_exec_start  # exception path
    continue
step.execution_seconds = time.monotonic() - _t_exec_start  # success path
```

#### 1i. Added restore timing in regression branch
```python
_t_restore_start = time.monotonic()
restored = _restore_checkpoint(run_dir, checkpoint)
step.restore_seconds = time.monotonic() - _t_restore_start
```

---

### 2. `tests/unit/cli/test_heal.py`

#### 2a. Updated imports
```python
from launch.cli.heal import (
    ...
    _CHECKPOINT_CONTENT_DIRS,
    _WORKER_CHECKPOINT_SCOPES,
    _create_checkpoint,
    ...
)
from launch.orchestrator.graph import DRIVE_GOAL_DRAFT, DRIVE_GOAL_KEY, DRIVE_GOAL_VALIDATE
```

#### 2b. Renamed `TestDriveGoalDraftInjection` → `TestDriveGoalValidateInjection`
- `test_drive_goal_draft_injected` → `test_drive_goal_validate_injected`
- Assertion updated: `== DRIVE_GOAL_VALIDATE` (was `== DRIVE_GOAL_DRAFT`)
- Docstring updated to explain single-pass semantics

#### 2c. Added `TestCheckpointScopes` class (6 tests)
- `test_w2_scope_is_empty_list`
- `test_w10_scope_includes_site_content`
- `test_w9_scope_is_none_skip_checkpoint`
- `test_unknown_worker_defaults_to_full_scope`
- `test_create_checkpoint_with_empty_scope_skips_content_dirs`
- `test_create_checkpoint_with_none_falls_back_to_full_scope`

#### 2d. Added `TestHealStepTiming` class (2 tests)
- `test_timing_fields_default_to_zero`
- `test_timing_fields_in_to_dict`

---

## Test Results

### Targeted heal tests
```
tests/unit/cli/test_heal.py: 75 passed, 0 failed
tests/unit/cli/test_heal_regression_guard.py: 25 passed, 0 failed
tests/unit/cli/test_heal_convergence_e2e.py: 12 passed, 0 failed
tests/unit/cli/test_tc3613_heal_exit_code.py: 19 passed, 0 failed
```

### Full suite
```
8080 passed, 13 skipped, 3 xfailed, 0 failed
(run time: 150.85s)
```

Net new tests from TC-3633: **+8** (6 scope tests + 2 timing tests)

---

## Evidence of goal change

The original assertion `captured_configs[0].get(DRIVE_GOAL_KEY) == DRIVE_GOAL_DRAFT`
now asserts `== DRIVE_GOAL_VALIDATE` and passes — confirming the injection was changed.

## Backward compatibility

- `_create_checkpoint(run_dir, step_idx)` without `content_dirs` → falls back to full scope
- `TestCheckpoint` tests in `test_heal_regression_guard.py` pass without modification

---

## Commands run

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal.py -v
# → 75 passed, 0 failed

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/cli/test_heal_regression_guard.py \
  tests/unit/cli/test_heal_convergence_e2e.py \
  tests/unit/cli/test_tc3613_heal_exit_code.py -v
# → 56 passed, 0 failed

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
# → 8080 passed, 13 skipped, 3 xfailed, 0 failed
```
