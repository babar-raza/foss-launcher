# TC-3721 Implementation Report
## W2 Evidence Quality Scoring + Hybrid Publishability Assessment

**Date**: 2026-03-04
**Agent**: agent_d2
**Taskcard**: TC-3721
**Status**: Complete

---

## Implementation Summary

TC-3721 adds two orthogonal capabilities to the W2 FactsBuilder worker:

1. **Evidence Richness Scoring** — deterministic 0.0–1.0 score per claim based on structural factors
2. **Hybrid Publishability Assessment** — C2-compliant denylist-first pipeline with optional LLM second-pass

---

## Files Modified

### `src/launch/workers/w2_facts_builder/extract_claims.py`

Added after the existing `_cluster_claims_by_topic` sentinel (end of file):

- `_PUBLISHABILITY_DENYLIST_TERMS` — `frozenset` of 30 spec/internal terms synced from `gate_spec_leakage.py _SPEC_LEAK_PATTERNS`
- `_denylist_publishable(claim_text: str) -> bool` — returns False if any denylist term found (C2 constraint: always runs first)
- `_score_evidence_richness(claim: dict) -> float` — 0.05 base + up to 0.65 from source_file, example kind, specificity, user-facing visibility; capped at 1.0
- `_batch_llm_publishability(claims, llm_client, batch_size=20) -> dict` — groups claims into batches, calls LLM with `temperature=0` (C6 compliance), parses JSON response, skips failed batches gracefully

### `src/launch/workers/w2_facts_builder/worker.py`

- **Import block updated**: Added `_denylist_publishable`, `_score_evidence_richness`, `_batch_llm_publishability`, `_is_spec_fragment` to the `from .extract_claims import` block
- **`_apply_quality_scoring()` helper added** (after `logger = get_logger()`): Orchestrates the full hybrid pipeline: score richness, run denylist, optionally call LLM, apply fallback regex, write `evidence_richness` and `publishable` fields to claims in-place
- **Wired into `execute_synthesis_phase()`**: Before `atomic_write_json(output_path, product_facts)`, calls `_apply_quality_scoring(product_facts.get("claims", []), ...)` wrapped in try/except (non-fatal)
- **Wired into `execute_facts_builder()`**: Same pattern — scoring applied before the second `atomic_write_json` in the main orchestrator path

---

## C2 Constraint Enforcement

The C2 constraint (denylist always wins) is enforced at line level in `_apply_quality_scoring`:

```python
if not denylist_ok:
    claim["publishable"] = False          # denylist blocked — LLM is NEVER consulted
elif cid in llm_publishable_results:
    claim["publishable"] = bool(...)      # LLM decides only for denylist-pass claims
elif fallback_to_regex:
    claim["publishable"] = not _is_spec_fragment(...)  # regex fallback
else:
    claim["publishable"] = True           # default
```

The LLM call is skipped entirely for denylist-rejected claims:
```python
denylist_pass_claims = [c for c in claims if denylist_results.get(..., False)]
if denylist_pass_claims and llm_client is not None:
    llm_publishable_results = _batch_llm_publishability(denylist_pass_claims, ...)
```

---

## Test Results

### TC-3721 Tests
```
tests/unit/workers/w2_facts_builder/test_tc3721_quality_scoring.py
20 passed, 0 failed in 1.35s
```

All 20 tests pass (12 required + 8 additional validation tests).

### Full Test Suite
```
Baseline (before TC-3721): 8596 passed, 13 failed (pre-existing), 13 skipped, 3 xfailed
After TC-3721:             8616 passed, 13 failed (same pre-existing), 13 skipped, 3 xfailed
Net new:                   +20 tests
```

Pre-existing failures (confirmed not caused by TC-3721 — fail on baseline too):
- `test_atomic_taskcard.py::test_write_to_protected_path_with_valid_taskcard` — looks for TC-100 in worktree
- `test_run_loop_taskcard.py::test_run_with_valid_taskcard_emits_event` — taskcard lookup in worktree
- `test_taskcard_loader.py` (5 tests) — taskcard file lookup in worktree
- `test_gate_fixtures.py` (4 tests) — fixture files not in worktree
- `test_validation_engine_golden.py::test_fixture_files_present` — fixture missing in worktree

---

## Test Coverage Map

| Test | Function under test | Assertion |
|------|---------------------|-----------|
| `test_denylist_rejects_jcid_term` | `_denylist_publishable` | JCID → False |
| `test_denylist_rejects_rgindices` | `_denylist_publishable` | rgIndices → False |
| `test_denylist_passes_clean_claim` | `_denylist_publishable` | clean claim → True |
| `test_denylist_rejects_ms_onestore` | `_denylist_publishable` | MS-ONESTORE → False |
| `test_denylist_rejects_little_endian` | `_denylist_publishable` | little-endian → False |
| `test_denylist_case_insensitive` | `_denylist_publishable` | ooxml (lower) → False |
| `test_richness_score_with_source_file` | `_score_evidence_richness` | source_file → score >= 0.35 |
| `test_richness_score_example_kind` | `_score_evidence_richness` | claim_kind=example → score >= 0.30 |
| `test_richness_score_minimum_floor` | `_score_evidence_richness` | minimal claim → score == 0.05 |
| `test_richness_score_caps_at_one` | `_score_evidence_richness` | score <= 1.0 |
| `test_richness_score_internal_visibility_no_bonus` | `_score_evidence_richness` | public > internal |
| `test_hybrid_publishable_denylist_blocks_llm` | `_apply_quality_scoring` | JCID claim → publishable=False |
| `test_hybrid_publishable_llm_decides_on_pass` | `_apply_quality_scoring` | LLM True → publishable=True |
| `test_fallback_to_regex_when_llm_unavailable` | `_apply_quality_scoring` | no LLM → regex fallback |
| `test_batch_llm_publishability_groups_claims` | `_batch_llm_publishability` | 25 claims/batch_size=20 → 2 calls |
| `test_batch_llm_empty_claims_returns_empty` | `_batch_llm_publishability` | empty → no LLM call |
| `test_worker_adds_richness_to_claims` | `_apply_quality_scoring` | all claims have evidence_richness |
| `test_worker_adds_publishable_to_claims` | `_apply_quality_scoring` | all claims have publishable (bool) |
| `test_worker_empty_claims_no_error` | `_apply_quality_scoring` | empty list → no error, no LLM call |
| `test_worker_no_llm_uses_fallback` | `_apply_quality_scoring` | None LLM → regex fallback applied |
