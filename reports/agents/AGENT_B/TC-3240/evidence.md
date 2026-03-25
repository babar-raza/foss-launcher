# TC-3240 Evidence — W10 Fixer Relative Path Resolution (Phase 2)

| Field | Value |
|-------|-------|
| Taskcard | TC-3240 |
| Session | zany-petting-parrot (phase 2) |
| Date | 2026-02-27 |

---

## Problem (Phase 2 — run_dir-prefixed relative paths)

Phase 1 fixed simple relative paths (`work/site/content/page.md`), but a
second class of path exists in validation_report.json: paths that are
relative yet already include the run_dir tail as a prefix, e.g.
`runs/test_run/work/site/content/page.md`.

Naive `run_dir / rel_path` produces a doubled prefix:
`.../runs/test_run/runs/test_run/work/site/content/page.md` — file not found.

## Root Cause

`normalize_report()` (TC-935) sometimes emits paths relative to a parent
of run_dir rather than strictly relative to run_dir itself. When the
relative path already contains the trailing components of run_dir, the
Phase 1 join logic duplicates those components.

## Fix

Added `_strip_rundir_overlap(rel, run_dir)` helper before the existing
`_normalize_issue_paths()` in `w10_fixer/worker.py`:

1. Computes the longest overlap: suffix of `run_dir.parts` == prefix of
   `rel.parts`.
2. Strips that overlap from the relative path before joining with run_dir.
3. Falls through to original path when no overlap exists (no-op for simple
   relative paths — backward compatible).

`_normalize_issue_paths()` now calls `_strip_rundir_overlap()` for both
`location.path` and `files[]` entries.

**Production code**: +15 lines (1 new helper + 2 modified lines in existing function)

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w10_fixer/worker.py` | Added `_strip_rundir_overlap()`, updated `_normalize_issue_paths()` to call it |
| `tests/unit/workers/test_w10_path_normalization.py` | +7 new tests (3 in TestNormalizeIssuePaths, 4 in TestStripRundirOverlap) |

## New Tests

### TestNormalizeIssuePaths (additions)
- `test_rundir_prefixed_relative_path_no_duplication` — location.path with run_dir tail prefix
- `test_rundir_prefixed_files_no_duplication` — files[] entries with run_dir tail prefix
- `test_rundir_prefixed_idempotent` — calling twice on prefixed path is safe

### TestStripRundirOverlap (new class)
- `test_no_overlap` — no common suffix/prefix, path returned unchanged
- `test_full_tail_overlap` — full run_dir tail stripped
- `test_partial_tail_overlap` — single-component tail match stripped
- `test_deeper_run_dir` — deeper hierarchy with multi-component overlap

## Test Results

```
tests/unit/workers/test_w10_path_normalization.py: 22 passed (15 original + 7 new)
Full suite: 7522 passed, 13 skipped, 0 failed
```

No regressions.
