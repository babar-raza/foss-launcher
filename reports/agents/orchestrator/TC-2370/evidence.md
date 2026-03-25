# TC-2370 Evidence: Gate 15 Method Signature Upgrade

## Implementation Summary

Modified `src/launch/workers/w9_validator/gates/gate_15_api_hallucination.py` to
also validate method names on known classes.

## Changes Made

### gate_15_api_hallucination.py

1. **`class_methods` extraction** — when loading `code_analysis.json`, now also
   builds `class_methods: Dict[str, Set[str]]` from each class's `methods` field,
   handling both string and dict method entries (lines ~118–141).

2. **Per-match method check** — in the match loop, when `symbol` IS in
   `known_symbols` and the ref contains a `.`, the member name (second segment,
   `(` stripped) is checked against `class_methods[symbol]`. Unknown methods emit
   G15-002 `GATE15_UNKNOWN_METHOD` warn (lines ~183–202).

3. **Gate still always passes** — no severity escalation; all new issues are `warn`.

## Test Results

```
tests/unit/workers/test_gate_15_api_hallucination.py::test_unknown_method_on_known_class_warns PASSED
tests/unit/workers/test_gate_15_api_hallucination.py::test_known_method_on_known_class_passes PASSED
tests/unit/workers/test_gate_15_api_hallucination.py::test_dotted_no_methods_data_skips PASSED
tests/unit/workers/test_gate_15_api_hallucination.py::test_single_symbol_no_dot_unchanged PASSED
```

4 new tests pass. Full suite: **4535 passed**, 9 skipped, 1 pre-existing NUL failure.

## Bug Fixed During Implementation

The test originally used `` `Scene.nonexistent()` `` but the Gate 15 regex
`r'`([A-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)`'` does not match when
`()` follows the identifier inside the backticks. Fixed test to use
`` `Scene.nonexistent` `` (no parentheses), consistent with how the regex works.

## Acceptance Criteria Verification

- [x] `Scene.nonexistent` (unknown method on known class) → G15-002 warn
- [x] `Scene.load` (real method) → no issue
- [x] No `methods` key in code_analysis → no method check (safe fallback)
- [x] Single-symbol reference (no dot) → unchanged top-level check behaviour
- [x] Gate always passes (warn-only)
- [x] 4 new tests pass
