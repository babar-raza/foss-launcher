# TC-3520 Evidence: W8 Patch Engine Line Range OOB Resilience

## Task Summary

TC-3520 adds two defenses to the W8 LinkerAndPatcher worker against "Line range out of bounds" failures:

1. `_patch_type_priority()` function + sort call in the main apply loop — ensures create_file patches run before update patches, and append patches run before update_by_anchor patches that may shrink the file
2. Clamp logic in `_apply_update_file_range_patch()` for `append_*` patches — if `end_line > len(lines)`, append at EOF instead of raising `LinkerPatchConflictError`

## Files Changed

### `src/launch/workers/w8_linker_and_patcher/worker.py`

Three changes:

**Change 1: New `_patch_type_priority()` function** (added at line 869, before `apply_patch`):
- 36-line module-level function
- Returns int priority: 0=create_file, 1=update_frontmatter_keys, 2=append_* range, 3=update_by_anchor, 4=update_range_*, 5=delete_file, 99=unknown
- Uses `patch.get("type", "")` and `patch.get("patch_id", "")` — safe for missing keys

**Change 2: Sort in main apply loop** (before `for patch in patches:` at ~line 1456):
```python
# TC-3520: Sort patches by type priority to prevent line-range OOB errors.
# create_file → update_frontmatter → append_ → update_by_anchor → update_range → delete
patches = sorted(patches, key=_patch_type_priority)
```

**Change 3: Clamp logic in `_apply_update_file_range_patch()`** (inserted before the existing strict OOB check):
```python
# TC-3520: Clamp append_ patches that exceed current file length.
patch_id = patch.get("patch_id", "")
if patch_id.startswith("append_") and end_line > len(lines):
    logger.debug("[W8] Clamping append patch %s: ...", patch_id, end_line, len(lines))
    new_lines = lines + [new_content + "\n"]
    with open(target_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return {"status": "applied", "reason": f"Append patch clamped to EOF (was line {patch['end_line']})"}
```

### `tests/unit/workers/test_w8_patch_ordering_and_ranges.py` (NEW)

19 new unit tests in 4 classes:
- `TestPatchTypePriority` (11 tests): each type returns correct int; sorting produces correct order; empty patch returns 99; case sensitivity; prefix exactness
- `TestAppendClamp` (5 tests): clamp when OOB; non-append still raises; shrink-then-append; preserves existing content; in-bounds uses normal path
- `TestPatchOrdering` (3 tests): subset sorting; full 6-type ordering; stability guarantee

## Commands Run

```bash
# New tests only
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w8_patch_ordering_and_ranges.py -v
# Result: 19 passed, 1 warning in 1.73s

# Full suite
.venv/Scripts/python.exe -m pytest tests/ -q
# Result: 7713 passed, 13 skipped, 3 xfailed, 47 warnings in 189.58s

# Taskcard validation
.venv/Scripts/python.exe tools/validate_taskcards.py
# Result: [OK] plans\taskcards\TC-3520_w8_patch_range_resilience.md
```

## Test Results

### New tests (19 passed, 0 failed)

```
tests/unit/workers/test_w8_patch_ordering_and_ranges.py ................ [100%]
19 passed, 1 warning in 1.73s
```

### Full suite

```
7713 passed, 13 skipped, 3 xfailed, 47 warnings in 189.58s (0:03:09)
```

Baseline (MEMORY.md): 7642 passed, 13 skipped, 3 xfailed, 0 failed. The count increase (+71) includes TC-3520's 19 new tests plus untracked tests from other in-progress taskcards already present in the working tree.

**No regressions introduced by TC-3520.**

## Determinism Verification

- `sorted()` with integer key is deterministic — same input always produces same output
- `_patch_type_priority` is a pure function (no side effects, no state)
- Python's `sorted()` is guaranteed stable (PEP 3106) — equal-priority patches retain their original relative order
- Clamp path writes `lines + [new_content + "\n"]` — no non-deterministic content

## Regression Guards

- `test_non_append_patch_still_raises_oob`: verifies non-append `update_file_range` patches still raise `LinkerPatchConflictError` for OOB (strict behavior preserved)
- `test_append_patch_not_oob_uses_normal_path`: verifies in-bounds append patches go through the normal replacement path

## Acceptance Checks

- [x] All acceptance criteria in this taskcard are met
- [x] 19 new tests added and passing
- [x] Full suite: 7713 passed, 0 failed
- [x] Determinism: `sorted()` stable; priorities are pure integer mappings
- [x] No schema changes (not applicable)
- [x] Evidence file complete
- [x] Self-review 12D written
