# Evidence: BLKR-04 — Fix TC-2362 Parallel Mode Batch Event Emission

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Branch:** `healing/blkr-01-03-04-rd06`
**Status:** DONE

---

## Summary of Changes

Fixed TC-2362 parallel page writing to emit `EVENT_ARTIFACT_WRITTEN` events in real-time
(as each page's future completes) rather than in a batch after all pages finish.

---

## Root Cause

`worker.py` lines 2238–2253: The result collection loop was placed **outside** the
`with ThreadPoolExecutor()` block, meaning it only ran after all futures had completed
(executor shutdown). This caused all N page events to be emitted in a burst at the end.

## Fix

Moved the `as_completed(futures)` loop **inside** the `with ThreadPoolExecutor()` block.
Each page's event is now emitted as soon as its future resolves, not after all pages complete.

### Before (batch)
```python
with ThreadPoolExecutor(max_workers=max_parallel) as pool:
    for page in to_generate:
        fut = pool.submit(_generate_single_page, ...)
        futures[fut] = page
# Loop runs AFTER pool shutdown (all pages done)
for fut in futures:
    entry = fut.result()
    emit_event(...)
```

### After (real-time)
```python
with ThreadPoolExecutor(max_workers=max_parallel) as pool:
    for page in to_generate:
        fut = pool.submit(_generate_single_page, ...)
        futures[fut] = page
    # Loop runs INSIDE pool context (emits as pages complete)
    for fut in as_completed(futures):
        entry = fut.result()
        emit_event(...)
```

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/worker.py` | Moved result collection + emit_event inside `with ThreadPoolExecutor()` block using `as_completed()` |
| `tests/unit/workers/test_tc_440_section_writer.py` | Added 2 new tests: `test_parallel_emits_per_page_events` + `test_sequential_emits_per_page_events` |

---

## Test Results

```
TestTC2362ParallelPageWriting: 5/5 tests pass (3 pre-existing + 2 new BLKR-04 tests)
Full suite: 4538 passed, 9 skipped, 0 failed
```

New tests:
- `test_parallel_emits_per_page_events`: Asserts 3 per-page draft events for 3 parallel pages
- `test_sequential_emits_per_page_events`: Regression — 1 per-page draft event for 1 sequential page

---

## Observability Impact

TC-2362 self-review Observability: **4/5 → 5/5**

Events now emitted as each page completes rather than in a batch. Observers (e.g., UI progress
bars, log tailing) will see page-level progress in real-time during parallel runs.

---

## Acceptance Criteria

| Check | Result |
|-------|--------|
| `test_parallel_emits_per_page_events` passes | ✅ PASS |
| `test_sequential_emits_per_page_events` passes (regression) | ✅ PASS |
| All 3 pre-existing TC-2362 tests pass | ✅ PASS |
| Full suite passes | ✅ 4538/4538 |
| Sequential mode (`max_parallel_pages=1`) behavior unchanged | ✅ |
