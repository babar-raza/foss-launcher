# TC-4290 Evidence — Planner: Widen claim-kind eligibility

## Date: 2026-03-14

## Changes Made

### 1. `src/launcher/workers/planner/plan.py`
- **`_KIND_TO_ROLES`**: Added `api` to all prose-generating roles (workflow_page, howto_article, tutorial, faq, troubleshooting, feature_showcase, blog_announcement, feature_blog, landing)
- **`_KIND_TO_ROLES`**: Added `feature` to workflow_page, howto_article, tutorial
- **`_KIND_TO_ROLES`**: Added `format` to workflow_page, howto_article
- **`_MAX_CLAIMS_PER_PAGE`**: Raised from 12 to 20
- **`_MAX_CLAIM_PAGES`**: Raised from 2 to 3
- **Page sorting**: Added `_page_sort_key()` to prioritize reference_object_page and api_reference pages in claim assignment order

### 2. Test fixes
- `tests/unit/workers/test_understand.py`: Updated `test_claim_assignment_max_2` to use `_MAX_CLAIM_PAGES` constant instead of hardcoded 2
- `tests/unit/workers/test_planner_topic_starvation.py`: Changed `test_ineligible_kind_does_not_trigger_starvation` to use `kind="license"` (genuinely ineligible) instead of `kind="feature"` (now eligible after widening)

## Root Cause Addressed

76-83% of extracted claims are `api` kind, but `_KIND_TO_ROLES` restricted `api` to only 1-4 page roles (api_reference, reference_object_page, comprehensive_guide). The remaining 14-18 pages were claim-starved, forcing LLM to hallucinate content.

## Test Results

```
4436 passed, 65 skipped, 3 xfailed, 2 xpassed in 102.93s
```

## Expected E2E Impact

- Pages go from 0-2 claims to 8-15 claims
- Fewer hallucinations → fewer api_identifier_unknown_* findings
- Better claim coverage → fewer claim_coverage HIGH findings
- Better route consistency → fewer route_consistency HIGH findings
