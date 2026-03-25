# SR-06 Evidence — O(n²) → O(n) Uniqueness Guard

**Session**: valiant-purring-pancake (R2 healing)
**Date**: 2026-02-28
**Gap linkage**: GAP-14 (O(n²) uniqueness guard)

## Change

**`src/launch/workers/w4_ia_planner/worker.py`** (~lines 5804-5809):

Before (O(n²)):
```python
# TC-3300/SR-01: Hard uniqueness guard — belt-and-suspenders safety net
_all_uids = [p.get("page_uid") for p in all_pages if p.get("page_uid")]
if len(_all_uids) != len(set(_all_uids)):
    _dupes = sorted({u for u in _all_uids if _all_uids.count(u) > 1})
```

After (O(n) via Counter — already imported):
```python
# TC-3300/SR-01+SR-06: Hard uniqueness guard — O(n) via Counter (GAP-14)
_all_uids = [p.get("page_uid") for p in all_pages if p.get("page_uid")]
if len(_all_uids) != len(set(_all_uids)):
    _uid_counts = Counter(_all_uids)
    _dupes = sorted(u for u, c in _uid_counts.items() if c > 1)
```

`Counter` was already imported (`from collections import Counter`). No new imports needed.

## Commands

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py -v
# 59 passed (unchanged — no new tests for this SR, covered by TestUniquenessGuard)

.venv/Scripts/python.exe -m pytest tests/ --tb=no -q
# 7630 passed, 13 skipped, 0 failed
```

## Result

- O(n²) → O(n) fix applied in 1 line change
- Error message format preserved: "page_uid uniqueness violated: {dupes}"
- All 59 page_uid tests pass; 7630 full suite pass, 0 failures
