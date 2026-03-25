# TC-2404 Self-Review

## Acceptance Check Results

- [x] `pytest tests/unit/workers/test_tc_2404_gate17_parallel.py -v` — 9 passed, 0 failed
- [x] `pytest tests/ --tb=no` — 4826 passed, 9 skipped, 0 failed
- [x] `run_gate_17` has `max_parallel_files: int = 4` parameter
- [x] `max_parallel_files_g17` in `run_config.schema.json`

## Task-Specific Review Checklist

- [x] `run_gate_17` signature is backward-compatible: `max_parallel_files=4` default
- [x] `system_text` loaded once before the thread pool (no N-repeated loads)
- [x] `gate_failed` accumulation is thread-safe (list of bools, then `any()` after)
- [x] `llm_client is None` early-return path unchanged (no thread pool created; verified by test)
- [x] `max_parallel_files=1` produces sequential path identical to old behavior
- [x] All existing W9 Gate 17 tests pass unchanged (37 gate tests)
- [x] `max_parallel_files_g17` in `run_config.schema.json`

## 12-Dimension Self-Review

1. **Correctness**: Sequential and parallel paths produce identical issue counts; verified by test.
2. **Backward compatibility**: `max_parallel_files=4` default; existing callers passing 2 positional args unchanged.
3. **Thread safety**: `_check_one_page` reads files and makes LLM calls only — no shared mutable state. Error flags collected in a list (list.append is GIL-safe in CPython).
4. **Exception handling**: Per-file `fut.result()` wrapped in `except Exception`; logs warning, continues. No gate crash.
5. **Test coverage**: 9 tests covering all key behaviors including None client, sequential=parallel equivalence, exception resilience, error code accumulation.
6. **Spec alignment**: TC-2404 taskcard accurately documents implementation. No spec doc update needed per TC (Gate 17 detection behavior unchanged).
7. **Schema alignment**: `run_config.schema.json` has `max_parallel_files_g17` with correct type/min/max/default.
8. **No new module-level imports**: `ThreadPoolExecutor`, `as_completed` imported lazily inside else branch (same pattern as existing gate_17_formatting_quality.py structure).
9. **Governance**: Taskcard and schema updated before code; TC-2404_w9_gate_17_per_file_llm_parallel.md spec_ref matches HEAD SHA.
10. **No behavioral change**: Gate pass/fail criteria unchanged; `gate_failed = any(error_flags)` equivalent to `gate_failed |= has_errors`.
11. **Determinism**: `PYTHONHASHSEED=0` used for full suite; issue list order may vary by thread scheduling but gate pass/fail is deterministic.
12. **Pilot impact**: Gate 17 wall time estimated 4x improvement (600s → 150s max on 20-file run with 4 workers).
