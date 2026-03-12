# SS-03: Checkpoint–Snapshot Integration Verification

- **Status:** Done
- **Gap linkage:** G-SS-03 (checkpoint.py copies snapshot.json — previously empty, now populated; verify integration)
- **Role:** Senior engineer. Drop-in, production-ready.

## Context

`checkpoint.py:create_checkpoint()` reads `snapshot.json` from disk and copies it into `checkpoints/<timestamp>/snapshot.json`. Before the snapshot fix, this always copied `{}`. Now that snapshots are populated, the checkpoint system should capture meaningful pipeline state. However, no integration test verifies:
- Checkpoint captures the snapshot written by `_write_final_snapshot()`
- `load_checkpoint()` returns a snapshot with real `artifacts_index` and `work_items`
- Checkpoint metadata (`events_count`, `completed_workers`) aligns with snapshot content

## Scope

- **Fix:** Add integration tests verifying checkpoint captures populated snapshots.
- **Allowed paths:**
  - `tests/unit/resilience/test_checkpoint.py` (extend)
- **Forbidden:** any other file/path

## Acceptance Checks

- **Tests:**
  - `create_checkpoint()` after `write_snapshot()` produces checkpoint dir with non-empty `snapshot.json`
  - `load_checkpoint()` returns snapshot data matching what was written
  - Checkpoint `snapshot.json` has `run_state`, `artifacts_index` keys (not `{}`)
  - `list_checkpoints()` returns entries sorted by timestamp
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_checkpoint.py -v` passes
- **Config respected end-to-end:** Checkpoint system can restore real pipeline state
- **No mock data in production paths:** Tests use tmp_path with realistic snapshot data

## Deliverables

- 3+ new test methods in `test_checkpoint.py`
- All existing checkpoint tests still pass

## Hard Rules

- Keep public signatures unchanged
- No network in offline tests
- Deterministic (PYTHONHASHSEED=0)
- No new deps
- Use `write_snapshot()` from `snapshot_manager` to create test snapshots (not raw JSON)

## Review Dimensions (5/5 targets)

| Dimension | What 5/5 means |
|-----------|----------------|
| Correctness | Checkpoint content verified field-by-field against written snapshot |
| Integration | Tests exercise write_snapshot → create_checkpoint → load_checkpoint chain |
| Robustness | Tests cover both populated and empty snapshot scenarios |
| Minimality | Only test additions, no source changes |
| Determinism | Tests pass with PYTHONHASHSEED=0 |

## Runbook

```bash
# 1. Read tests/unit/resilience/test_checkpoint.py
# 2. Add tests using write_snapshot() + create_checkpoint() + load_checkpoint()
# 3. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_checkpoint.py -v
# 4. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
