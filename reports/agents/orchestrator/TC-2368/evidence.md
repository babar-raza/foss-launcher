# TC-2368 Evidence: W4 Claim-to-Snippet Binding (demo_snippet_ids)

## Changes Made

### `src/launch/workers/w4_ia_planner/worker.py`
- Added `link_claims_to_snippets(claims, snippet_catalog, max_per_claim=2)` function:
  - Uses TF-IDF cosine similarity from existing `embeddings.py` module
  - Tokenizes each snippet as `code + tags` for richer matching
  - Builds shared IDF over all claim texts + snippet texts for accurate scoring
  - Pre-computes snippet TF-IDF vectors once (O(n) not O(n×m) per claim)
  - Sets `demo_snippet_ids: List[str]` = top-2 snippet_ids with score > 0.0
  - Idempotent: claims that already have `demo_snippet_ids` are not modified
  - Falls back gracefully: ImportError or empty catalog returns claims unchanged
- Added call to `link_claims_to_snippets()` in the W4 `run()` function:
  - Runs immediately after loading `product_facts` and `snippet_catalog` (line ~3749)
  - Updates `product_facts["claims"]` in-place
  - Wrapped in `try/except` — linking failure MUST NOT crash W4

### `tests/unit/workers/test_tc_430_ia_planner.py`
- Added `link_claims_to_snippets` to imports
- Added `TestTC2368LinkClaimsToSnippets` class (4 tests):
  - Claim with token overlap gets correct demo_snippet_id
  - Empty catalog returns claims unchanged
  - Claim with no token overlap gets empty demo_snippet_ids
  - Claims with existing demo_snippet_ids are not overwritten

## Test Results

```
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2368LinkClaimsToSnippets::test_link_claims_basic_match PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2368LinkClaimsToSnippets::test_link_claims_empty_catalog PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2368LinkClaimsToSnippets::test_link_claims_no_overlap PASSED
tests/unit/workers/test_tc_430_ia_planner.py::TestTC2368LinkClaimsToSnippets::test_link_claims_preserves_existing PASSED
```

Full suite (excluding pre-existing NUL device OS artifact): 4517 passed, 9 skipped, 1 warning

## Acceptance Criteria Verification

- [x] All existing W4 tests still pass
- [x] 4 new tests pass
- [x] `demo_snippet_ids` present on all claims after linking (list, possibly empty)
- [x] `claim_id` unchanged by this addition (SHA256 inputs unmodified)
- [x] Failure in linking MUST NOT crash W4 (try/except guard in run() function)

## Integration Notes

W4 is the first pipeline worker that reads both `product_facts.json` (from W2) and
`snippet_catalog.json` (from W3). The linking runs at load-time before page planning,
making `demo_snippet_ids` available throughout all downstream processing including
W5 generator-specific context builders (TC-2369).
