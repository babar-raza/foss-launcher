---
id: TC-3774
title: "Core embeddings module with TF-IDF fallback and API client"
status: In-Progress
priority: High
owner: "agent-B"
updated: "2026-03-07"
tags: [embeddings, understand, shared]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3774_core_embeddings_module.md
  - src/launcher/shared/embeddings.py
  - src/launcher/models/run_config.py
  - tests/unit/shared/test_embeddings.py
evidence_required:
  - reports/agents/embeddings/TC-3774/evidence.md
---

# Taskcard TC-3774 -- Core Embeddings Module

## Objective

Create `src/launcher/shared/embeddings.py` by porting v1's proven TF-IDF implementation as a deterministic fallback and adding an `EmbeddingClient` for API-based neural embeddings via `qwen3-embedding-8b`. This immediately unblocks `map_evidence.py` which has 4 broken import sites.

## Required spec references

- `specs/03_product_facts_and_evidence.md` (Evidence mapping improvements)
- `specs/10_determinism_and_caching.md` (Deterministic scoring)
- `specs/34_strict_compliance_guarantees.md` (Guarantee D: Network allowlist)

## Scope

### In scope
- Port all TF-IDF functions from v1 `src/launch/workers/w2_facts_builder/embeddings.py`
- Create `EmbeddingClient` for OpenAI-compatible `/v1/embeddings` endpoint
- Create `EmbeddingIndex` for in-memory vector storage with save/load
- Create `embed_texts()` batch function with transparent fallback
- Update `get_similarity_scorer()` factory
- Add `EmbeddingEndpoint` model to `run_config.py`
- Unit tests for all functions

### Out of scope
- Integration into extract.py (TC-3775)
- Modifying map_evidence.py scoring logic (future TC)
- Dense vector database / persistent caching (future TC)

## Inputs

- v1 embeddings.py (main branch: `src/launch/workers/w2_facts_builder/embeddings.py`)
- v2 jaccard.py STOPWORDS constant
- http.py `http_post` for network-safe requests

## Outputs

- `src/launcher/shared/embeddings.py` — complete module
- `src/launcher/models/run_config.py` — updated with EmbeddingEndpoint
- `tests/unit/shared/test_embeddings.py` — unit test suite
- `reports/agents/embeddings/TC-3774/evidence.md` — test results

## Allowed paths

- plans/taskcards/TC-3774_core_embeddings_module.md
- src/launcher/shared/embeddings.py
- src/launcher/models/run_config.py
- tests/unit/shared/test_embeddings.py
- reports/agents/embeddings/TC-3774/evidence.md

### Allowed paths rationale
- embeddings.py: new shared module
- run_config.py: add EmbeddingEndpoint for config
- test_embeddings.py: unit tests
- evidence.md: test output capture

## Implementation steps

### Step 1: Create embeddings.py with TF-IDF port

Port all 7 TF-IDF functions verbatim from v1. Change import from `._shared` to `launcher.shared.jaccard`.

### Step 2: Add EmbeddingClient class

OpenAI-compatible `/v1/embeddings` client using `http_post`. Batch processing in groups of 32. `is_available()` probe.

### Step 3: Add EmbeddingIndex class

In-memory keyed vector store. Cosine similarity lookup. `most_similar()` ranked retrieval. Deterministic JSON save/load.

### Step 4: Add embed_texts() and get_similarity_scorer()

Batch embedding with automatic fallback. Factory returns appropriate scorer.

### Step 5: Update run_config.py

Add `EmbeddingEndpoint` model and optional field on `LLMConfig`.

### Step 6: Write unit tests

17+ test cases covering TF-IDF, index, client mock, fallback.

## Failure modes

### Failure mode 1: Import cycle with jaccard.py

**Detection**: `ImportError: cannot import name 'STOPWORDS' from 'launcher.shared.jaccard'`
**Resolution**: Verify jaccard.py exports STOPWORDS at module level (confirmed: line 8)
**Gate**: Module import test

### Failure mode 2: Network allowlist blocks embedding endpoint

**Detection**: `NetworkBlockedError` from http_post
**Resolution**: Embedding endpoint uses same host as LLM (`llm.professionalize.com`) which is already allowlisted
**Gate**: Guarantee D compliance

### Failure mode 3: Non-deterministic TF-IDF output

**Detection**: Test flakiness under different PYTHONHASHSEED values
**Resolution**: Sort all output dicts by key; use stable math operations (no set iteration for output)
**Gate**: Determinism spec compliance

## Task-specific review checklist

1. [ ] All 7 v1 TF-IDF functions ported with identical behavior
2. [ ] STOPWORDS imported from launcher.shared.jaccard (not duplicated)
3. [ ] EmbeddingClient uses http_post for network allowlist compliance
4. [ ] EmbeddingIndex.save() produces deterministic output (sorted keys)
5. [ ] embed_texts() falls back to TF-IDF when client=None or unavailable
6. [ ] get_similarity_scorer() returns TF-IDF when no config
7. [ ] EmbeddingEndpoint is Optional on LLMConfig (backward-compatible)
8. [ ] No new dependencies added (pure stdlib for TF-IDF path)

## Deliverables

1. `src/launcher/shared/embeddings.py`
2. `src/launcher/models/run_config.py` (updated)
3. `tests/unit/shared/test_embeddings.py`
4. `reports/agents/embeddings/TC-3774/evidence.md`

## Acceptance checks

1. [ ] `from launcher.shared.embeddings import tokenize, precompute_token_cache` succeeds
2. [ ] `from launcher.shared.embeddings import EmbeddingClient, EmbeddingIndex` succeeds
3. [ ] All unit tests pass under PYTHONHASHSEED=0
4. [ ] map_evidence.py imports resolve without error
5. [ ] EmbeddingEndpoint field is optional and backward-compatible

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: import resolution PASS
- [ ] Evidence captured: reports/agents/embeddings/TC-3774/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_embeddings.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_map_evidence.py -v
```

**Expected results**:
- All embeddings unit tests PASS
- map_evidence tests still PASS (imports now resolve)

## Integration boundary proven

**Upstream**: v1 embeddings.py (ported), jaccard.py STOPWORDS, http.py http_post
**Downstream**: map_evidence.py (4 import sites), extract.py Phase B.4 (TC-3775)
**Contract**: `tokenize(str) -> list[str]`, `precompute_token_cache(str) -> tuple | None`, `EmbeddingIndex` with save/load/similarity
