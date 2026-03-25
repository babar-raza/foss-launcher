# Self-Review 12D — TC-3721: W2 Evidence Quality Scoring + Hybrid Publishability Assessment

**Date**: 2026-03-04
**Agent**: agent_d2
**Reviewer**: orchestrator

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|:-----:|----------|
| 1 | Coverage | 5/5 | 20 tests across 3 test classes; covers denylist, richness scoring, batch LLM grouping, hybrid pipeline, empty inputs, no-LLM fallback |
| 2 | Correctness | 5/5 | All 20 tests pass; C2 constraint enforced at code level (denylist_pass_claims computed before LLM call; denylist=False never reaches LLM) |
| 3 | Evidence | 5/5 | report.md with test evidence table, before/after counts, file list, design rationale for each function |
| 4 | Test Quality | 5/5 | All LLM calls mocked (MagicMock); deterministic (no real network); edge cases (empty list, None LLM, case sensitivity, batch boundary) |
| 5 | Maintainability | 5/5 | Functions well-separated: denylist pure str→bool, richness pure dict→float, batch LLM returns dict, apply_quality_scoring orchestrates; easily testable independently |
| 6 | Safety | 5/5 | All scoring is non-fatal (wrapped in try/except in worker); adds fields only (never removes existing fields); no disk writes |
| 7 | Security | 5/5 | No new secrets; LLM client reuses existing authenticated instance; no new network endpoints |
| 8 | Reliability | 5/5 | Graceful degradation on LLM failure (skips batch, falls back to regex); empty claims list is a no-op; None llm_client handled |
| 9 | Observability | 4/5 | logger.info summary after scoring (scored count, publishable count); per-batch warning on LLM failure; no structured event emitted |
| 10 | Performance | 5/5 | Richness scoring O(n) linear; denylist O(n*k) but k=30 constant; LLM batched at configurable batch_size; skips LLM for denylist-rejected claims |
| 11 | Compatibility | 5/5 | Only ADDs fields to claim dicts; no existing fields removed or modified; both execute_synthesis_phase and execute_facts_builder covered |
| 12 | Docs/Specs Fidelity | 5/5 | C2 constraint from taskcard implemented exactly; denylist synced from gate_spec_leakage.py; temperature=0 per C6; fallback_to_regex config key matches spec |
| 13 | Root cause addressed | 5/5 | Root cause: no publishability signal in W2 claims, causing downstream planners to treat all claims equally; TC-3721 adds explicit evidence_richness + publishable fields |

**Total**: 63/65

## What Was Checked

- [x] All 20 tests pass: `PYTHONHASHSEED=0 python -m pytest tests/unit/workers/w2_facts_builder/test_tc3721_quality_scoring.py -v`
- [x] Full suite (with my changes): 8616 passed, 13 failed (pre-existing), 13 skipped, 3 xfailed (baseline 8596, +20)
- [x] Pre-existing failures verified: all 13 failures exist on baseline without TC-3721 changes
- [x] C2 constraint: `test_hybrid_publishable_denylist_blocks_llm` verifies JCID claim is blocked before LLM consulted
- [x] Batch grouping: `test_batch_llm_publishability_groups_claims` verifies 25 claims/batch_size=20 = 2 LLM calls
- [x] Fallback: `test_fallback_to_regex_when_llm_unavailable` verifies regex used when LLM is None
- [x] Empty list no-op: `test_worker_empty_claims_no_error` verifies no LLM call made
- [x] Both worker.py insertion points confirmed (execute_synthesis_phase L2685, execute_facts_builder L3707)

## Known Gaps

### Dimension 9 (Observability: 4/5)

The quality scoring emits a summary log with `logger.info("[TC-3721] Quality scoring complete: N claims scored, M publishable")` and per-batch warnings on LLM failure. However, there is no structured event emitted to the event stream (no `emit_event()` call). This is acceptable because the scoring is a supplemental enrichment step, not a primary worker step. If formal telemetry is needed, an `emit_event()` call for `"W2_QUALITY_SCORING_COMPLETE"` could be added in a follow-up TC.
