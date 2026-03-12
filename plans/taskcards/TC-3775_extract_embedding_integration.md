---
id: TC-3775
title: "Integrate embeddings into extract.py Phase B.4"
status: Draft
priority: High
owner: "agent-B"
updated: "2026-03-07"
tags: [embeddings, understand, extract]
depends_on: [TC-3774]
allowed_paths:
  - plans/taskcards/TC-3775_extract_embedding_integration.md
  - src/launcher/workers/understand/extract.py
  - tests/integration/test_extract_embeddings.py
evidence_required:
  - reports/agents/embeddings/TC-3775/evidence.md
---

# Taskcard TC-3775 -- Integrate Embeddings into extract.py

## Objective

Add Phase B.4 to `extract.py` that computes an embedding index for all extracted claims and doc chunks, writing `embedding_index.json` as a side artifact for downstream workers.

## Required spec references

- `specs/03_product_facts_and_evidence.md` (Evidence mapping)
- `specs/21_worker_contracts.md` (W2 contract)

## Scope

### In scope
- Add `_compute_embeddings()` helper to extract.py
- Add `_chunk_text()` helper for doc content chunking
- Wire Phase B.4 into `run_extract()` after snippet extraction
- Write embedding_index.json artifact
- Integration tests

### Out of scope
- Modifying downstream workers to consume the index (future TCs)
- Modifying map_evidence.py scoring (future TC)

## Inputs

- Claims list from Phase B.2-B.3
- Doc contexts from `_build_doc_contexts()`
- WorkerContext with llm_config and artifact store

## Outputs

- `artifacts/embedding_index.json` in run directory
- Updated extract.py with Phase B.4

## Allowed paths

- plans/taskcards/TC-3775_extract_embedding_integration.md
- src/launcher/workers/understand/extract.py
- tests/integration/test_extract_embeddings.py
- reports/agents/embeddings/TC-3775/evidence.md

### Allowed paths rationale
- extract.py: integration point
- test_extract_embeddings.py: integration tests
- evidence.md: test output capture

## Implementation steps

### Step 1: Add _chunk_text() helper

Split text into ~500-char segments at sentence boundaries.

### Step 2: Add _compute_embeddings() function

Build text map from claims + doc chunks. Try API client if configured. Fall back to TF-IDF.

### Step 3: Wire into run_extract()

After Phase B.3, call _compute_embeddings() and save artifact.

### Step 4: Write integration tests

Test artifact production with mock LLM context.

## Failure modes

### Failure mode 1: No WorkerContext.store available

**Detection**: AttributeError on context.store
**Resolution**: Guard with hasattr check; skip embedding if no store
**Gate**: Worker contract compliance

### Failure mode 2: Empty claims list

**Detection**: embed_texts receives empty dict
**Resolution**: Return None early, skip artifact write
**Gate**: Graceful degradation

### Failure mode 3: Embedding API timeout during extract

**Detection**: Timeout exception from EmbeddingClient
**Resolution**: Caught by is_available() probe; falls back to TF-IDF
**Gate**: Resilience

## Task-specific review checklist

1. [ ] _compute_embeddings() uses try/except for robustness
2. [ ] Artifact written only when index is non-empty
3. [ ] Doc chunks capped at reasonable size (500 chars, max 250 chunks)
4. [ ] Claims keyed as "claim:{claim_id}" for downstream lookup
5. [ ] No modification to existing run_extract() return signature
6. [ ] Logging at appropriate level (info for success, warning for fallback)

## Deliverables

1. `src/launcher/workers/understand/extract.py` (updated)
2. `tests/integration/test_extract_embeddings.py`
3. `reports/agents/embeddings/TC-3775/evidence.md`

## Acceptance checks

1. [ ] extract.py Phase B.4 runs without error
2. [ ] embedding_index.json artifact produced
3. [ ] Integration tests pass under PYTHONHASHSEED=0
4. [ ] Existing extract tests still pass (no regression)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: artifact production PASS
- [ ] Evidence captured: reports/agents/embeddings/TC-3775/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_extract_embeddings.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k extract -v
```

**Expected results**:
- Embedding index artifact written with claim keys
- No regression in existing extract tests

## Integration boundary proven

**Upstream**: TC-3774 embeddings module (EmbeddingClient, embed_texts, EmbeddingIndex)
**Downstream**: Generate/Evaluate workers (future consumption of embedding_index.json)
**Contract**: EmbeddingIndex JSON artifact with keys "claim:{id}" and "doc:{path}:{chunk_idx}"
