# PM-03: Add Claim-Assignment Priority Test

## Status: Done

## Gap Linkage: PM-G4

## Role
Senior engineer. Drop-in, production-ready.

## Context
TC-3813 added class-aware claim sorting in `_assign_claims()` — when a page has
`target_class` set, claims mentioning that class are sorted to the front so they
get assigned first. However, there is **no test** verifying this behavior. The
current tests only check that `target_class` is populated on the PlannedPage,
not that the page actually receives the correct class-relevant claims.

This is a core behavioral guarantee of the feature that is completely untested.

## Scope

### Fix
- Add test verifying that per_module page for "Workbook" receives claims
  mentioning "Workbook" rather than generic/unrelated claims
- Add test verifying that when claims are scarce, class-relevant claims are
  still prioritized even if they've already been assigned to other pages
  (up to `_MAX_CLAIM_PAGES` limit)

### Allowed paths
- `tests/test_planner_per_module.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py -v` — all pass

### Tests
- New test: `test_class_claims_prioritized_on_per_module_page` — verify that
  Workbook-mentioning claims are in the assigned_claims list for the Workbook page
- New test: `test_unrelated_claims_not_assigned_to_class_page` — verify that
  claims NOT mentioning the target class are not preferentially assigned
- Existing tests still pass

### Config respected end-to-end
- N/A

### No mock data in production paths
- N/A

## Deliverables
- Modified `tests/test_planner_per_module.py`: 2 new test methods in
  `TestPerModuleGating`

## Hard rules
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Testability | Both happy path and negative path tested |
| Correctness | Test assertions prove claims are correctly prioritized |
| Thoroughness | Tests cover: exact match, no match, mixed set |

## Now (runbook)

```bash
# 1. Add two test methods to TestPerModuleGating in tests/test_planner_per_module.py
# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py -v
```
