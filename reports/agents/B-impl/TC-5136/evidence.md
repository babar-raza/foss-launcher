# TC-5136 Evidence — Claim Coverage Depth Verification (Pass 2)

## Changes Made

### `src/launcher/workers/evaluate/checks/claim_coverage.py`
- Added Pass 2 TF-IDF depth verification after existing Pass 1 keyword check
- New constants: `_DEPTH_THRESHOLD = 0.20`, `_CONTEXT_WINDOW = 300`
- New functions:
  - `_extract_claim_context(body, key_terms, window)` — extracts +/-300 char window around keyword match
  - `_verify_claim_depth(claim_text, context_text)` — TF-IDF cosine similarity via `shared/embeddings.py`
- Modified `check_claim_coverage()`:
  - Pass 1 (existing): keyword coverage — behavior unchanged
  - Pass 2 (new): for keyword-covered claims, verify depth via TF-IDF
  - Shallow claims produce `Finding(check="claim_coverage_depth", severity="low")`
- Graceful degradation: if `compute_tfidf_similarity` import fails, depth check is skipped

### `tests/unit/workers/evaluate/checks/test_claim_coverage.py`
- Added 9 new tests in 3 test classes:
  - `TestExtractClaimContext`: window extraction, empty input, boundary clamping
  - `TestVerifyClaimDepth`: substantive > 0.20, casual < 0.20, empty inputs
  - `TestClaimCoverageDepthIntegration`: shallow coverage finding, Pass 1 unchanged, substantive no findings

## Test Results

```
tests/unit/workers/evaluate/checks/test_claim_coverage.py: 21/21 PASS (12 existing + 9 new)
Full suite: 5096 passed, 0 failed
```

## Key Verification

- Substantive paragraph ("Use Workbook.save() to write your spreadsheet data to XLSX format...") scores > 0.20
- Casual mention ("The library supports many file formats...") scores < 0.20
- Pass 1 behavior completely unchanged (all 12 existing tests pass unmodified)
- Pass 2 findings are informational only (severity="low"), do not block generation

## Acceptance Checks

- [x] Substantive content scores above depth threshold
- [x] Casual mentions score below depth threshold
- [x] Shallow coverage produces Finding with check="claim_coverage_depth"
- [x] Pass 1 keyword coverage behavior unchanged
- [x] All existing tests pass
- [x] New tests pass (9/9)
