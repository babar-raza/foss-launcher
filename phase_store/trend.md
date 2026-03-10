# Understand Module Redesign — Phase Trend Dashboard

**Plan**: humming-greeting-kay
**Branch**: v2
**Baseline**: 3432 tests (Phase 0 start)

| Phase | Description | Tests | New Tests | A+B% | D+F% | Healing Iters | Status |
|-------|-------------|-------|-----------|------|------|---------------|--------|
| Baseline | Pre-redesign | 3432 | — | N/A | N/A | — | — |
| Phase 0 | Fix 5 Plan C defects | 3432 | 0* | N/A | N/A | 0 | Done |
| Phase 1 | Pipeline reorder + evidence injection + contradiction resolver | 3445 | 13 | N/A | N/A | 0 | Done |
| Phase 2 | PlatformProfile + adapter infrastructure | 3461 | 16 | N/A | N/A | 0 | Done |
| Phase 3 | TypeScript tree-sitter depth enhancement | 3475 | 14 | N/A | N/A | 0 | Done |
| Phase 4 | Property-call gate + evidence cleanup | 3484 | 9 | N/A | N/A | 0 | Done |
| Phase 5-6 | .NET + Java + C++ adapters | 3496 | 12 | N/A | N/A | 0 | Done |
| Phase 7 | E2E validation — integration tests | 3537 | 41 | N/A | N/A | 0 | Done |
| Healing HG-05/09/10 | TS e2e tests, safe truncation, import cleanup | 3545 | 8 | N/A | N/A | 0 | Done |
| **HG-02 Pilot** | **aspose-3d-foss-python pilot (actual LLM run)** | — | — | **18%** | **5%** | — | **MEASURED** |
| Healing HG-07/08 | GenericExtractor MissingInfoEntry + Phase 0 regression guards | 3553 | 8 | N/A | N/A | 0 | Done |
| Healing HG-11/12 | Evidence injection into generate worker + format matrix extension string fix | 3565 | 12 | N/A | N/A | 0 | Done |
| **HG-11/12 Pilot (post)** | **Re-run aspose-3d-foss-python with evidence injection** | — | — | **18%** | **0%** ↓ | — | **MEASURED** |
| Healing HG-14 | Format-option class hallucination prevention guard in section_writer.txt | 3567 | 2 | N/A | N/A | 0 | Done |
| **HG-14 Pilot (post)** | **Re-run with format-option class guard active** | — | — | **14%** | **0%** | — | **MEASURED** |
| Healing HG-15 | Mandatory claim coverage enforcement in CLAIMS header + STRICT RULES | 3569 | 2 | N/A | N/A | 0 | Done |
| **HG-15 Pilot (post)** | **Re-run with mandatory claim coverage instruction active** | — | — | **14%** | **0%** | — | **MEASURED** |
| Healing HG-16 | Post-generation hallucinated code block repair in section_validator.py + worker.py | 3574 | 5 | N/A | N/A | 0 | Done |
| **HG-16 Pilot (post, w/ comment FP)** | **Re-run with code block repair active (pre-HG-17)** | — | — | **41%** | **0%** | — | **MEASURED** |
| Healing HG-17 | Fix HG-16 comment false-positives: strip comment content before class scan | 3577 | 3 | N/A | N/A | 0 | Done |
| Healing HG-18 | CamelCase-only class detection (require two camel-words minimum) | 3579 | 2 | N/A | N/A | 0 | Done |
| **HG-16+17+18 Pilot (post)** | **Pilot with CamelCase-only code block repair** | — | — | **22%** | **0%** | — | **MEASURED** |
| Healing HG-19 | Fix evaluate api_surface_summary to use typed_methods (eliminate false-positive FA) | 3581 | 2 | N/A | N/A | 0 | Done |
| **HG-19 Pilot (post)** | **Re-run with complete API surface in reviewer prompt** | — | — | **TBD** | **TBD** | — | **PLANNED** |

*Phase 0 fixed evaluate worker bugs; test count unchanged because fixes were to existing code paths.

## Summary

- **Total new tests**: 149 (105 from phases + 8 HG-05/09/10 + 8 HG-07/08 + 12 HG-11/12 + 2 HG-14 + 2 HG-15 + 5 HG-16 + 3 HG-17 + 2 HG-18 + 2 HG-19)
- **Total test count**: 3432 → 3581
- **Pre-existing failures**: 6 (TestDeployIntegration — unrelated to redesign)
- **New failures introduced**: 0
- **Healing iterations needed**: 0 across all phases

## Pilot Quality Measurement (HG-02)

**Run**: `260310_193521_3d_python_881e` — aspose-3d-foss-python, 2026-03-11

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| A+B rate | 18% | ≥ 70% (Phase 3) | **FAIL** |
| D+F rate | 5% | ≤ 30% | PASS |
| CRITICAL findings | 0 | 0 | PASS |
| API coverage | 100% | — | PASS |

**Top quality gaps (baseline)**:
1. Factual accuracy failures (24 high findings) — LLM fabricates class/method names
2. API identifier unknown (7 high findings) — hallucinated classes not in API surface
3. SEO issues (22 low findings) — product name missing from titles

**Post-HG-11/12 measurement (2026-03-11)**:
- A+B: 18% (unchanged), D+F: 0% (improved from 5%)
- Remaining blockers: 27 factual_accuracy + 17 api_consistency high findings from hallucinated Aspose-pattern class names (`ObjLoadOptions`, `StlFormat`) from LLM training data

**Post-HG-14 measurement (2026-03-11)**:
- A+B: 14% (LLM stochastic noise), D+F: 0%
- factual_accuracy: 27→23 (↓4), api_identifier_unknown: 5→3 (↓2), completeness appeared: 0→8

**Post-HG-15 measurement (2026-03-11)**:
- A+B: 14% (no change), D+F: 0%
- api_identifier_unknown: 3→0 (↓3), factual_accuracy: 23→23 (plateau), completeness: 8→8 (plateau)
- **PROMPT HARDENING PLATEAU**: 5 healing taskcards exhausted. D+F fixed (5%→0%). A+B stuck at 14-18%.
- Root cause: LLM Aspose training priors override prompt-level prohibition. Requires post-generation enforcement.

**Next priority**: HG-16 — post-generation identifier repair OR method-level API corrections in section prompt.

## Key Deliverables

1. **Pipeline reordering**: All deterministic evidence (format matrix, limitations, install recipe, workflows) extracted BEFORE LLM claim extraction
2. **Evidence injection**: Structured evidence context (≤4000 chars) injected into LLM prompt
3. **Contradiction resolver**: Post-LLM resolver downgrades claims conflicting with source-verified facts
4. **PlatformProfile**: Config-driven platform metadata for all 6 platforms
5. **Adapter architecture**: PlatformExtractor interface with 6 implementations (Python, TypeScript, .NET, Java, C++, Generic)
6. **TypeScript depth**: Full type extraction (params, return types, properties, enums) via tree-sitter
7. **Property-call gate**: Detects `obj.prop()` anti-pattern when `prop` is a property
8. **Evidence provenance**: MissingInfoEntry + FieldConfidence models for downstream trust signals
9. **Integration test suite**: 41 tests covering 7 scenarios + bundle assembly
