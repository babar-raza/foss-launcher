# Evidence — TC-3100: W2 Quality Uplift

## Test Results

### New tests (48 passing)
```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_quality_uplift.py -v
Result: 48 passed, 0 failed
```

### Existing W2 tests (111 passing, unchanged)
```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py -x -q
Result: 111 passed, 0 failed
```

### Full worker test suite (5275 passing)
```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ tests/unit/autopilot/ tests/unit/provenance/ tests/unit/state_store/ tests/unit/cli/ --tb=no
Result: 5275 passed, 1 skipped, 3 xfailed, 9 xpassed
```

### Full test suite (7124 passing)
```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
Result: 7124 passed, 2 failed (pre-existing flaky orchestrator tests), 13 skipped
```
The 2 failures are in `tests/unit/orchestrator/test_recursion_limit.py` — test-order flakiness, pass in isolation (43/43).

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/launch/workers/w2_facts_builder/code_analyzer.py` | 1A: init re-exports, 1B: function_details, 1C: defaults, 1D: method start_line, 3A: capabilities, 3B: workflows, 3C: example_coverage | ~180 lines added |
| `src/launch/workers/w5_section_writer/multi_pass.py` | Constructor defaults + function_details rendering | ~25 lines changed |
| `src/launch/workers/w2_facts_builder/extract_claims.py` | excerpt_hash + context line range | ~15 lines added |
| `specs/schemas/api_inventory.schema.json` | function_details, constructor.default, method_details.start_line | +25 lines |
| `specs/schemas/evidence_map.schema.json` | excerpt_hash, context_start_line, context_end_line | +12 lines |
| `specs/schemas/repo_truth.schema.json` | capabilities, workflows, example_coverage | +40 lines |
| `tests/unit/workers/test_w2_quality_uplift.py` | 48 new tests across 16 test classes | ~600 lines new |

## Schema Compliance

All three schemas updated BEFORE code changes to avoid `additionalProperties: false` violations:
- `api_inventory.schema.json`: function_details (root), method_details.start_line, constructor.parameters.default
- `evidence_map.schema.json`: citations.excerpt_hash, citations.context_start_line, citations.context_end_line
- `repo_truth.schema.json`: capabilities, workflows, example_coverage (all optional, root additionalProperties=true)

## Backward Compatibility

- `functions` flat list preserved (function_details is additive)
- `constructor.parameters` still has name+annotation (default is additive)
- `method_details` still has name+signature+docstring+return_type (start_line is additive)
- All new repo_truth fields are optional (schema has additionalProperties=true)
- All new evidence_map citation fields are optional (not in required list)
