# TC-1046: Evidence Report

## Objective

Replace the Jaccard similarity heuristic in `map_evidence.py` with TF-IDF cosine similarity for improved evidence-to-claim matching accuracy.

## Files Changed

### Created

| File | Purpose |
|------|---------|
| `src/launch/workers/w2_facts_builder/embeddings.py` | TF-IDF-based semantic similarity module (stdlib only) |
| `tests/unit/workers/test_w2_embeddings.py` | 33 unit tests for the embeddings module |

### Modified

| File | Change |
|------|--------|
| `src/launch/workers/w2_facts_builder/map_evidence.py` | `compute_text_similarity()` now delegates to `embeddings.compute_tfidf_similarity()` |

## Implementation Details

### embeddings.py

Public API:

- `tokenize(text) -> List[str]` -- Lowercase tokenization with stopword and short-word removal. Stopword set is identical to the one in `map_evidence.extract_keywords_from_claim()`.
- `compute_tf(tokens) -> Dict[str, float]` -- Term frequency: count/total.
- `compute_idf(documents) -> Dict[str, float]` -- Smoothed IDF: `log(1 + N/df)`. The smoothing prevents shared terms from collapsing to zero weight in 2-document corpora.
- `compute_tfidf_vector(tokens, idf) -> Dict[str, float]` -- Sparse TF-IDF vector.
- `cosine_similarity(vec1, vec2) -> float` -- Cosine similarity on sparse dicts. Handles zero vectors gracefully.
- `compute_tfidf_similarity(text1, text2) -> float` -- End-to-end API: tokenize, build 2-doc corpus, compute TF-IDF vectors, return cosine similarity. Short-circuits to 1.0 for identical token bags.
- `get_similarity_scorer(llm_client=None) -> Callable` -- Factory that returns the TF-IDF scorer.

### Key Design Decisions

1. **Smoothed IDF (`log(1 + N/df)`)**: Standard IDF (`log(N/df)`) zeros out any term appearing in all documents. With a 2-document corpus this means shared terms contribute nothing, making the cosine similarity unable to detect overlap. The smoothed variant preserves overlap signal while still giving higher weight to discriminative terms.

2. **Identical-document short-circuit**: When both documents produce the same token bag (Counter), the function returns 1.0 directly. This is mathematically correct and avoids edge cases in the vector computation.

3. **Sparse dict representation**: Vectors are `Dict[str, float]` instead of dense arrays, making the implementation memory-efficient and free of numpy/scipy dependencies.

4. **Drop-in replacement**: `compute_text_similarity()` in `map_evidence.py` preserves its exact signature and return range `[0.0, 1.0]`. The scoring weights in `score_evidence_relevance()` remain unchanged at 0.3/0.4/0.3.

### map_evidence.py Change

The `compute_text_similarity()` function body was replaced with a single-line delegation:

```python
from .embeddings import compute_tfidf_similarity
return compute_tfidf_similarity(text1, text2)
```

All other functions remain untouched.

## Test Results

### New tests: 33 passed

```
tests/unit/workers/test_w2_embeddings.py - 33 passed
```

Test classes and coverage:
- `TestTokenize` (5 tests): basic, empty, stopword removal, short word removal, order preservation
- `TestComputeTF` (3 tests): frequency, empty, single token
- `TestComputeIDF` (4 tests): single doc, multi doc, empty corpus, duplicate tokens
- `TestComputeTFIDFVector` (3 tests): weighting, empty tokens, missing IDF term
- `TestCosineSimilarity` (6 tests): identical, orthogonal, similar, zero first, zero second, both zero
- `TestComputeTFIDFSimilarity` (7 tests): identical, empty first/second/both, similar>dissimilar, deterministic, stopword-only
- `TestGetSimilarityScorer` (3 tests): returns callable, offline works, with llm_client
- `TestTFIDFVsJaccard` (2 tests): semantic discrimination, score range

### Existing tests: 38 passed

```
tests/unit/workers/test_tc_412_map_evidence.py - 38 passed
```

All existing map_evidence tests pass without modification, confirming backward compatibility.

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All new tests pass (min 12) | PASS | 33 tests passed |
| All existing map_evidence tests pass (38+) | PASS | 38 tests passed |
| TF-IDF more accurate than Jaccard | PASS | `test_tfidf_better_discriminates_semantic_match` |
| No external dependencies | PASS | Only uses `math`, `re`, `collections.Counter` |
| Deterministic output | PASS | `test_deterministic`, `test_map_evidence_deterministic_output` |
| Stdlib only | PASS | No numpy, scipy, sklearn imports |
| Cosine returns [0, 1] | PASS | `test_tfidf_score_range` |
| Empty text returns 0.0 | PASS | `test_empty_first_string`, `test_empty_second_string`, `test_both_empty_strings` |
| Identical text returns 1.0 | PASS | `test_identical_strings`, `test_identical_vectors` |
