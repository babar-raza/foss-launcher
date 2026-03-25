# TC-3570 Evidence — Heal Checkpoint MAX_PATH Fix

## Summary

Implemented `_win_path()` helper in `src/launch/cli/heal.py` to bypass the
Windows 260-char MAX_PATH limit in checkpoint create/restore operations.

## Changes Made

### `src/launch/cli/heal.py`
- Added `import sys` to imports
- Added `_win_path(p: Path) -> Path` helper (idempotent, no-op on non-Windows)
- Applied `_win_path()` to all `shutil.copytree()`, `shutil.rmtree()`, and
  `Path.mkdir()` calls in `_create_checkpoint()` and `_restore_checkpoint()`
- Added STOP-THE-LINE guard: if `_create_checkpoint()` returns None, the current
  heal step is skipped via `continue` (unsafe to proceed without rollback)

### `tests/unit/cli/test_heal.py`
- Added `_win_path` to import block
- Added `TestCheckpointMaxPath` class (5 tests):
  - `test_win_path_adds_prefix_on_win32`
  - `test_win_path_noop_on_non_windows`
  - `test_win_path_idempotent`
  - `test_win_path_unc_prefix` (Windows-only, skipped on Linux)
  - `test_win_path_already_prefixed_not_double_prefixed`

## Test Results

```
.venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal.py::TestCheckpointMaxPath -v
5 passed in 0.35s
```

Full suite: **7734 passed, 13 skipped, 3 xfailed, 0 failed** (was 7713).

## Root Cause Fixed

`_heal_checkpoints/step_N/work/site/content/blog.aspose.org/cells/python/...`
exceeds Windows 260-char MAX_PATH → `shutil.copytree()` raises `[WinError 206]`
→ checkpoint returns None → regression guard fires but cannot restore.

Fix: `_win_path()` prefixes all checkpoint paths with `\\?\` on Windows,
enabling long path support (up to 32,767 chars) via the Win32 extended-length
path API.
