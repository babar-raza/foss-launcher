# PM-02: Code Hygiene — Imports, Constants, Dead Parameter

## Status: Done

## Gap Linkage: PM-G2, PM-G3

## Role
Senior engineer. Drop-in, production-ready.

## Context
TC-3813 introduced `import re as _re` at line 359 (mid-file) rather than with
the other imports at the top. Two constants (`_MIN_CLAIMS_PER_CLASS`,
`_MIN_CLASS_NAME_LEN`) were placed next to the helpers instead of in the
constants block. Additionally, `_class_name_to_slug` accepts a `product`
parameter that is never used — the plan originally intended family-keyword
enrichment but it was dropped during implementation without removing the
parameter.

## Scope

### Fix
1. Remove `import re as _re` from line 359; add `import re` to the top imports
   block. Replace all `_re.` references with `re.` in the affected functions.
2. Move `_MIN_CLAIMS_PER_CLASS` and `_MIN_CLASS_NAME_LEN` to the constants block
   (after `_MAX_CLAIMS_PER_PAGE` around line 34-40).
3. Remove the `product` parameter from `_class_name_to_slug()`. Update all call
   sites (currently: `_expand_per_module` line ~561, tests).

### Allowed paths
- `src/launcher/workers/planner/plan.py`
- `tests/test_planner_per_module.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- Existing tests still pass after refactor
- No new tests needed (refactor-only)

### Config respected end-to-end
- N/A

### No mock data in production paths
- N/A

## Deliverables
- Modified `src/launcher/workers/planner/plan.py`: import moved, constants moved,
  dead parameter removed, all `_re.` → `re.`
- Modified `tests/test_planner_per_module.py`: remove `_make_product()` from
  `_class_name_to_slug` test calls

## Hard rules
- Keep public signatures unless justified — removing unused `product` param is
  justified because no external caller passes it (function is private `_`-prefixed)
- Update all call sites
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Consistency | All imports at top, all constants in constants block |
| Maintainability | No dead parameters, no mid-file imports |
| Minimality | Pure refactor, zero behavioral change |
| Correctness | All call sites updated, tests pass |

## Now (runbook)

```bash
# 1. In plan.py: add `import re` to top imports (line ~7)
# 2. Remove line 359 (`import re as _re`)
# 3. Find-replace _re. → re. in plan.py (only in the affected functions)
# 4. Move _MIN_CLAIMS_PER_CLASS and _MIN_CLASS_NAME_LEN to constants block
# 5. Remove `product` parameter from _class_name_to_slug signature
# 6. Update call site in _expand_per_module
# 7. Update tests

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
