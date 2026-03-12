# PM-01: Fix Case-Insensitive Class-Claim Matching

## Status: Done

## Gap Linkage: PM-G1

## Role
Senior engineer. Drop-in, production-ready.

## Context
`_build_class_claim_index()` compiles regex patterns without `re.IGNORECASE`.
Claim text frequently lowercases class names (e.g., "the workbook class handles
file loading") while `public_classes` contains the PascalCase canonical name
("Workbook"). The current code misses these matches, under-counting viable
classes and preventing per_module pages from being created when they should be.

This is the highest-severity gap from the TC-3813 self-review — a real bug
that will cause the gating to be too aggressive in production.

## Scope

### Fix
- Add `re.IGNORECASE` flag to the compiled pattern in `_build_class_claim_index()`
- Add a test case verifying lowercase claim text matches PascalCase class names
- Add a test case verifying mixed-case matching (e.g., "WORKBOOK" in claim text)

### Allowed paths
- `src/launcher/workers/planner/plan.py`
- `tests/test_planner_per_module.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py -v` — all pass

### Tests
- New test: claim text "the workbook class handles loading" matches class "Workbook"
- New test: claim text "WORKBOOK supports saving" matches class "Workbook"
- Existing tests still pass (no regressions)

### Config respected end-to-end
- N/A (no config changes)

### No mock data in production paths
- N/A

## Deliverables
- Modified `src/launcher/workers/planner/plan.py`: add `re.IGNORECASE` to line ~416
- Modified `tests/test_planner_per_module.py`: 2 new test methods in `TestBuildClassClaimIndex`

## Hard rules
- Keep public signatures unchanged
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Both lowercase and UPPERCASE claim text tested |
| Consistency | Flag added consistently to all compiled patterns |
| Production grading | Bug eliminated with zero false-positive risk |
| Correctness | Case-insensitive matching is semantically correct for class names |
| Robustness | No edge case where IGNORECASE causes wrong matches |
| Testability | Specific parametrized tests for case variations |
| Performance | No measurable impact (IGNORECASE adds negligible overhead) |
| Minimality | Single-line fix + 2 test methods |

## Now (runbook)

```bash
# 1. Apply fix
# In src/launcher/workers/planner/plan.py line ~416, change:
#   _re.compile(rf"\b{_re.escape(cls)}\b")
# to:
#   _re.compile(rf"\b{_re.escape(cls)}\b", _re.IGNORECASE)

# 2. Add tests to tests/test_planner_per_module.py in TestBuildClassClaimIndex:
#   test_case_insensitive_lowercase
#   test_case_insensitive_uppercase

# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py -v

# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
