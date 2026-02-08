# TC-1045 Evidence Bundle: Implement LLM Claim Enrichment

**Agent**: Agent-B
**Taskcard**: TC-1045
**Status**: Complete
**Date**: 2026-02-07
**Spec Reference**: specs/08_semantic_claim_enrichment.md

---

## 1. Files Created/Modified

### Created
- `src/launch/workers/w2_facts_builder/enrich_claims.py` (NEW - 480 lines)
- `tests/unit/workers/test_w2_claim_enrichment.py` (NEW - 46 tests)

### Modified
- `src/launch/workers/w2_facts_builder/worker.py` (added enrichment integration between TC-411 and TC-412)

---

## 2. Acceptance Criteria Evidence

### 2.1 All 5 enrichment metadata fields implemented
- `audience_level` (beginner/intermediate/advanced) - Lines 235-240 in enrich_claims.py
- `complexity` (simple/medium/complex) - Lines 241-243 in enrich_claims.py
- `prerequisites` (claim_id array) - Line 244 in enrich_claims.py
- `use_cases` (string array) - Line 245 in enrich_claims.py
- `target_persona` (string) - Line 246 in enrich_claims.py

### 2.2 Offline heuristics produce valid metadata (no nulls, schema-compliant)
- `test_no_null_values` verifies all fields are non-null
- `test_original_claims_not_mutated` verifies input immutability
- Keyword-based audience_level: BEGINNER_KEYWORDS and ADVANCED_KEYWORDS
- Length-based complexity: <50 simple, >150 complex, else medium
- Empty arrays for prerequisites and use_cases
- "{product_name} developers" for target_persona

### 2.3 Cache key includes all 5 components
- `compute_cache_key()` uses: repo_url, repo_sha, prompt_hash[:16], llm_model, schema_version
- Matches spec 08 section 5.1 exactly
- 7 tests verify cache key behavior (determinism, component sensitivity)

### 2.4 Batch size is 20 claims per LLM call
- DEFAULT_BATCH_SIZE = 20 (constant)
- `enrich_claims_batch()` slices claims in batches of batch_size
- `test_batch_processes_all_claims` verifies 25 claims processed correctly

### 2.5 Hard limit enforced at 1000 claims with prioritization
- DEFAULT_MAX_CLAIMS = 1000 (constant)
- `_apply_hard_limit()` sorts by claim_kind priority then claim_id
- Priority order: feature > api > workflow > format > limitation > compatibility
- `test_claims_over_limit_truncated` verifies truncation

### 2.6 Budget alert emitted at $0.15 threshold
- DEFAULT_BUDGET_ALERT_THRESHOLD = 0.15
- Warning logged when estimate_cost() > threshold
- Cost formula: (claim_count * 100/1000) * 0.003 + (claim_count * 50/1000) * 0.015

### 2.7 Skip enrichment for <10 claims (use heuristics)
- MIN_CLAIMS_FOR_LLM = 10
- `test_few_claims_use_heuristics` verifies LLM not called for 5 claims
- Falls through to offline heuristics

### 2.8 Temperature=0.0 for deterministic LLM output
- `_enrich_batch_via_llm()` passes temperature=0.0 to chat_completion
- `test_llm_uses_temperature_zero` verifies the parameter

### 2.9 All claim lists sorted by claim_id
- `enrich_claims_batch()` always returns sorted(enriched, key=lambda c: c["claim_id"])
- `test_output_sorted_by_claim_id` verifies ordering
- `test_same_input_same_output` verifies determinism

### 2.10 Integration into worker.py between TC-411 and TC-412
- Enrichment step inserted at worker.py between TC-411 completion and TC-412 start
- Reads claims from extracted_claims dict
- Calls enrich_claims_batch() with appropriate args
- Re-writes extracted_claims.json with enriched fields
- Emits FACTS_BUILDER_STEP_STARTED/COMPLETED telemetry events
- Failure handling: catches all exceptions, logs, continues W2 (per spec 08 section 9.4)

---

## 3. Test Results

```
tests/unit/workers/test_w2_claim_enrichment.py: 46 passed
tests/unit/workers/test_tc_411_extract_claims.py: 42 passed
tests/unit/workers/test_tc_412_map_evidence.py: 38 passed
Full worker test suite: 1259 passed
```

No regressions detected.

### Test Coverage by Category

| Category | Tests | Spec Section |
|---|---|---|
| Offline heuristics | 11 | 6.2-6.7 |
| Cache key computation | 7 | 5.1 |
| Cost estimation | 4 | 7.3 |
| Prompt template | 4 | 4.1-4.2 |
| Batch processing | 2 | 3.2 |
| LLM enrichment (mocked) | 2 | 3.1-3.3 |
| Cache behavior | 3 | 5.2-5.3 |
| Hard limit enforcement | 3 | 7.2 |
| Skip behavior (<10) | 1 | 7.4 |
| Deterministic output | 2 | 8.1-8.3 |
| Error handling | 2 | 9.4 |
| Cache I/O | 3 | 5.2-5.3 |
| Internal helpers | 2 | 6.2-6.3 |
| **Total** | **46** | |

---

## 4. Spec Compliance Matrix

| Spec Section | Requirement | Status |
|---|---|---|
| 2.1-2.2 | Enrichment schema (5 fields) | Implemented |
| 2.3 | Backward compatibility (all OPTIONAL) | Implemented |
| 3.1 | Execution trigger (after TC-411, before TC-412) | Implemented |
| 3.2 | Batch processing (20/call) | Implemented |
| 3.3 | LLM config (temperature=0.0, max_tokens=4096) | Implemented |
| 3.4 | Skip conditions (offline, <10, AG-002) | Implemented |
| 4.1 | System prompt | Implemented |
| 4.2 | User prompt template | Implemented |
| 4.3 | Prompt versioning (hash in cache key) | Implemented |
| 5.1 | Cache key computation | Implemented |
| 5.2 | Cache location ({RUN_DIR}/cache/enriched_claims/) | Implemented |
| 5.3 | Cache validation (schema, claim IDs) | Implemented |
| 6.1-6.7 | Offline fallback heuristics | Implemented |
| 7.1 | Batch size (20 configurable) | Implemented |
| 7.2 | Hard limit (1000, prioritized) | Implemented |
| 7.3 | Budget alerts ($0.15 threshold) | Implemented |
| 7.4 | Skip for <10 claims | Implemented |
| 8.1 | Temperature=0.0 | Implemented |
| 8.2 | Prompt hashing in cache key | Implemented |
| 8.3 | Sorted output by claim_id | Implemented |
| 8.4 | Schema versioning in cache key | Implemented |
| 9.1-9.4 | W2 integration and failure handling | Implemented |
| 14.1 | Telemetry events (7 event types) | Implemented |
| 14.2 | Log messages (info, warning, error) | Implemented |

---

## 5. Allowed Paths Compliance

All files created/modified are within the taskcard's allowed_paths:
- `src/launch/workers/w2_facts_builder/enrich_claims.py`
- `src/launch/workers/w2_facts_builder/worker.py`
- `tests/unit/workers/test_w2_claim_enrichment.py`
- `reports/agents/agent_b/TC-1045/**`
