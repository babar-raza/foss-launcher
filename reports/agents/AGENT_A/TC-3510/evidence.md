# TC-3510 Evidence Report: Heal W5 Cascade Hardening

## Summary

TC-3510 implements three features in `src/launch/cli/heal.py`:

1. **Pre-step checkpoint snapshots** — `_create_checkpoint()` and `_restore_checkpoint()` snapshot `artifacts/`, `work/site/content/`, and `drafts/` before each heal step.
2. **Regression guard with rollback** — After each step, if `new_failed_count > failed_count`, the checkpoint is restored, a `HEAL_STEP_REGRESSED` event is emitted, and the loop continues to the next iteration (rather than stopping).
3. **W5 deprioritization** — `_deprioritize_w5()` moves W5 recommendations to the end of the list when ≤4 gates are failing, to prefer lower-risk workers (W10/W8/W6) first.

## Files Modified

### `src/launch/cli/heal.py`

- Added `import shutil` (line 18)
- Added `_EVENT_HEAL_STEP_REGRESSED = "HEAL_STEP_REGRESSED"` (line 29)
- Added checkpoint constants `_CHECKPOINT_DIR_NAME`, `_CHECKPOINT_ARTIFACTS`, `_CHECKPOINT_CONTENT_DIRS` (lines 41-43)
- Added `_create_checkpoint(run_dir, step_idx) -> Optional[Path]` (lines 240-269) — copies `artifacts/` + content dirs into `_heal_checkpoints/step_{N}/`
- Added `_restore_checkpoint(run_dir, checkpoint_dir) -> bool` (lines 272-297) — restores artifacts + content dirs from checkpoint
- Added `_deprioritize_w5(recommendations, failed_gate_count) -> List[Dict]` (lines 94-116) — reorders W5 to end when ≤4 gates failing
- Modified `is_stuck()` (lines 191-209) — skip regressed steps (notes.startswith("regressed:")) in stuck detection
- Modified `_was_tried_without_improvement()` (lines 167-188) — skip regressed last step in improvement check
- Modified `run_heal_loop()`:
  - Line 412: `checkpoint: Optional[Path] = None` initialized at loop top
  - Line 418: `recommendations = _deprioritize_w5(recommendations, failed_count)`
  - Line 477: `checkpoint = _create_checkpoint(run_dir, step_idx)` before HEAL_STEP_STARTED
  - Lines 548-575: Regression branch: sets `step.notes = f"regressed: {old} → {new}"`, emits `_EVENT_HEAL_STEP_REGRESSED`, restores checkpoint, reloads report, `continue`

## Files Added

### `tests/unit/cli/test_heal_regression_guard.py`

16 new tests across 3 classes:

- `TestCheckpoint` (6 tests):
  - `test_create_checkpoint_copies_artifacts`
  - `test_create_checkpoint_copies_content_dir`
  - `test_restore_checkpoint_overwrites_artifacts`
  - `test_create_checkpoint_handles_missing_dirs_gracefully`
  - `test_create_checkpoint_creates_step_subdir`
  - `test_restore_checkpoint_copies_drafts_dir`

- `TestW5Deprioritization` (7 tests):
  - `test_w5_moved_to_end_when_few_gates_failing`
  - `test_w5_stays_in_position_when_many_gates_failing`
  - `test_w5_deprioritized_at_boundary_4_gates`
  - `test_no_w5_recommendations_unchanged`
  - `test_empty_recommendations_unchanged`
  - `test_multiple_w5_all_moved_to_end`
  - `test_threshold_at_5_gates_does_not_deprioritize`

- `TestRegressionGuard` (3 tests):
  - `test_regression_detected_and_continues_to_next_candidate`
  - `test_step_notes_regressed_on_regression`
  - `test_checkpoint_restored_after_regression`

## Commands Run

```bash
# New test file only
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_regression_guard.py -v
# → 16 passed, 0 failed

# CLI tests (includes existing heal tests)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/ -v -q
# → 137 passed, 0 failed

# Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
# → 7713 passed, 13 skipped, 3 xfailed, 0 failed

# Taskcard validation
.venv/Scripts/python.exe tools/validate_taskcards.py
# → [OK] plans\taskcards\TC-3510_heal_w5_cascade_hardening.md
```

## Test Results

| Suite | Passed | Failed | Skipped | xfailed |
|-------|--------|--------|---------|---------|
| TC-3510 tests only | 16 | 0 | 0 | 0 |
| CLI tests | 137 | 0 | 0 | 0 |
| Full suite | 7713 | 0 | 13 | 3 |

Baseline (pre-TC-3510): 7642 passed, 13 skipped, 3 xfailed, 0 failed
TC-3510 adds: +16 new tests (net: +71 vs baseline due to other in-progress TCs also counting)

## Deterministic Verification

- `_create_checkpoint()` uses `shutil.copytree()` — deterministic filesystem copy
- `_restore_checkpoint()` uses `shutil.rmtree()` then `shutil.copytree()` — deterministic overwrite
- `_deprioritize_w5()` uses list comprehension with stable Python list ordering (partition, not sort)
- No timestamps, random IDs, or nondeterministic ordering introduced

## No Gate Weakening

- No gate files modified
- No validation logic removed or weakened
- All 41 gates unchanged
