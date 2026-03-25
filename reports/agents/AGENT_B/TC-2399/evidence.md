# TC-2399 Evidence: Implement `launch resume` Command

## Files Modified/Created

| File | Action | Change summary |
|---|---|---|
| `src/launch/orchestrator/graph.py` | Modified | Added `start_node: str = "clone_inputs"` param; `set_entry_point(start_node)` |
| `src/launch/orchestrator/run_loop.py` | Modified | Added `_EVENT_RUN_RESUMED`, `RESUME_NODE_MAP`, `_validate_resume_artifacts()`, `execute_run_from_node()` |
| `src/launch/cli/main.py` | Modified | Added `resume` Typer command |
| `scripts/run_pilot.py` | Modified | Added `--from-worker` argument and `_resume_pilot()` helper |
| `tests/unit/orchestrator/test_resume_from_node.py` | Created | 15 unit tests across 6 test classes |

## Test Results

```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_resume_from_node.py -v
Result:  15 passed in 1.36s ✅

Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/
Result:  4807 passed, 9 skipped, 1 warning in 149.99s ✅
         (previous baseline: 4792 passed — +15 new tests, 0 regressions)
```

## Shared-Library Compliance

- `_EVENT_RUN_RESUMED = "RUN_RESUMED"` defined in `run_loop.py` (NOT in `models/event.py`)
- `src/launch/models/**` not in `allowed_paths` ✅
- `src/launch/io/**` not in `allowed_paths` ✅
- `src/launch/util/**` not in `allowed_paths` ✅

## RESUME_NODE_MAP Coverage

22 entries total: W1–W11 (short aliases) + 11 full node names. Verified by
`test_total_alias_count` (asserts exactly 22).

## Backward Compatibility

- `build_orchestrator_graph()` without arguments → identical behaviour (default `"clone_inputs"`)
- `execute_run()` unchanged
- All 4792 pre-existing tests continue to pass

## Acceptance Checks

- [x] `build_orchestrator_graph("draft_sections").compile()` runs without error (test 5)
- [x] `launch resume --from-worker WBAD` exits code 1 with alias list in output (test 6)
- [x] `launch resume --run-dir <dir_missing_artifact> --from-worker W5` exits 1 with missing path (test 4)
- [x] 15 new tests pass; 0 regressions in full suite (4807 passed)
- [x] `events.ndjson` append-only — `execute_run_from_node()` uses `append_event()` ✅
- [x] Shared-library Gate E: no `src/launch/models/**` writes ✅

---

## Hardening: W2 Prevalidation Strengthening (2026-02-27 — imperative-weaving-noodle)

### Problem
`create_run_skeleton()` always creates `work/repo/` as an empty directory.
W2's prior `required_paths = ["work/repo"]` only checked directory existence → resume into W2 passed
prevalidation even when W1 never ran, then crashed deep in `execute_extraction_phase()` (line 2089)
or `_assemble_product_facts()` (line 857) with opaque `FactsBuilderError`.

### Changes
| File | Change |
|------|--------|
| `src/launch/orchestrator/run_loop.py` | W2 + ingest entries: added `artifacts/repo_inventory.json`, `artifacts/frontmatter_contract.json` |
| `tests/unit/orchestrator/test_resume_from_node.py` | Added `TestW2ResumeArtifactValidation` (3 tests) |

### New Error Message (on empty dir)
```
ValueError: Cannot resume from '...': missing required artifact(s):
  - artifacts/repo_inventory.json
  - artifacts/frontmatter_contract.json
```

### Test Evidence
```
test_resume_from_node.py   18 passed  (15 orig + 3 new) ✅
Full suite:                7163 passed, 13 skipped, 0 failed ✅
```
