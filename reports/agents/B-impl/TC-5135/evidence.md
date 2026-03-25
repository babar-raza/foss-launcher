# TC-5135 Evidence — Three-Tier Structural Snippet-Claim Linking

## Changes Made

### `src/launcher/workers/understand/extract/_linking.py`
- Added three-tier structural linking cascade:
  - **Tier 1 — API identity**: `_detect_api_entities()` + `_build_claim_api_index()` match snippet class/method names against claims referencing those API entities
  - **Tier 2 — TF-IDF cosine**: `compute_tfidf_similarity()` from `shared/embeddings.py` with threshold 0.25
  - **Tier 3 — Word overlap**: existing `_link_snippet_to_claims()` as fallback
- Added `link_snippets()` bulk entry point
- Fixed PascalCase regex limitation: added direct name matching for single-hump names like "Workbook"
- Added `_CLASS_METHOD_RE` for detecting `ClassName.method()` patterns in claims

### `src/launcher/workers/understand/extract/_snippets.py`
- Removed inline `_link_snippet_to_claims()` calls at two locations
- Snippets now created with `claim_ids=[]`, linking deferred to bulk step

### `src/launcher/workers/understand/extract/_entry.py`
- Added bulk linking call after `_extract_snippets()`:
  ```python
  snippets = _link_snippets_bulk(snippets, claims, api_surface, _pre_llm_api_facts)
  ```

### `src/launcher/workers/understand/extract/__init__.py`
- Added `link_snippets` to module exports

### `tests/unit/workers/understand/test_structural_linking.py` (new)
- 15 tests covering all three tiers and edge cases
- Test classes: TestDetectApiEntities, TestBuildClaimApiIndex, TestLinkSnippetsTier1, TestLinkSnippetsTier2, TestLinkSnippetsTier3, TestLinkSnippetsEdgeCases

## Test Results

```
tests/unit/workers/understand/test_structural_linking.py: 15/15 PASS
Full suite: 5096 passed, 0 failed
```

## Key Verification

- Tier 1 correctly links `Workbook()` snippet to "Workbook provides save functionality" claim
- Tier 1 correctly rejects "Worksheet cells provide formatting" decoy (no false positive from domain vocab)
- `_detect_api_entities()` handles single-hump PascalCase ("Workbook") via direct match
- Max links cap (10) respected

## Acceptance Checks

- [x] Tier 1 API identity match works for known classes
- [x] No false positives from domain vocabulary overlap
- [x] Tier 2 TF-IDF fallback activates when no class detected
- [x] Tier 3 word-overlap fallback works as last resort
- [x] Already-linked snippets preserved
- [x] Max links per snippet respected
- [x] All existing tests pass
- [x] New tests pass (15/15)
