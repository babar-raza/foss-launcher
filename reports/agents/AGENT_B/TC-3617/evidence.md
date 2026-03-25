# TC-3617 Evidence — Healing Cost Reduction

## Summary

Three optimizations implemented to reduce healing cost/time:
- **B1**: Batch 3 LLM semantic checks into 1 call per file
- **B2**: Content-hash-keyed semantic result cache
- **B3**: W10 sibling-issue batch fix for formatting and howto

## 2026-03-02 Amendment

- B3 now uses one file-wide LLM repair pass per same-file family batch when
  `llm_client` is available, with deterministic single-file fallback when it is
  unavailable or the response is invalid.
- The W10 batch-fix test suite now includes mock-based call-count coverage for
  the LLM path:
  - `test_formatting_uses_one_llm_call_for_same_file_batch`
  - `test_howto_uses_one_llm_call_for_same_file_batch`
- The semantic cache key now hashes normalized excerpt text only; metadata-only
  changes inside evidence excerpt objects do not invalidate the cache.
- Verified on 2026-03-02 with:
  - `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_batch_fix.py tests/unit/workers/test_w10_kb_howto_fix.py tests/unit/workers/test_w10_scaffold_fix.py -x`
  - Result: `87 passed, 1 warning`
- The older note claiming W7 does not pass `run_dir` is stale and superseded:
  current W7 wiring already passes `run_dir` into semantic cache checks.

## Files Changed

| File | Change |
|------|--------|
| `specs/50_healing_cost_reduction.md` | NEW — BINDING spec (3 contracts) |
| `plans/taskcards/TC-3617_healing_cost_reduction.md` | NEW — taskcard |
| `plans/taskcards/INDEX.md` | Updated — TC-3617 registered |
| `src/launch/workers/w7_content_reviewer/checks/semantic_accuracy.py` | B1: `check_semantic_bundle()`, `_run_offline_checks()`. B2: `_cache_key()`, `_load_cache()`, `_save_cache()`. Modified `check_all()` (+run_dir param, bundle routing, cache check/store) |
| `src/launch/workers/w10_fixer/worker.py` | B3: `fix_formatting_defect()` collects all sibling FQ codes via validation_report. `fix_kb_howto_structure()` collects all missing headings via validation_report. Both use graceful degradation. |
| `tests/unit/workers/w7_content_reviewer/test_semantic_bundle.py` | NEW — 6 tests |
| `tests/unit/workers/w7_content_reviewer/test_semantic_checks.py` | Updated — 3 new cache tests (`TestSemanticCache`) |
| `tests/unit/workers/test_w10_batch_fix.py` | NEW — 5 tests |

## Test Results

```
$ .venv/Scripts/python.exe -m pytest tests/ -x --tb=no -p no:warnings
7947 passed, 13 skipped, 3 xfailed in 170.06s
```

### New tests (14 total)

**B1 Bundle tests (6):**
- `test_bundle_makes_one_llm_call` — 1 file → 1 LLM call (not 3)
- `test_bundle_returns_all_three_check_types` — Issues from all 3 checks returned
- `test_bundle_fallback_on_timeout` — Timeout → offline heuristics
- `test_bundle_fallback_on_parse_error` — Bad JSON → offline heuristics
- `test_bundle_n_files_n_calls` — 3 files → 3 calls (not 9)
- `test_bundle_skips_licensing_for_non_foss` — Non-FOSS → "NOT APPLICABLE" in prompt

**B2 Cache tests (3):**
- `test_cache_hit_skips_llm` — Prepopulated cache → 0 LLM calls
- `test_cache_miss_stores_result` — First run stores, second run hits cache
- `test_cache_invalidated_by_content_change` — Changed content → cache miss

**B3 Batch fix tests (5):**
- `test_formatting_fixes_all_sibling_fq_codes` — FQ-4 + FQ-1 on same file → both fixed
- `test_formatting_single_issue_when_report_missing` — Graceful degradation
- `test_batch_fix_ignores_other_files` — Cross-file issues not batched
- `test_howto_injects_all_missing_headings` — 3 missing headings → all injected
- `test_howto_single_heading_when_report_missing` — Graceful degradation

## Call-Count Evidence (Mock-Based)

B1: `test_bundle_n_files_n_calls` proves N files → N calls (not 3N):
```python
mock_llm.chat_completion.call_count == 3  # for 3 files (was 9 before)
```

B2: `test_cache_miss_stores_result` proves 0 calls on second run:
```python
# First run: call_count == 1
# Second run: call_count == 0 (cache hit)
```

## Determinism Verification

- Cache key: SHA-256 of `(rel_path:content_hash:evidence_hash)` — deterministic
- Cache write: `tempfile + os.replace()` — atomic
- B3 heading injection order: canonical `_HEADING_ORDER` list — deterministic
- B3 error code collection: `set` → all `any()` checks use sorted patterns

## Integration Notes

- B1 (bundle) is active immediately: `check_all()` with `llm_client` present routes through `check_semantic_bundle()` instead of 3 individual LLM calls
- B2 (cache) requires caller to pass `run_dir` to `check_all()`. W7 worker.py doesn't pass it yet (outside TC-3617 allowed_paths). A follow-up can wire it in.
- B3 (batch fix) is active immediately: both fix functions load validation_report on every invocation
- All individual check functions remain callable independently (public API unchanged)
