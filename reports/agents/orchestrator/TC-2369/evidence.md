# TC-2369 Evidence: W5 Generator-Specific Context Builders

## Changes Made

### `src/launch/workers/w5_section_writer/generators/content_generators.py`
- Added `build_tutorial_context(page, product_facts, snippet_catalog)`:
  - Orders claims: workflow/feature kinds first, other kinds after (max 10)
  - Collects `demo_snippet_ids` from ordered claims (TC-2368 binding)
  - Falls back to first-5 catalog snippets if no demo IDs available
  - Returns dict: `claims`, `snippets`, `claim_context`, `snippet_text`
- Added `build_feature_showcase_context(page, product_facts, snippet_catalog, primary_claim, related_claims)`:
  - Collects `demo_snippet_ids` from primary claim and related claims
  - Falls back to first-5 catalog snippets if no demo IDs
  - Returns dict with same keys as tutorial context
- Added `build_api_reference_context(page, product_facts, snippet_catalog)`:
  - Sorts api/format claims alphabetically by claim_text; other kinds appended after
  - Gets snippets from api claim demo_snippet_ids, fallback to 'api'/'reference' tagged snippets
  - Returns dict with same keys
- Updated `generate_tutorial_content()`:
  - Replaced generic `_build_enriched_claim_context(claims, product_facts)` + first-5-snippets
  - Now calls `build_tutorial_context(page, product_facts, snippet_catalog)` for both context vars
- Updated `generate_feature_showcase_content()`:
  - Replaced generic `_build_enriched_claim_context(all_feature_claims, ...)` + first-5-snippets
  - Now calls `build_feature_showcase_context(page, ...)` for both `enriched_context` and `snippet_context`
  - Fixed follow-on bug: `_call_llm_for_content()` `snippets=` param now uses `feature_ctx["snippets"]`

### `tests/unit/workers/test_tc_440_section_writer.py`
- Added import for `build_tutorial_context`, `build_feature_showcase_context`, `build_api_reference_context`
- Added `TestTC2369GeneratorContextBuilders` class (4 tests):
  - `test_build_tutorial_context_workflow_claims_first`: workflow claims ordered before limitation
  - `test_build_tutorial_context_uses_demo_snippet_ids`: demo_snippet_ids preferred over catalog order
  - `test_build_feature_showcase_context_uses_primary_snippets`: primary claim demo snippets used
  - `test_build_api_reference_context_sorts_api_claims`: api claims sorted alphabetically

## Test Results

```
tests/unit/workers/test_tc_440_section_writer.py::TestTC2369GeneratorContextBuilders::test_build_tutorial_context_workflow_claims_first PASSED
tests/unit/workers/test_tc_440_section_writer.py::TestTC2369GeneratorContextBuilders::test_build_tutorial_context_uses_demo_snippet_ids PASSED
tests/unit/workers/test_tc_440_section_writer.py::TestTC2369GeneratorContextBuilders::test_build_feature_showcase_context_uses_primary_snippets PASSED
tests/unit/workers/test_tc_440_section_writer.py::TestTC2369GeneratorContextBuilders::test_build_api_reference_context_sorts_api_claims PASSED
```

Full suite (excluding pre-existing NUL device OS artifact): 4517 passed, 9 skipped, 1 warning

## Acceptance Criteria Verification

- [x] All existing W5 section_writer tests still pass
- [x] 4 new tests pass
- [x] Tutorial generator receives workflow claims first, then feature claims
- [x] Feature showcase generator receives snippets linked to primary claim
- [x] API reference generator receives api claims sorted alphabetically
- [x] Fallback to first-5 when no demo_snippet_ids available

## Bug Fix During Implementation

Discovered and fixed a follow-on bug in `generate_feature_showcase_content()`: the
`_call_llm_for_content()` call at line 1615 referenced the old `snippets` local variable
which was removed by the context builder replacement. Fixed by using `feature_ctx["snippets"]`
(the snippets from the per-role context builder).
