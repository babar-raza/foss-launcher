# TC-412 Implementation Report: Map Evidence to Claims

**Agent**: W2_AGENT
**Taskcard**: TC-412 - W2.2 Map claims to evidence in docs and examples
**Date**: 2026-01-28
**Status**: COMPLETE

---

## Executive Summary

Successfully implemented TC-412 evidence mapping worker module that enriches extracted claims with supporting evidence from discovered documentation and example code. The implementation achieves 100% test pass rate (32/32 tests) with deterministic outputs and full spec compliance.

**Key Deliverables**:
- ✅ Worker module: `src/launch/workers/w2_facts_builder/map_evidence.py` (467 lines)
- ✅ Test suite: `tests/unit/workers/test_tc_412_map_evidence.py` (32 tests, 100% pass)
- ✅ Evidence documentation: `reports/agents/W2_AGENT/TC-412/`

---

## Implementation Overview

### Core Algorithm

The evidence mapping algorithm (per specs/03_product_facts_and_evidence.md):

1. **Load Dependencies**: Read extracted_claims.json (TC-411), discovered_docs.json and discovered_examples.json (TC-400)
2. **Score Evidence Relevance**: For each claim, compute relevance scores for all docs/examples using:
   - Source priority (from specs/03:117-128 evidence priority table)
   - Semantic text similarity (Jaccard similarity on word sets)
   - Keyword matching (claim keywords → evidence text)
3. **Filter & Rank**: Apply minimum relevance threshold (0.2 for docs, 0.25 for examples), sort by score descending
4. **Enrich Claims**: Add `supporting_evidence` array and `evidence_count` to each claim
5. **Validate & Write**: Schema-validate against evidence_map.schema.json, deterministically sort by claim_id, atomic write

### Key Features

**Relevance Scoring Algorithm**:
```
final_score = (0.3 × base_priority_score) + (0.4 × similarity) + (0.3 × keyword_match)
```
- Base priority score inverts source_priority (1→1.0, 7→~0.14)
- Similarity uses Jaccard index on word sets
- Keyword matching checks claim keywords in evidence text

**Deterministic Processing**:
- Stable claim sorting by claim_id (lexicographic)
- Stable evidence sorting by relevance_score (descending)
- No timestamps, UUIDs, or non-deterministic hashing
- Compliant with specs/10_determinism_and_caching.md

**Error Handling**:
- Graceful degradation: Claims without evidence still included
- File not found warnings logged but don't block pipeline
- Missing artifacts raise FileNotFoundError with clear messages
- Schema validation catches structural errors early

---

## Test Results

### Test Execution

```bash
pytest tests/unit/workers/test_tc_412_map_evidence.py -v
```

**Result**: 32/32 tests PASSED (100%)

### Test Coverage Breakdown

1. **Text Similarity** (5 tests): Jaccard similarity, case-insensitivity, empty text handling
2. **Keyword Extraction** (3 tests): Stopword filtering, short word filtering, claim kind inclusion
3. **Evidence Scoring** (3 tests): High/low similarity scoring, keyword match weighting
4. **Doc Evidence** (4 tests): Basic discovery, relevance sorting, max limit, threshold filtering
5. **Example Evidence** (2 tests): Basic discovery, relevance sorting
6. **Claim Enrichment** (2 tests): Basic enrichment, evidence sorting
7. **Validation** (4 tests): Valid structure, missing fields, invalid claims type, invalid claim
8. **Deterministic Sorting** (2 tests): Claim sorting, stability across runs
9. **Integration** (7 tests): Basic mapping, with examples, missing artifacts (3 variants), determinism, empty claims

### Critical Test Cases

**Deterministic Output** (test_map_evidence_deterministic_output):
- Runs evidence mapping twice with identical inputs
- Verifies claim_ids in same order
- Verifies evidence_counts identical
- **Status**: PASSED ✅

**Missing Dependencies** (3 tests):
- extracted_claims.json missing → FileNotFoundError
- discovered_docs.json missing → FileNotFoundError
- discovered_examples.json missing → FileNotFoundError
- **Status**: All PASSED ✅

**Empty Input Handling** (test_map_evidence_empty_claims):
- Handles empty claims array gracefully
- Produces valid evidence_map.json with metadata
- **Status**: PASSED ✅

---

## Spec Compliance

### specs/03_product_facts_and_evidence.md

✅ **Evidence Priority Ranking** (lines 117-128):
- Implemented source_priority mapping (1=manifest → 7=readme_marketing)
- Higher priority sources get higher base scores in relevance algorithm
- Reuses source_priority from TC-411 extracted claims

✅ **Evidence Structure** (lines 59-66):
- Claims include claim_id, claim_text, claim_kind, truth_status, citations
- Added supporting_evidence array with relevance scores
- Added evidence_count for quick filtering

### specs/04_claims_compiler_truth_lock.md

✅ **Claim ID Stability** (lines 12-19):
- Preserves claim_id from TC-411 (SHA256 of normalized text + kind)
- No modification to existing claim structure
- Only enriches with additional evidence fields

### specs/21_worker_contracts.md (W2 FactsBuilder)

✅ **Input Artifacts** (lines 101-104):
- Reads repo_inventory.json (from TC-400)
- Reads extracted_claims.json (from TC-411)
- Reads discovered_docs.json and discovered_examples.json (from TC-400)

✅ **Output Artifacts** (lines 106-108):
- Writes evidence_map.json (schema-validated)
- Includes schema_version, repo_url, repo_sha, claims, contradictions
- Metadata includes total_claims, claims_with_evidence, average_evidence_per_claim

✅ **Stable Claim IDs** (lines 111-112):
- Preserves claim_id from TC-411
- Deterministic sorting by claim_id

### specs/10_determinism_and_caching.md

✅ **Stable Ordering** (lines 39-46):
- Claims sorted by claim_id (lexicographic)
- Evidence sorted by relevance_score (descending), then by path (lexicographic)
- No timestamps in output artifacts

✅ **Deterministic Outputs** (lines 50-52):
- Repeat runs produce identical claim order
- Repeat runs produce identical evidence counts
- Verified by test_map_evidence_deterministic_output

### specs/schemas/evidence_map.schema.json

✅ **Schema Compliance**:
- Required fields: schema_version, repo_url, repo_sha, claims
- Claims array with required fields: claim_id, claim_text, claim_kind, truth_status, citations
- Optional contradictions array (empty in TC-412, populated in future TC)
- Validation implemented in validate_evidence_map_structure()

---

## Artifact Quality

### Generated Artifacts

**evidence_map.json** structure:
```json
{
  "schema_version": "1.0.0",
  "repo_url": "https://github.com/...",
  "repo_sha": "abc123...",
  "claims": [
    {
      "claim_id": "sha256_hash",
      "claim_text": "Supports OBJ format",
      "claim_kind": "format",
      "truth_status": "fact",
      "citations": [...],
      "supporting_evidence": [
        {
          "path": "docs/formats.md",
          "type": "documentation",
          "relevance_score": 0.85,
          "doc_type": "technical"
        },
        {
          "path": "examples/load_obj.py",
          "type": "example",
          "relevance_score": 0.72,
          "language": "python"
        }
      ],
      "evidence_count": 2
    }
  ],
  "contradictions": [],
  "metadata": {
    "total_claims": 10,
    "claims_with_evidence": 8,
    "average_evidence_per_claim": 2.5,
    "total_supporting_evidence": 25
  }
}
```

**Atomic Writes**: Uses atomic_write_json() from IO layer (temp file → rename pattern)

**Determinism**: No timestamps, stable sorting, reproducible outputs

---

## Dependencies

### Consumed Artifacts (from TC-400, TC-411)

✅ **extracted_claims.json** (TC-411):
- Required fields: schema_version, repo_url, repo_sha, claims[]
- Each claim: claim_id, claim_text, claim_kind, truth_status, citations, source_priority

✅ **discovered_docs.json** (TC-400):
- Required fields: schema_version, doc_entrypoint_details[]
- Each doc: path, type

✅ **discovered_examples.json** (TC-400):
- Required fields: schema_version, example_file_details[]
- Each example: path, language

### Provided Artifacts (for downstream workers)

✅ **evidence_map.json**:
- Consumed by TC-500 (snippet curation): Uses supporting_evidence to prioritize examples
- Consumed by TC-600 (page planning): Uses evidence_count to determine claim coverage
- Consumed by TC-700 (writers): Uses citations and supporting_evidence for grounding

---

## Quality Gates

### Gate 0-S (Specs Alignment)

✅ **Full Compliance**:
- All spec references implemented (specs/03, 04, 10, 21)
- Evidence priority ranking per specs/03:117-128
- Deterministic outputs per specs/10
- Worker contract per specs/21:98-125

### Gate 1 (Tests)

✅ **100% Pass Rate**: 32/32 tests passing
✅ **Coverage**: All functions tested (unit + integration)
✅ **Edge Cases**: Empty inputs, missing files, invalid structure
✅ **Determinism**: Verified stable outputs across runs

### Gate 2 (Determinism)

✅ **Stable Ordering**: Claims sorted by claim_id
✅ **No Timestamps**: Metadata excludes time-based fields
✅ **Reproducible**: test_map_evidence_deterministic_output verifies

### Gate 3 (Schema Validation)

✅ **Schema Compliance**: validate_evidence_map_structure() enforces schema
✅ **Required Fields**: All required fields present
✅ **Type Safety**: Claims array, citations array, proper types

---

## Known Limitations & Future Work

### Current Implementation Limitations

1. **Heuristic Similarity**: Uses Jaccard similarity instead of LLM embeddings
   - **Reason**: LLM client optional in TC-412 (semantic similarity deferred to TC-413)
   - **Impact**: May miss semantically similar but lexically different evidence
   - **Mitigation**: Keyword matching compensates for some cases

2. **No Contradiction Detection**: Contradictions array always empty
   - **Reason**: Contradiction detection is TC-413 (separate taskcard)
   - **Impact**: Conflicting claims not automatically resolved
   - **Future**: TC-413 will populate contradictions array

3. **Fixed Relevance Thresholds**: 0.2 for docs, 0.25 for examples
   - **Reason**: No adaptive thresholding in TC-412 scope
   - **Impact**: May filter out some valid low-score evidence
   - **Future**: Could make configurable via run_config

### Future Enhancements (Out of Scope for TC-412)

- **TC-413**: LLM-based semantic similarity using embeddings
- **TC-413**: Contradiction detection and resolution per specs/03:130-183
- **TC-500**: Use supporting_evidence for snippet curation prioritization
- **TC-600**: Use evidence_count for coverage-based page planning

---

## Lessons Learned

1. **Incremental Evidence Enrichment**: TC-411 extracts claims, TC-412 adds evidence mappings, TC-413 adds semantic analysis. Clean separation of concerns.

2. **Determinism from Day 1**: Implementing stable sorting and avoiding timestamps early prevented rework.

3. **Test-First for Edge Cases**: Tests for missing artifacts, empty claims, and file errors caught implementation gaps early.

4. **Schema Validation Early**: validate_evidence_map_structure() catches errors before writing, preventing corrupt artifacts downstream.

5. **Graceful Degradation**: Claims without evidence still included in output (evidence_count=0) allows pipeline to continue.

---

## Conclusion

TC-412 is **COMPLETE** with:
- ✅ Full implementation (467 lines, production-ready)
- ✅ Comprehensive test suite (32 tests, 100% pass)
- ✅ Complete spec compliance (4 specs covered)
- ✅ Deterministic outputs (verified)
- ✅ Schema validation (enforced)
- ✅ Evidence documentation (report + self_review)

**Ready for integration** into W2 FactsBuilder pipeline.

**Next Steps**:
1. Commit implementation to feat/TC-412-map-evidence branch
2. Update STATUS_BOARD with completion timestamp
3. Ready for TC-413 (semantic similarity + contradiction detection)
