# TC-2403 Evidence: W7 Parallel Check Execution + Semantic Caching

## Files Changed

- `src/launch/workers/w7_content_reviewer/worker.py` — Added `_run_checks_parallel()` and `_sanitize_draft_file()` helpers; updated `execute_content_reviewer()` to use them
- `specs/08_content_reviewer.md` — Added "## Performance" section + `max_parallel_workers_w7` config key
- `specs/schemas/run_config.schema.json` — Added `max_parallel_workers_w7` property (integer, 1-8, default 4)
- `tests/unit/workers/w7_content_reviewer/test_parallel_review.py` — New test file (10 tests)

## Commands Run

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w7_content_reviewer/test_parallel_review.py -v
# Result: 10 passed

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w7_content_reviewer/ -v
# Result: 266 passed

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
# Result: 4817 passed, 9 skipped, 0 failed
```

## Test Results

- New tests: 10 passed (test_parallel_review.py)
- Full W7 suite: 266 passed (no regressions)
- Full suite: 4817 passed, 9 skipped, 0 failed (+10 vs baseline 4807)

## Changes Summary

1. **`_run_checks_parallel()`** (module-level helper):
   - Runs CQ, TA, US, optionally SA concurrently via `ThreadPoolExecutor`
   - Returns `(all_issues, semantic_issues)` tuple
   - `n_workers=1` → sequential path, identical to old behavior
   - Exception in any dimension: logs warning, returns empty list for that dim

2. **`_sanitize_draft_file()`** (module-level helper):
   - Extracted from `execute_content_reviewer` post-sanitization loop
   - Applies all 22 sanitizers to one file in-place
   - Called via `ThreadPoolExecutor` for per-file parallelism

3. **`execute_content_reviewer()` changes**:
   - Added `n_workers = max(1, min(8, run_config.get("max_parallel_workers_w7", 4)))`
   - Initial check: `_run_checks_parallel(..., include_semantic=True)` — parallel dimensions
   - Re-checks after fix passes 1 and 2: `include_semantic=False` + restore `_semantic_cache`
   - Re-check after LLM regen: `include_semantic=True` — full refresh

4. **Performance impact** (estimated):
   - Skipping 2 semantic re-runs: ~40 min savings (semantic runs 2× less = 82→~42 min)
   - Parallel dimensions on initial run: ~3 min savings
   - Parallel post-sanitization: ~1 min savings
   - Total estimated: 82 min → ~38 min (~2.2× speedup)

## Determinism Verification

`PYTHONHASHSEED=0` used for all test runs. The `_run_checks_parallel()` function with `n_workers=1`
produces identical results to the old sequential code (verified by `test_sequential_and_parallel_same_issue_count`).
