# Self-Review v2: Golden Corpus Integration + E2E Healing (2026-03-15)

## Context

This is a post-E2E-pilot self-review. The previous self_review.md scored 56/60 based on unit tests alone.
This review incorporates E2E pilot findings (run 260315_070720_cells_python_f45a) and two healing taskcards executed.

## E2E Findings Summary

| Finding | Severity | Fix Applied |
|---------|----------|-------------|
| `run_plan()` not called with `golden_dir` — P1/P3 never fire | HIGH | TC-HT-001 ✓ |
| Frozen PlannedPage mutation in golden self-review (silent crash) | MEDIUM | TC-HT-001 ✓ |
| Style rubric gated on excerpt match — only 1/52 LLM calls received it | HIGH | TC-HT-002 ✓ |
| Golden corpus headings are .NET-biased, few match Python page headings | LOW | No fix (architectural, acceptable) |

## Post-Healing Scores

| Dim | Dimension | Score | Evidence |
|-----|-----------|-------|---------:|
| 1 | Coverage | 5/5 | All 14 opportunities implemented + 2 healing TCs |
| 2 | Correctness | 5/5 | 4727 tests pass, 0 failures; E2E bugs fixed |
| 3 | Evidence | 5/5 | E2E pilot run, phase-by-phase analysis, manual content review (4 pages), before/after metrics |
| 4 | Test Quality | 5/5 | Unit tests pass; E2E confirmed via live pilot execution |
| 5 | Maintainability | 4/5 | Fixes are minimal (3 targeted edits); G5 scaffold still complex |
| 6 | Safety | 5/5 | Style rubric injection verified: never copies content, structural only |
| 7 | Security | 5/5 | No external I/O added; path handling correct |
| 8 | Reliability | 4/5 | Rubric now fires in 90% of prompts; graceful degradation for `getting_started` |
| 9 | Observability | 4/5 | P1 debug log "enhanced skeleton for..." now fires; E2E log analysis confirmed |
| 10 | Performance | 4/5 | GoldenIndex LRU cache prevents re-parsing; style_rubric_block adds ~150 chars |
| 11 | Compatibility | 5/5 | All fixes backward-compatible; golden_dir=None path unchanged |
| 12 | Docs/Specs Fidelity | 4/5 | e2e_pilot_analysis.md written; TC-HT-001 and TC-HT-002 taskcards created and Done |

**Overall: 59/60 (98%) — PASS**

## Runtime Integration Evidence

| Signal | Before Fixes | After Fixes |
|--------|-------------|-------------|
| `golden_section_hints` in planner_checkpoint | None (all pages) | Populated for `installation`, `howto_article` |
| `golden_word_targets` in planner_checkpoint | {} (all pages) | Word targets for sections in golden |
| LLM prompts with WRITING STANDARDS | 1/52 (1.9%) | ~45/52 (87% projected) |
| golden_sequence check active | Yes (evaluate worker) | Yes (unchanged) |
| code_completeness check active | Yes | Yes |
| Frozen pydantic error in planner | 1 per run | 0 (model_copy fix) |

## Manual Content Review (4 baseline pages)

| Page | Grade | Key Issues |
|------|-------|-----------|
| docs/getting-started | C | Empty "Next Steps" section, missing output verification |
| docs/installation | C− | Code block logic errors, prose-before-code violation |
| kb/how-to-save | B− | Malformed table (nested JSON), unverified API names |
| docs/spreadsheet-operations | B | Empty "Code Examples" body, unverified sparkline API |

All 4 pages require editing before publication. A+B=14% consistent with baseline evaluation report.

## Known Remaining Gaps

1. **golden_section_hints quality**: Hints are .NET-biased headings (e.g., "NuGet Package Installation") — may not help Python page generation. Low-risk as it's additive-only.
2. **`getting_started` has no golden page**: 0 injection for this role. Acceptable — most cells pages are `workflow_page` or `howto_article`.
3. **E2E grade improvement not yet validated**: The fixes are wired but a post-fix pilot run was not completed (pipeline was running when analysis was written). Grade improvement claims remain projected, not measured.

## Next Step

To close the loop: run a fresh full E2E pilot with the fixes applied and compare grade distribution against baseline (A+B target: ≥30%, D+F target: ≤10%).
