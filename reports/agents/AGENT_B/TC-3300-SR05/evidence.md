# SR-05 Evidence — Safety Valve + Uniqueness Guard Tests

**Session**: valiant-purring-pancake (R2 healing)
**Date**: 2026-02-28
**Gap linkage**: GAP-12 (safety valve test), GAP-13 (uniqueness guard test)

## Changes

### Test file additions (`tests/unit/workers/test_w4_page_uid.py`)

**`TestSafetyValve`** (1 test):
- `test_collision_loop_exceeds_100_raises`: Patches `launch.workers.w4_ia_planner.worker.hashlib`
  so all sha256 calls return `"0" * 64`. With 3 pages that all produce the same base uid,
  the 3rd page's collision resolution generates the same suffix on every iteration
  → counter hits 101 → ValueError("collision loop exceeded 100 iterations").

**`TestUniquenessGuard`** (2 tests):
- `test_guard_logic_raises_on_duplicates`: Creates 2 pages, runs `_assign_page_uids()`,
  corrupts one uid to duplicate the other, then runs the Counter-based guard logic inline
  → ValueError raised with "page_uid uniqueness violated".
- `test_guard_logic_passes_on_unique_uids`: Same setup but no corruption → empty dupes list.

## Commands

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py::TestSafetyValve -v
# 1 passed

.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py::TestUniquenessGuard -v
# 2 passed

.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py -v
# 59 passed
```

## Result

- 3 new tests passing (1 safety valve + 2 uniqueness guard)
- All 59 page_uid tests pass
- 7630 passed, 13 skipped, 0 failed (full suite)
