---
id: TC-1045
title: "Implement LLM Claim Enrichment (MANDATORY)"
status: In-Progress
priority: P1
agent: Agent-B
depends_on: [TC-1040, TC-1044]
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
allowed_paths:
  - src/launch/workers/w2_facts_builder/enrich_claims.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_w2_claim_enrichment.py
  - reports/agents/agent_b/TC-1045/**
---

# TC-1045: Implement LLM Claim Enrichment (MANDATORY)

## Objective

Create `enrich_claims.py` module in W2 FactsBuilder that enriches claims with semantic metadata (audience_level, complexity, prerequisites, use_cases, target_persona). Implement both LLM-based enrichment with caching AND offline heuristic fallbacks. Integrate into W2 worker pipeline between claim extraction (TC-411) and evidence mapping (TC-412).

## Required spec references

- `specs/08_semantic_claim_enrichment.md` — Full enrichment specification (sections 2-9)
- `specs/03_product_facts_and_evidence.md` — Claims structure, enrichment requirements
- `specs/schemas/evidence_map.schema.json` — Claim enrichment field definitions
- `specs/30_ai_agent_governance.md` — AG-002 approval gate for LLM usage
- `specs/21_worker_contracts.md` — W2 contract with enrichment sub-task

## Scope

### In scope

1. Create `src/launch/workers/w2_facts_builder/enrich_claims.py` with:
   - `enrich_claims_batch()` — batched LLM enrichment (20 claims/call)
   - `add_offline_metadata_fallbacks()` — heuristic fallbacks for offline mode
   - `compute_cache_key()` — deterministic cache key computation
   - `_load_from_cache()` / `_save_to_cache()` — cache read/write
   - `_build_enrichment_prompt()` — prompt template rendering
   - `estimate_cost()` — cost estimation and budget alerts
2. Integrate enrichment into `worker.py` `execute_facts_builder()` between TC-411 and TC-412
3. Create comprehensive unit tests in `tests/unit/workers/test_w2_claim_enrichment.py`
4. Write evidence bundle and self-review

### Out of scope

- Semantic embeddings (TC-1046)
- Actual LLM API calls in tests (all tests use mocks)
- Schema file modifications (already done in TC-1040)
- W5 changes to consume enrichment (separate taskcard)

## Inputs

- `specs/08_semantic_claim_enrichment.md` — Full specification
- `specs/schemas/evidence_map.schema.json` — Schema with enrichment fields
- `src/launch/workers/w2_facts_builder/worker.py` — Integration target
- `src/launch/workers/w2_facts_builder/extract_claims.py` — Claims structure reference
- `src/launch/clients/llm_provider.py` — LLM client interface

## Outputs

- `src/launch/workers/w2_facts_builder/enrich_claims.py` (NEW)
- `src/launch/workers/w2_facts_builder/worker.py` (MODIFIED — add enrichment step)
- `tests/unit/workers/test_w2_claim_enrichment.py` (NEW)
- `reports/agents/agent_b/TC-1045/evidence.md`
- `reports/agents/agent_b/TC-1045/self_review.md`

## Allowed paths

- `src/launch/workers/w2_facts_builder/enrich_claims.py`
- `src/launch/workers/w2_facts_builder/worker.py`
- `tests/unit/workers/test_w2_claim_enrichment.py`
- `reports/agents/agent_b/TC-1045/**`## Implementation steps

1. **Create `enrich_claims.py`** with all functions per spec 08 sections 2-6:
   - `enrich_claims_batch(claims, product_name, llm_client, cache_dir, offline_mode)` → enriched claims
   - `add_offline_metadata_fallbacks(claims, product_name)` → claims with heuristic metadata
   - `compute_cache_key(repo_url, repo_sha, prompt_template, llm_model, schema_version)` → sha256 hex
   - `_build_enrichment_prompt(claims_batch, product_name, platform)` → formatted prompt string
   - `estimate_cost(claim_count, model)` → float cost estimate
   - `_load_from_cache(cache_dir, cache_key)` → Optional[list]
   - `_save_to_cache(cache_dir, cache_key, enriched_claims, metadata)` → None

2. **Offline heuristics** (spec 08 section 6):
   - audience_level: keyword-based (install→beginner, custom→advanced, else→intermediate)
   - complexity: length-based (<50→simple, >150→complex, else→medium)
   - prerequisites: empty array (no dependency analysis)
   - use_cases: empty array (no scenario generation)
   - target_persona: `f"{product_name} developers"`

3. **Cost controls** (spec 08 section 7):
   - Batch size: 20 claims per LLM call
   - Hard limit: 1000 claims max (prioritize key_features > install_steps > others)
   - Budget alert: warn if estimate > $0.15/repo
   - Skip enrichment if < 10 claims (use heuristics instead)

4. **Determinism** (spec 08 section 8):
   - temperature=0.0 for all LLM calls
   - Prompt hash in cache key
   - Sorted output by claim_id
   - Schema version in cache key

5. **Integrate into worker.py**:
   - After TC-411 extract_claims completes, call enrich_claims_batch()
   - Update extracted_claims in-memory before TC-412 evidence mapping reads them
   - Re-write extracted_claims.json with enrichment fields
   - Emit telemetry events per spec 08 section 14

6. **Unit tests** (spec 08 section 10):
   - Test offline heuristics for all metadata fields
   - Test cache key computation stability
   - Test prompt template rendering
   - Test cost estimation accuracy
   - Test batch processing boundaries
   - Test LLM enrichment with mocked client
   - Test cache hit/miss behavior
   - Test hard limit enforcement (>1000 claims)
   - Test skip behavior (<10 claims)
   - Test deterministic output (sorted claims)

## Failure modes

1. **LLM API unavailable**: Detection: ConnectionError, timeout, 401/403. Resolution: Fall back to offline heuristics. Gate: AG-002 approval not required for offline mode.
2. **LLM returns malformed JSON**: Detection: json.JSONDecodeError. Resolution: Log error, retry once, then fall back to offline heuristics for that batch. Gate: Schema validation on LLM output.
3. **Cache file corruption**: Detection: json.JSONDecodeError on cache load, schema mismatch. Resolution: Invalidate cache, re-enrich. Gate: Cache validation per spec 08 section 5.3.
4. **Cost budget exceeded**: Detection: estimate_cost() > $0.15. Resolution: Emit telemetry warning, continue enrichment (soft limit). Gate: Hard limit at 1000 claims.
5. **Claims exceed hard limit**: Detection: len(claims) > 1000. Resolution: Prioritize claims by group, skip remaining, mark with enrichment_skipped flag. Gate: spec 08 section 7.2.

## Task-specific review checklist

1. [ ] All 5 enrichment metadata fields implemented (audience_level, complexity, prerequisites, use_cases, target_persona)
2. [ ] Offline heuristics produce valid metadata (no nulls, schema-compliant)
3. [ ] Cache key includes all 5 components (repo_url, repo_sha, prompt_hash, llm_model, schema_version)
4. [ ] Batch size is 20 claims per LLM call
5. [ ] Hard limit enforced at 1000 claims with prioritization
6. [ ] Budget alert emitted at $0.15 threshold
7. [ ] Skip enrichment for <10 claims (use heuristics)
8. [ ] Temperature=0.0 for deterministic LLM output
9. [ ] All claim lists sorted by claim_id
10. [ ] Integration into worker.py between TC-411 and TC-412

## Deliverables

- `src/launch/workers/w2_facts_builder/enrich_claims.py` — Enrichment module
- `tests/unit/workers/test_w2_claim_enrichment.py` — Unit tests (minimum 15 tests)
- `reports/agents/agent_b/TC-1045/evidence.md` — Evidence bundle
- `reports/agents/agent_b/TC-1045/self_review.md` — 12D self-review

## Acceptance checks

1. All unit tests pass (minimum 15 tests)
2. Offline heuristics produce valid metadata for all 5 fields
3. Cache key is deterministic (same inputs → same key)
4. LLM enrichment works with mocked client
5. Worker integration: enrichment runs between TC-411 and TC-412
6. No regression in existing W2 tests (109+ tests)
7. Cost controls active and tested
8. Deterministic output verified (sorted claims)

## Self-review

Agent MUST perform 12D self-review before routing. Minimum 4/5 on all dimensions.

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract
