# TC-3660 Evidence — Latest Run State

## Test Results

### Targeted tests (22 new)
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/state_store/test_latest_state.py -x -v
# 22 passed, 0 failed
```

### Full suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -p no:warnings
# 8168 passed, 13 skipped, 3 xfailed, 0 failed (+22 net new from 8146 baseline)
```

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/launch/state_store/latest_state.py` | NEW: `write_latest_state()`, `hydrate_latest_state()`, `_create_dir_link()`, `_win_path()` | ~230 lines |
| `src/launch/state_store/__init__.py` | Added exports: `hydrate_latest_state`, `write_latest_state` | +6 lines |
| `src/launch/cli/main.py` | Added: import, Step 4b hydration call, Step 12c write call | +15 lines |
| `src/launch/workers/w1_repo_scout/clone.py` | Added: `_try_reuse_existing_clone()` helper + 3 guard calls (product, site, workflows) | +75 lines |
| `specs/48_autopilot_phase_selection.md` | Added §Latest Run State (layout, meta.json, work_refs.json, hydration/write behavior, W1 guard) | +85 lines |
| `tests/unit/state_store/test_latest_state.py` | NEW: 22 tests across 5 classes | ~370 lines |
| `plans/taskcards/TC-3660_latest_run_state.md` | NEW: governance taskcard | ~150 lines |

## Test Class Breakdown

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestWriteLatestState` | 7 | meta.json fields, work_refs, artifacts copy, drafts copy, atomic replace, missing snapshot |
| `TestHydrateLatestState` | 7 | no snapshot, SHA mismatch, sig mismatch, artifacts, drafts, non-overwriting artifacts, non-overwriting drafts |
| `TestCreateDirLink` | 2 | symlink success, nonexistent target platform behavior |
| `TestTryReuseExistingClone` | 5 | no .git, matching SHA, mismatched SHA, non-SHA ref, git error |
| `TestRoundTrip` | 1 | full write→hydrate cycle |

## Key Design Decisions

1. **Non-overwriting hydration**: Two-layer store artifacts always take precedence over latest state artifacts. `hydrate_latest_state()` only copies files that don't already exist.

2. **Symlink → junction fallback**: `_create_dir_link()` tries `os.symlink()` first, then `mklink /J` on Windows. Both succeed on this development machine; the test uses `pytest.skip()` if neither works.

3. **Atomic write**: `write_latest_state()` writes to `latest_tmp/` then renames to `latest/`. This prevents half-written state on crash.

4. **Clone guard SHA comparison**: `_try_reuse_existing_clone()` only skips clone for full 40-char SHA refs. Branch/tag refs always trigger re-clone for safety.

5. **Resolve symlink chains**: `write_latest_state()` calls `Path.resolve()` on work refs to avoid symlink-to-symlink chains across multiple runs.
