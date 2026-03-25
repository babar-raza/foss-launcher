# TC-2404 Evidence: W9 Gate 17 Per-File LLM Parallelization

## Files Modified

### `src/launch/workers/w9_validator/gates/gate_17_formatting_quality.py`
- Added `max_parallel_files: int = 4` parameter to `run_gate_17()` (backward-compatible default)
- Replaced sequential `for md_path in md_files:` loop with branched implementation:
  - `max_parallel_files=1` → sequential path (identical to pre-TC-2404 behavior)
  - `max_parallel_files>1` → `ThreadPoolExecutor(max_workers=_n, thread_name_prefix="gate17_check")`
- Error flags accumulated via `error_flags: List[bool]` list; `gate_failed = any(error_flags)` avoids GIL-unsafe mutation
- `system_text` loaded once before pool (no N-repeated loads)
- Exception per-file caught and logged; gate continues processing remaining files

### `src/launch/workers/w9_validator/worker.py`
- Gate 17 call site updated from `run_gate_17(md_files_g17, gate17_llm_client)` to:
  ```python
  _g17_parallel = max(1, min(8, run_config.get("max_parallel_files_g17", 4)))
  g17_passed, g17_issues = run_gate_17(md_files_g17, gate17_llm_client, max_parallel_files=_g17_parallel)
  ```

### `specs/schemas/run_config.schema.json`
- Added `max_parallel_files_g17` property (integer, minimum 1, maximum 8, default 4)

## Files Created

### `tests/unit/workers/test_tc_2404_gate17_parallel.py`
- 9 tests across 6 test classes
- Covers: backward-compatible signature, llm_client=None early-return, sequential vs parallel
  consistency, thread exception handling, gate_failed accumulation, empty file list

## Test Results

```
pytest tests/unit/workers/test_tc_2404_gate17_parallel.py -v
→ 9 passed in 0.77s

pytest tests/unit/workers/test_tc_570_extended_gates.py -v
→ 37 passed in 1.48s

pytest tests/ --tb=no
→ 4826 passed, 9 skipped, 0 failed in 122.55s
```

## Performance Impact

Gate 17 scans one LLM call per markdown file with a 30-second timeout.
For a typical 20-file run at max_parallel_files=4:
- Sequential: 20 × 30s = 600s max (10 min)
- Parallel (4 workers): 5 batches × 30s = 150s max (2.5 min)
- Estimated 4x speedup on the Gate 17 phase

## Acceptance Check Results

- [x] `run_gate_17` has `max_parallel_files: int = 4` parameter
- [x] `max_parallel_files_g17` in `run_config.schema.json`
- [x] `pytest tests/unit/workers/test_tc_2404_gate17_parallel.py -v` — 9 tests pass (≥5)
- [x] `pytest tests/ --tb=no` — 4826 passed, 0 failures
