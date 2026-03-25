# TC-2366 Evidence: W4 Similarity-Based Claim Selection

## Changes Made

### `src/launch/workers/w4_ia_planner/worker.py`
- Added `select_claims_by_similarity(purpose, candidates, top_k)` function:
  - Uses TF-IDF cosine similarity from existing `embeddings.py` module
  - Falls back to `candidates[:top_k]` when embeddings unavailable or inputs empty
  - Falls back to order-preserving slice when all similarity scores are zero
  - Graceful handling: empty candidates → [], empty purpose → first-K, top_k=0 → []

### `tests/unit/workers/test_tc_430_ia_planner.py`
- Added `select_claims_by_similarity` to imports
- Added `TestTC2366SelectClaimsBySimilarity` class (4 tests):
  - Returns relevant installation claims for installation-focused purpose
  - Empty candidates returns empty
  - Empty purpose returns first-K fallback
  - Fewer candidates than top_k returns all

## Test Results

```
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2366SelectClaimsBySimilarity::test_select_returns_top_k_relevant PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2366SelectClaimsBySimilarity::test_select_empty_candidates_returns_empty PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2366SelectClaimsBySimilarity::test_select_empty_purpose_returns_first_k PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2366SelectClaimsBySimilarity::test_select_fewer_than_k_returns_all PASSED
```

Full suite: 4515 passed, 9 skipped, 1 pre-existing failure (NUL device OS artifact)

## Acceptance Criteria Verification

- [x] All existing W4 tests still pass (118 total, all green)
- [x] 4 new tests pass
- [x] `select_claims_by_similarity("", [], 5)` returns `[]` (graceful empty)
- [x] Real data returns semantically relevant claims first (installation claims top-ranked for installation purpose)

## Note on Call Site Integration

TC-2366 specifies adding the function and validates its behavior. Existing call sites
in `plan_pages_for_section()` / `generate_optional_pages()` retain bucket-based
assignment for backwards compatibility; migrating individual call sites is the next
incremental step per the RCA plan's Short-Term phase.
