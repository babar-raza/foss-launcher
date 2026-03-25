# TC-4286 Evidence: Fallback claim_id fan-out bug

## Root Cause

`render_section_deterministic()` in `fallback.py` line 174 passed `claim_ids=snippet.claim_ids` without filtering. A single snippet carries 24-96 claim_ids (linked across many API features), but the section is only assigned 12 claims by the planner.

**Chain**: Planner assigns 12 claims → Snippet fan-out brings 31 snippets carrying 134 unique claim_ids → Fallback renderer writes all 134 into IR blocks → Evaluator checks coverage against 134 claims instead of 12 → 71-78% uncovered → HIGH severity → editorial-critical failure.

## Fix

In `render_section_deterministic()`, build `assigned_ids = {c.claim_id for c in claims}` from the section's assigned claims. Filter snippet.claim_ids to `[cid for cid in snippet.claim_ids if cid in assigned_ids]`. When `claims` is empty (externally-linked snippets), keep original claim_ids.

## Tests

2 new tests in `TestFallbackRenderer`:
1. `test_snippet_claim_ids_filtered_to_section_claims` — snippet with ["C001", "C099", "C100"] filtered to ["C001"] when section claims = [C001]
2. `test_snippet_claim_ids_kept_when_no_claims` — empty claims list preserves original claim_ids

## Impact

Eliminates claim_coverage HIGH findings on reference pages (api-overview, workbook, worksheet, cells) across all pilots. Pages evaluated against 12 assigned claims instead of 128+. Reduces editorial-critical rate by ~18% per pilot.
