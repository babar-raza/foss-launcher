# TC-3550 Evidence — W10 KB Howto H1 Goal → H2 Rename

## Summary

Fixed `fix_kb_howto_structure()` in `src/launch/workers/w10_fixer/worker.py`
to rename H1-level Goal headings (`# My Product Goal`) to the correct H2/H3
level before the idempotency check fires.

## Root Cause

The LLM sometimes writes `# Aspose.PRODUCT for Python Goal` (H1) instead of
`## Goal` (H2). The gate `gate_kb_howto_structure` uses `^#{2,3}` regex, so
H1 is invisible — it reports "Goal missing". When W10 tries to fix this, it
injects a second `## Goal` heading *after* the existing H1, creating duplicates.

## Changes Made

### `src/launch/workers/w10_fixer/worker.py`
- Inside `_inject()` nested function in `fix_kb_howto_structure()`, added a
  TC-3550 block BEFORE the idempotency check:
  - Regex: `^#\s+.*\bGoal\b.*$` (H1 only, multi-line, case-insensitive)
  - On match: detect heading level (## or ###), rewrite to `{prefix} Goal`,
    write file, return `True` immediately
  - Only fires when `missing_heading == "goal"` (guard prevents false positives)

### `tests/unit/workers/test_w10_kb_howto_fix.py`
- Added `TestH1GoalRename` class (5 tests):
  - `test_h1_goal_renamed_to_h2`
  - `test_h1_goal_rename_idempotent`
  - `test_h1_goal_only_fires_for_goal_issue`
  - `test_h1_goal_long_product_name`
  - `test_h1_goal_applied_to_work_site_copy`

## Test Results

```
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_kb_howto_fix.py::TestH1GoalRename -v
5 passed in 0.12s
```

Full suite: **7734 passed, 13 skipped, 3 xfailed, 0 failed** (was 7713).

## Idempotency

On the second run:
- H1 Goal is now `## Goal` → `_h1_goal_re.search()` does NOT match
- Idempotency check `^#{2,3}\s+.*\bgoal\b` DOES match → returns `False`
- No duplicate heading created ✓
