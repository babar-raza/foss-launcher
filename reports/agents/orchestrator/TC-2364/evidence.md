# TC-2364 Evidence: W4 Content-Signal Role Assignment

## Changes Made

### `src/launch/workers/w4_ia_planner/worker.py`
- Added `from collections import Counter` import
- Modified `assign_page_role()` to accept optional `available_claims: Optional[List[Dict[str, Any]]] = None`
- Added TC-2364 content-signal classification block before slug fallback:
  - `api >= 40%` → `api_reference`
  - `workflow >= 40%` → `workflow_page`
  - `limitation >= 50%` → `troubleshooting`
  - `faq >= 30%` OR `"faq" in slug` → `faq`
  - `feature >= 40%` → `feature_showcase`
- Preserved all existing slug-based logic as fallback (100% backwards compatible)

### `tests/unit/workers/test_tc_430_ia_planner.py`
- Added `TestTC2364ContentSignalRoleAssignment` class (4 tests)
- Imported `select_claims_by_similarity` (for TC-2366)

## Test Results

```
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2364ContentSignalRoleAssignment::test_api_heavy_claims_gives_api_reference PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2364ContentSignalRoleAssignment::test_workflow_heavy_claims_gives_workflow_page PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2364ContentSignalRoleAssignment::test_slug_fallback_when_claims_ambiguous PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2364ContentSignalRoleAssignment::test_no_claims_uses_slug_only PASSED
```

Full suite: 4515 passed, 9 skipped, 1 pre-existing failure (NUL device OS artifact, unrelated)

## Acceptance Criteria Verification

- [x] All existing W4 tests still pass (118 total, all green)
- [x] 4 new tests pass
- [x] `assign_page_role(slug, available_claims=[])` behaves identically to `assign_page_role(slug)` (no claims = slug fallback)
