# Task Backlog — Round 17 Pipeline Quality Improvement

**Updated**: 2026-02-18T17:00:00Z
**Plan Source**: `C:\Users\prora\.claude\plans\iridescent-swinging-pumpkin.md`
**Diagnosis**: `FLAWED.md` (repo root)

---

## Workstream Breakdown

### Phase 1: Fix and Enable Multi-Pass Generation — TC-2350

| Field | Value |
|-------|-------|
| Owner | Agent-B (Implementation) |
| Status | **IN PROGRESS** |
| Priority | P0 — Highest leverage; entire 3-pass orchestrator already implemented |
| Files | `multi_pass.py`, `rich_context.py`, `ruleset.v1.yaml` |
| Tests | Existing W5 tests + 1 new multi-pass integration test |
| Bug 1 | `llm_client.generate()` → `llm_client.chat_completion()` (3 call sites) |
| Bug 2 | Claim marker regex `[claim:\s*\w+]` → `<!-- claim: -->` (4 locations) |
| Acceptance | Both pilots pass exit 0 with multi-pass enabled; W7 failures ≤ baseline |

### Phase 2: Citation Excerpts in W2 — TC-2351

| Field | Value |
|-------|-------|
| Owner | Agent-B |
| Status | Pending |
| Priority | P1 — Gives LLM real source content instead of file paths |
| Files | `extract_claims.py`, `content_generators.py`, `product_facts.schema.json` |
| Tests | 2 new tests (excerpt extraction + context builder) |
| Acceptance | Claims in `product_facts.json` have `citation_excerpt` populated |

### Phase 3: Pre-Generation Sufficiency Check — TC-2352

| Field | Value |
|-------|-------|
| Owner | Agent-B |
| Status | Pending |
| Priority | P1 — Prevents thin content from being generated |
| Files | New `context_validator.py`, `worker.py` (generate_section_content) |
| Tests | 4 new tests (threshold checks per role) |
| Acceptance | `draft_manifest.json` includes `context_sufficiency` report |

### Phase 4: Acceptance Criteria with Re-Prompt — TC-2353

| Field | Value |
|-------|-------|
| Owner | Agent-B |
| Status | Pending |
| Priority | P1 — Validates structural completeness before accepting |
| Files | `content_generators.py` or `context_validator.py`, `worker.py` |
| Tests | 2 new tests (retry succeeds, retry exhausted) |
| Acceptance | Tutorial pages always have Prerequisites/Steps/Example |

### Phase 5: Sanitizer Instrumentation — TC-2354

| Field | Value |
|-------|-------|
| Owner | Agent-E (Observability) |
| Status | Pending (blocked on Phases 1-4) |
| Priority | P2 — Measure → reduce after upstream fixes |
| Files | `content_sanitizer.py`, `worker.py` |
| Tests | 1 new test (metrics recording) |
| Acceptance | `sanitizer_metrics.json` produced; zero-fire transforms annotated |

---

## Dependency Graph

```
Phase 1 (TC-2350 multi-pass) ──────────────────┐
Phase 2 (TC-2351 excerpts)   ──────────────────┤
Phase 3 (TC-2352 sufficiency)──────────────────┼──> Phase 5 (TC-2354 sanitizer audit)
Phase 4 (TC-2353 acceptance) ──────────────────┘         │
                                                          ▼
                                                    Final Pilots
```

Phases 1-4 are independent and can run in parallel. Phase 5 runs after all four.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Sanitizer transforms fired / page | ≤ 15 |
| W7 gate failures / page | ≤ 3 |
| W5.5 avg score / dimension | ≥ 4.0 |
| Pages triggering quality floor | < 10% |
| Claim citation rate | ≥ 70% |
| Tutorial pages with all required sections | 100% |

---

## Critical Files (Cross-Phase)

| File | TCs |
|------|-----|
| `src/launch/workers/w5_section_writer/multi_pass.py` | TC-2350 |
| `src/launch/workers/w5_section_writer/rich_context.py` | TC-2350 |
| `src/launch/workers/w5_section_writer/worker.py` | TC-2350, TC-2352, TC-2353 |
| `src/launch/workers/w5_section_writer/generators/content_generators.py` | TC-2351, TC-2353 |
| `src/launch/workers/w2_facts_builder/extract_claims.py` | TC-2351 |
| `src/launch/workers/_shared/content_sanitizer.py` | TC-2354 |
| `specs/rulesets/ruleset.v1.yaml` | TC-2350 |
| `tests/unit/workers/test_tc_440_section_writer.py` | TC-2350, TC-2353 |

---

## Previous Round (Round 11) Summary

Round 11 added LLM-enhanced specialized generators (TC-1650–TC-1666), which was a
foundational improvement. However, the system still suffers from the 6 root causes
identified in FLAWED.md. The current round addresses the upstream causes that Round 11's
downstream enhancements could not fix.
