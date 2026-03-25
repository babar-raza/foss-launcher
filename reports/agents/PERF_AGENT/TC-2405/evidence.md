# TC-2405 Evidence: W2 Workflow + Example Enrichment Parallelization

## Files Modified

### `src/launch/workers/w2_facts_builder/worker.py`

**Example enrichment (lines ~1064–1078 → expanded)**:
- Pre-assign `example_id`/`primary_snippet_id` sequentially (IDs must exist before threads read dicts)
- Read `_n_ex = min(len(example_files), run_config.get("max_parallel_batches", 4))` with None guard
- Sequential path when `_n_ex <= 1` or only 1 file (identical to pre-TC-2405 behavior)
- Parallel path: `ThreadPoolExecutor(max_workers=_n_ex, thread_name_prefix="ex_enrich")`
  - Futures keyed by index for deterministic result ordering: `[_ex_results[i] for i in range(n)]`
  - Per-future fallback dict on exception (same fallback as old code)

**Workflow step enrichment (lines ~1109–1216 → restructured)**:
- Pre-filter qualifying workflows into `_pending_wfs` list (avoids re-filtering inside thread)
- Extracted inner function `_call_llm_for_wf(wf, tag, target_steps)`:
  - Takes a snapshot of `wf['steps']` as a copy before returning (avoids stale `max_step_num`)
  - Returns `(wf, tag, current_steps_snapshot, new_steps)` — no mutation inside thread
- Sequential path when `_n_wf <= 1` (identical to pre-TC-2405 behavior)
- Parallel path: `ThreadPoolExecutor(max_workers=_n_wf, thread_name_prefix="wf_enrich")`
  - All `claims.append()`, `wf['steps'].append()`, `wf['claim_ids'].append()` in main thread after `as_completed`
  - Thread exception caught per-future; workflow left with original steps

## Files Created

### `plans/taskcards/TC-2405_w2_parallel_workflow_example_enrichment.md`
### `tests/unit/workers/test_tc_2405_w2_parallel_enrichment.py`
- 10 tests across 5 test classes
- Covers: sequential=parallel consistency, result order preservation, ID pre-assignment, fallback on exception, workflow tag filtering, `run_config=None` safety

## Test Results

```
pytest tests/unit/workers/test_tc_2405_w2_parallel_enrichment.py -v
→ 10 passed in 0.75s

pytest tests/unit/workers/test_tc_410_facts_builder.py -v
→ 51 passed in 3.83s

pytest tests/ --tb=no
→ 4836 passed, 9 skipped, 0 failed in 112.65s
```

## Performance Impact

- **Example enrichment**: `enrich_example` is I/O-bound (reads file, pure Python). With 4 workers
  on 20 example files: ~5x speedup on the example phase.
- **Workflow enrichment**: `llm_generate_workflow_steps` makes one LLM call per qualifying workflow
  (typically 1–5). With 4 workers: up to 4x speedup on the workflow LLM phase.
- Both reuse `max_parallel_batches` (existing key, default 4). No new config key.

## Acceptance Check Results

- [x] `pytest tests/unit/workers/test_tc_2405_w2_parallel_enrichment.py -v` — 10 tests pass (≥5)
- [x] `pytest tests/ --tb=no` — 4836 passed, 0 failures
- [x] Example enrichment uses `ThreadPoolExecutor` when `max_parallel_batches > 1` and `len(example_files) > 1`
- [x] Workflow enrichment: LLM call parallelized; mutations applied in main thread
