# Self Review (12-D)

> Agent: agent_b
> Taskcard: TC-3617
> Date: 2026-03-01

## Summary
- What I changed: Added bundled semantic check (B1), content-hash cache (B2), and sibling-issue batch fix (B3) to reduce healing cost
- How to run verification: `.venv/Scripts/python.exe -m pytest tests/ -x --tb=no -p no:warnings`
- Key risks / follow-ups: B2 cache requires W7 worker.py to pass `run_dir` (outside TC-3617 scope); B3 loads validation_report.json on every fix invocation (extra I/O, but file is already in memory cache from execute_fixer)

## 2026-03-02 Amendment
- B3 is now aligned with the originally requested execution path when `llm_client`
  is available: W10 performs one file-wide LLM repair call per same-file family
  batch and writes the validated full-file response atomically.
- The deterministic W10 path remains as the explicit fallback when `llm_client`
  is unavailable or the LLM response is invalid.
- The earlier note that B2 cache was not wired is stale; W7 now passes `run_dir`
  into the semantic check path.
- The semantic cache key now hashes excerpt text only; metadata-only changes in
  evidence excerpt objects no longer invalidate cache entries.
- Targeted W10 regression run on 2026-03-02:
  - `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_batch_fix.py tests/unit/workers/test_w10_kb_howto_fix.py tests/unit/workers/test_w10_scaffold_fix.py -x`
  - Result: `87 passed, 1 warning`
- Full close-out and score recalibration remain part of follow-up verification, not
  this amendment.

## Evidence
- Diff summary: +~300 lines in semantic_accuracy.py, +~25 lines in worker.py, +3 new test files
- Tests run: `pytest tests/ -x` → 7947 passed, 13 skipped, 3 xfailed, 0 failed
- Logs/artifacts written: `reports/agents/agent_b/TC-3617/evidence.md`

## 12 Quality Dimensions (score 1-5)

1) Correctness
Score: 5/5
- Bundle produces identical issue format (`_make_issue()`) as individual checks
- Cache key includes evidence hash, not just content
- B3 graceful degradation proven by tests (report-missing path)
- Offline fallback verified for both timeout and parse error
- 14 new tests all passing

2) Completeness vs spec
Score: 4/5
- All 3 contracts from spec 50 implemented
- B2 cache is functional but not yet wired into W7 production path (needs worker.py change)
- Individual check functions remain public API (spec requirement met)
- FOSS guard preserved in bundle prompt

3) Determinism / reproducibility
Score: 5/5
- Cache key is SHA-256 deterministic
- Cache write is atomic (tempfile + os.replace)
- B3 heading injection uses canonical `_HEADING_ORDER`
- B3 error code collection uses `set` + `any()` — order-independent

4) Robustness / error handling
Score: 5/5
- Bundle: catches any exception, falls back to offline
- Cache: `_load_cache` returns {} on corrupt, `_save_cache` silently fails
- B3 formatting: `try/except` around report load, degrades to single issue
- B3 howto: same pattern, tested with missing report

5) Test quality & coverage
Score: 4/5
- 6 bundle tests cover call count, types, fallback, multi-file, FOSS guard
- 3 cache tests cover hit, miss+store, invalidation
- 5 batch fix tests cover multi-code, single-issue, cross-file, multi-heading, degradation
- Missing: parallel bundle test (ThreadPoolExecutor path), cache thread safety under contention

6) Maintainability
Score: 5/5
- `check_semantic_bundle` is a standalone function, easy to modify/replace
- Cache helpers are 3 small functions with clear contracts
- B3 changes are minimal — just set expansion at top of existing functions
- No new dependencies added

7) Readability / clarity
Score: 5/5
- TC-3617 comments explain each change
- Bundle prompt is well-structured (3 tasks, clear instructions)
- `_run_offline_checks` helper named clearly for its purpose
- B3 uses `error_codes` set (plural) vs `error_code` (singular) — clear naming

8) Performance
Score: 4/5
- B1: 3N LLM calls → N calls (67% reduction per file)
- B2: 0 LLM calls on re-run with unchanged drafts
- B3: N formatting issues per file → 1 heal iteration (saves N-1 W9 runs)
- B3 loads validation_report.json inside fix function (I/O overhead, but small file)
- Bundle timeout bumped to 25s (from 15s) — acceptable for 3x content

9) Security / safety
Score: 5/5
- No new external inputs — cache is per-run, not cross-run
- Atomic cache write prevents partial reads
- No secret data in cache (only issue metadata)
- `output_schema` injection is text-based (no code execution)

10) Observability (logging + telemetry)
Score: 3/5
- B3 formatting fix diff_summary now shows all codes: `sorted(error_codes)`
- B3 howto fix diff_summary shows all headings: `sorted(all_missing)`
- Missing: no explicit logging when bundle fallback triggers (would be useful)
- Missing: no telemetry event for cache hit/miss (could be added)
- Fix plan: Add `logger.info("Bundle fallback triggered for %s", page_slug)` in a follow-up

11) Integration (CLI/MCP parity, run_dir contracts)
Score: 4/5
- B1 integrates seamlessly — `check_all()` routes through bundle when llm_client present
- B2 `run_dir` parameter is backward-compatible (default None)
- B3 loads validation_report via existing `load_json_artifact()` helper
- B2 not yet wired into W7 worker.py (needs separate taskcard for worker.py changes)

12) Minimality (no bloat, no hacks)
Score: 5/5
- No unnecessary abstractions — bundle is a function, cache is 3 helpers
- B3 reuses existing `if` branches — just widens the code set
- No new dependencies, no new config keys
- Existing public API unchanged

## Final verdict
- Ship
- Total: 55/60
- Dimension 10 (Observability) at 3/5: Follow-up should add `logger.info` for bundle fallback and cache hit/miss metrics. Can be done in a separate micro-taskcard.
