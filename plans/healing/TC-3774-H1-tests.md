# TC-3774-H1: Unit Tests for --stop-after Feature

## Context

TC-3774 added `--stop-after` to the CLI, `stop_after` to `build_pipeline` and `execute_run`, and a `RunResult` return type. Zero new tests were written. A codebase with 665 tests should not accept a feature with no coverage.

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-01 | No tests for stop_after in graph_builder, run_loop, or CLI | TC-3774-H1 |

## Taskcard: TC-3774-H1

- **Status:** Done
- **Gap linkage:** G-01
- **Role:** Senior engineer. Drop-in, production-ready.

### Scope

- **Fix:** Add unit tests covering `stop_after` in `build_pipeline`, `RunResult` dataclass, CLI validation, and `_print_worker_summary`.
- **Allowed paths:**
  - `tests/unit/test_pipeline_e2e.py` (extend existing)
  - `tests/unit/test_cli.py` (new or extend)
- **Forbidden:** any other file/path

### Acceptance Checks

- **CLI:**
  - `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_pipeline_e2e.py -v -k stop_after` passes
  - `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_cli.py -v` passes (if file created)
- **Tests:**
  - `build_pipeline(stop_after="understand")` produces a compiled graph with only intake+understand nodes
  - `build_pipeline(stop_after="intake")` produces a 1-node graph
  - `build_pipeline(stop_after="nonexistent")` raises `ValueError` with "not a valid worker"
  - `build_pipeline(stop_after=None)` produces full 5-node graph (regression)
  - `RunResult` round-trips correctly: `report=None`, `worker_outputs` populated, `stopped_after` set
  - `_print_worker_summary("intake", {...})` produces expected output (capture typer.echo)
  - `_print_worker_summary("understand", {...})` produces expected output
  - CLI rejects invalid `--stop-after` value (typer exit code 1)
- **Config respected end-to-end:** `pipeline.yaml` worker list drives valid stop_after values
- **No mock data in production paths:** Tests use `MockWorker` from existing test infrastructure

### Deliverables

- New `TestStopAfter` class in `tests/unit/test_pipeline_e2e.py` with 4+ test methods
- New `TestWorkerSummary` test class (in `test_pipeline_e2e.py` or `test_cli.py`) with 2+ test methods
- All tests self-contained (no network, no LLM)

### Hard Rules

- Keep public signatures unchanged
- No network in offline tests
- Deterministic (PYTHONHASHSEED=0)
- No new deps
- Tests use existing `MockWorker` and `_DictProxy` from `test_pipeline_e2e.py`

### Review Dimensions (5/5 targets)

| Dimension | What 5/5 means |
|-----------|----------------|
| Thoroughness | Happy path + error path + regression for each changed function |
| Testability | Each test is isolated, fast (<1s), deterministic |
| Correctness | Tests assert on real model field names verified from source |
| Robustness | Tests cover None values, empty dicts, missing keys |
| Minimality | No test duplication; reuse existing fixtures |

### Runbook

```
1. Read tests/unit/test_pipeline_e2e.py (current state)
2. Add TestStopAfter class with methods:
   - test_stop_after_understand_builds_two_node_graph
   - test_stop_after_intake_builds_one_node_graph
   - test_stop_after_invalid_raises
   - test_stop_after_none_builds_full_graph
3. Add TestWorkerSummary class (or in test_cli.py):
   - test_intake_summary_output
   - test_understand_summary_output
4. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
5. Verify 665+N passed, 0 failed
```
