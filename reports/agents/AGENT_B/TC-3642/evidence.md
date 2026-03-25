# TC-3642 Evidence — PhaseSelector .git Hardening

## Test Results

### Targeted tests (26 phase_selector + 18 resume)
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/autopilot/test_phase_selector.py tests/unit/orchestrator/test_resume_from_node.py -v
# 44 passed, 0 failed
```

### Full suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short
# 8174 passed, 13 skipped, 3 xfailed, 0 failed
```

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/launch/autopilot/phase_selector.py` | Added `.git` existence check after `repo_dir.is_dir()` (lines 142-146) | +5 |
| `src/launch/orchestrator/run_loop.py` | Changed W2 entry from `work/repo` to `work/repo/.git` (lines 100, 147) | ~2 |
| `specs/43_resumable_pipeline.md` | W2 row in §Artifact Pre-validation table: added `.git` requirement | ~1 |
| `specs/48_autopilot_phase_selection.md` | §Baseline Algorithm: documented REPO_NOT_CLONED reason | ~3 |
| `tests/unit/autopilot/test_phase_selector.py` | Updated `_setup_w1()` to create `.git` dir; added 2 new tests | ~15 |
| `tests/unit/orchestrator/test_resume_from_node.py` | Updated fixtures for `.git` in W2 required_paths | ~5 |
| `tests/integration/test_drive_e2e.py` | Updated `_make_run_dir()` to create `.git` dir | ~2 |

## New Tests

| Test | Coverage |
|------|----------|
| `test_repo_dir_exists_but_no_git_returns_w1` | Empty `work/repo/` without `.git` returns W1 with REPO_NOT_CLONED |
| `test_repo_dir_with_git_passes_checkpoint` | `work/repo/` with `.git` present proceeds past checkpoint 1 |

## Design Decisions

1. **Check `.git` not just `repo_dir.is_dir()`**: `create_run_skeleton()` always creates
   `work/repo/` as an empty directory. Only a real git clone (or symlink to one) will
   have `.git` inside. This is the simplest, most reliable discriminator.

2. **Return early with REPO_NOT_CLONED**: Follows existing pattern — each checkpoint
   returns immediately with a reason code on failure. No need for fallthrough logic.

3. **RESUME_NODE_MAP uses `work/repo/.git`**: `_validate_resume_artifacts()` treats paths
   without a file extension as directories and calls `.exists()`, which returns True for
   both files and directories. `.git` is a directory, so this works correctly.

4. **Test fixtures updated, not test logic changed**: All `_setup_w1()` helpers now create
   `.git` dir. This ensures existing tests reflect the "valid clone" scenario correctly.
