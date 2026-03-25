# TC-3686 Report — W4 Claim Distribution Title-Keyword Boost + Usage Cap

## Summary
Added title-keyword matching to W4 claim selection and capped single-claim
reuse at 3 pages to resolve 5+ title-content mismatch issues.

## Root Cause
`select_claims_for_page()` pulls claims in fixed priority order with no
title-keyword matching. `used_claim_ids` was a binary set with no tracking
of how many pages share a claim.

## Changes
- `worker.py` (W4): Added `_rerank_claims_by_title()` function with keyword
  overlap scoring, `MAX_PAGES_PER_CLAIM = 3` constant, `_TITLE_MATCH_STOPWORDS`
  frozenset. Changed `used_claim_ids` from `set` to `_claim_usage_counts: Dict`.

## Tests
- 11 new tests in `tests/unit/workers/w4/test_claim_title_boost.py`
  - `TestTitleKeywordMatch` (4): matching ranked, no keywords, stopwords, stable
  - `TestUsageCap` (3): capped excluded, below cap, empty counts
  - `TestEdgeCases` (4): empty IDs, missing claim_text, constant, purpose words

## Verification
- Full suite: 8617 passed, 0 failed (PYTHONHASHSEED=0)
