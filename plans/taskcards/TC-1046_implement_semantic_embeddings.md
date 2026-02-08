---
id: TC-1046
title: "Implement Semantic Embeddings for Evidence Mapping"
status: In-Progress
priority: P1
agent: Agent-B
depends_on: [TC-1045]
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
allowed_paths:
  - src/launch/workers/w2_facts_builder/embeddings.py
  - src/launch/workers/w2_facts_builder/map_evidence.py
  - tests/unit/workers/test_w2_embeddings.py
  - reports/agents/agent_b/TC-1046/**
---

# TC-1046: Implement Semantic Embeddings for Evidence Mapping

## Objective

Replace the Jaccard similarity heuristic in `map_evidence.py` with a semantic embedding-based similarity scoring system. Create `embeddings.py` module that provides vector embeddings for text, with offline fallbacks using TF-IDF when embeddings API is unavailable. The goal is to improve evidence→claim matching accuracy.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md` — Evidence mapping improvements
- `specs/03_product_facts_and_evidence.md` — Evidence priority and structure
- `specs/08_semantic_claim_enrichment.md` — Semantic understanding requirements
- `specs/10_determinism_and_caching.md` — Deterministic scoring

## Scope

### In scope

1. Create `src/launch/workers/w2_facts_builder/embeddings.py` with:
   - `compute_text_embedding()` — via LLM embedding API (when available)
   - `compute_cosine_similarity()` — vector cosine similarity
   - `compute_tfidf_similarity()` — offline fallback using TF-IDF (no external deps)
   - `get_similarity_scorer()` — factory that returns appropriate scorer based on mode
2. Update `map_evidence.py` `compute_text_similarity()` to use semantic similarity when available
3. Ensure offline mode preserves current Jaccard behavior (no regression)
4. Create comprehensive unit tests

### Out of scope

- External embedding libraries (sentence-transformers, etc.) — use stdlib only + LLM API
- Changing the evidence map schema
- Changing the W2 worker orchestration flow

## Inputs

- `src/launch/workers/w2_facts_builder/map_evidence.py` — Current similarity implementation
- `src/launch/clients/llm_provider.py` — LLM client interface
- `specs/03_product_facts_and_evidence.md` — Evidence scoring requirements

## Outputs

- `src/launch/workers/w2_facts_builder/embeddings.py` (NEW)
- `src/launch/workers/w2_facts_builder/map_evidence.py` (MODIFIED)
- `tests/unit/workers/test_w2_embeddings.py` (NEW)
- `reports/agents/agent_b/TC-1046/evidence.md`
- `reports/agents/agent_b/TC-1046/self_review.md`

## Allowed paths

- `src/launch/workers/w2_facts_builder/embeddings.py`
- `src/launch/workers/w2_facts_builder/map_evidence.py`
- `tests/unit/workers/test_w2_embeddings.py`
- `reports/agents/agent_b/TC-1046/**`

## Implementation steps

1. **Create `embeddings.py`** with TF-IDF similarity (stdlib-only):
   - `compute_tfidf_vectors(texts)` — build TF-IDF vectors using collections.Counter and math
   - `compute_cosine_similarity(vec1, vec2)` — dot product / (norm1 * norm2)
   - `compute_tfidf_similarity(text1, text2)` — end-to-end TF-IDF similarity
   - `get_similarity_scorer(llm_client=None)` — returns scoring function

2. **Update `map_evidence.py`**:
   - Replace `compute_text_similarity()` Jaccard with TF-IDF scorer from embeddings.py
   - Keep Jaccard as additional signal (weighted combination)
   - Preserve existing function signatures for backward compatibility
   - New scoring: 50% TF-IDF + 30% keyword match + 20% source priority

3. **Tests**:
   - TF-IDF computation correctness
   - Cosine similarity (identical/orthogonal/similar vectors)
   - Scorer factory (online vs offline mode)
   - Integration with map_evidence scoring
   - Deterministic output
   - Edge cases (empty text, single word, very long text)

## Failure modes

1. **TF-IDF computation failure**: Detection: ZeroDivisionError on empty vectors. Resolution: Return 0.0 similarity. Gate: Edge case tests.
2. **Scoring regression**: Detection: Existing tests fail. Resolution: Preserve backward-compatible scoring weights. Gate: All map_evidence tests pass.
3. **Performance degradation**: Detection: Evidence mapping takes >2x longer. Resolution: Cache TF-IDF vectors per document. Gate: Performance budget test.

## Task-specific review checklist

1. [ ] TF-IDF implementation uses only stdlib (no numpy, scipy, sklearn)
2. [ ] Cosine similarity returns float between 0.0 and 1.0
3. [ ] Empty text returns 0.0 similarity (no errors)
4. [ ] Identical texts return 1.0 similarity
5. [ ] map_evidence.py backward compatible (existing tests pass)
6. [ ] Deterministic scoring (same inputs → same scores)
7. [ ] Scorer factory works for online and offline modes

## Deliverables

- `src/launch/workers/w2_facts_builder/embeddings.py` — Embeddings module
- `tests/unit/workers/test_w2_embeddings.py` — Unit tests (minimum 12 tests)
- `reports/agents/agent_b/TC-1046/evidence.md`
- `reports/agents/agent_b/TC-1046/self_review.md`

## Acceptance checks

1. All new tests pass (minimum 12)
2. All existing map_evidence tests pass (38+ tests)
3. TF-IDF similarity more accurate than Jaccard for semantic matching
4. No external dependencies added
5. Deterministic output verified

## Self-review

Agent MUST perform 12D self-review before routing. Minimum 4/5 on all dimensions.
