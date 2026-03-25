# TC-5134 Evidence — Sort Stability Tiebreakers + Content Drift Detection

## Changes Made

### `src/launcher/workers/planner/plan.py`
- Added `getattr(sf, "fact_id", "")` as third tuple element in snippet seeding sort (line ~595)
- Provides deterministic tiebreaker when confidence and priority are equal

### `src/launcher/workers/generate/section_prompt.py`
- Replaced `claim_ids[0]` fallback tiebreaker in `_rank_snippets()` with:
  - `getattr(s, "snippet_id", "") or ""` as primary tiebreaker
  - `_hl.md5((getattr(s, "code", "") or "").encode(), usedforsecurity=False).hexdigest()` as secondary
- Guarantees unique sort key even when snippet_id is missing

### `src/launcher/workers/generate/worker.py`
- Added `import hashlib` at module level
- Added content fingerprinting block before `return manifest`:
  - Computes SHA-256 per page, composite hash, writes `content_fingerprint.json`
  - Wrapped in try/except — fingerprint is diagnostic, not a gate
- **Bug fix**: Changed `_fp_page.content_path` to `_fp_page.md_path` — content_path doesn't
  include the `content_bundle/pages/` prefix or `.md` extension, so the original code always
  resolved to non-existent paths (page_count=0). Discovered during pilot run comparison.

### `tests/unit/workers/test_sort_stability.py` (new, SR-01)
- 6 tests covering both plan.py and section_prompt.py sort stability
- TestPlanSortStability: equal-priority sort by fact_id, 10-run shuffle stability, primary sort preserved
- TestSectionPromptSortStability: equal-score sort by code hash, 10-run shuffle stability, source_type primary

## Test Results

```
tests/unit/workers/test_sort_stability.py: 6/6 PASS
Full suite: 5186 passed, 0 failed
```

## Pilot Run Evidence

Content fingerprint (after md_path fix, verified manually):
- Run `260318_082116_cells_python_1012`: 19 pages fingerprinted
- Composite hash: `a6c5abac9534e3d1...`
- Per-page hashes verified for all 19 pages

## Acceptance Checks

- [x] Equal-priority items sorted identically (fact_id tiebreaker)
- [x] Content fingerprint JSON produced with correct page hashes
- [x] All existing tests pass (5186)
- [x] Snippet ranking uses unique tiebreaker (MD5 code hash)
- [x] Dedicated sort stability test file created (6 tests)
