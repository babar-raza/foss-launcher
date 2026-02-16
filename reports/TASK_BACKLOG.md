# Task Backlog — Round 11 LLM-Powered Content Quality Hardening

**Updated**: 2026-02-14T23:35:00Z

## Workstream Breakdown

### Phase 0: Quick Wins (Independent) — 2 TCs
| ID | Scope | Owner | Status | Tests |
|----|-------|-------|--------|-------|
| TC-1650 | Strip visible claim markers → HTML comments | Agent-B | Pending | 5+ tests (W5, W7, existing test updates) |
| TC-1651 | Fix raw data structure leakage in comprehensive guide | Agent-B | Pending | 1 new test |

**Phase Goal**: Eliminate BLOCKER-2 (visible claim markers) and BLOCKER-6 (raw dicts in prose)

### Phase 2: LLM Infrastructure (Foundation) — 2 TCs
| ID | Scope | Owner | Status | Tests |
|----|-------|-------|--------|-------|
| TC-1658 | W5 LLM integration layer (3 helper functions) | Agent-B | Pending | 4 new tests |
| TC-1659 | Prompt templates for specialized generators (6 files) | Agent-B | Pending | Prompt loading tests |

**Phase Goal**: Build shared LLM infrastructure for all enhanced generators

**Dependencies**: None (can run in parallel with Phase 0)

### Phase 1: LLM-Enhanced Specialized Generators — 6 TCs
| ID | Scope | Owner | Status | Tests |
|----|-------|-------|--------|-------|
| TC-1652 | LLM-enhanced comprehensive guide generator | Agent-B | Pending | 2 new tests |
| TC-1653 | LLM-enhanced troubleshooting generator | Agent-B | Pending | 2 new tests |
| TC-1654 | LLM-enhanced FAQ generator | Agent-B | Pending | 2 new tests |
| TC-1655 | LLM-enhanced best practices generator | Agent-B | Pending | 2 new tests |
| TC-1656 | LLM-enhanced tutorial generator | Agent-B | Pending | 2 new tests |
| TC-1657 | LLM-enhanced feature showcase generator | Agent-B | Pending | 2 new tests |

**Phase Goal**: Transform W5 specialized generators from deterministic claim-wrappers to LLM-powered content generators

**Dependencies**: Phase 2 (TC-1658, TC-1659) must complete first — generators use LLM integration layer + prompts

**Impact**:
- TC-1652: Eliminates BLOCKER-1 ("Refer to repository") + BLOCKER-4 (empty workflows)
- TC-1653: Eliminates BLOCKER-3 (0 real solutions)
- TC-1654: Lifts FAQ from C/B to A quality
- TC-1655: Eliminates BLOCKER-5 for best practices
- TC-1656: Eliminates BLOCKER-5 for tutorials + BLOCKER-7 (no code examples)
- TC-1657: Eliminates thin feature showcase pages

### Phase 3: Truncation & Post-Processing Fixes — 3 TCs
| ID | Scope | Owner | Status | Tests |
|----|-------|-------|--------|-------|
| TC-1660 | Replace hard truncation with LLM summarization | Agent-B | Pending | 2 new tests |
| TC-1661 | Fix _first_sentence_bullets post-processor | Agent-B | Pending | 1 new test |
| TC-1662 | Fix broken code fences and orphaned blocks | Agent-B | Pending | 2 new tests |

**Phase Goal**: Eliminate truncation artifacts ("...") and broken code fences

**Dependencies**: None (can run in parallel with Phases 0-2)

**Impact**: Eliminates BLOCKER-5 (truncated sentences), fixes SERIOUS-9 (broken code fences)

### Phase 4: W5 Integration — 2 TCs
| ID | Scope | Owner | Status | Tests |
|----|-------|-------|--------|-------|
| TC-1663 | Thread LLM client through W5 specialized generators | Agent-B | Pending | 2 new tests |
| TC-1664 | Use enriched_text in LLM prompts (line 2771 fix) | Agent-B | Pending | 1 new test |

**Phase Goal**: Wire LLM enhancements into W5 run() pipeline

**Dependencies**: Phase 1 (TC-1652–TC-1657) + Phase 2 (TC-1658, TC-1659) must complete first

**Impact**: Production runs get LLM-enhanced content; backward compat maintained (deterministic fallback when llm_client unavailable)

### Phase 5: Validation Alignment — 2 TCs
| ID | Scope | Owner | Status | Tests |
|----|-------|-------|--------|-------|
| TC-1665 | Update W7 gate_14 for HTML comment claim markers | Agent-B | Pending | 2 new tests |
| TC-1666 | W5.5 ContentReviewer skip claim marker checks on HTML comments | Agent-B | Pending | 1 new test |

**Phase Goal**: Update W7/W5.5 validators to recognize HTML comment claim markers

**Dependencies**: Phase 0 (TC-1650) must complete first — claim markers converted to HTML comments

### Phase 6: VFV & Publication Readiness
| Activity | Scope | Owner | Status |
|----------|-------|-------|--------|
| Test suite | Full pytest run (expect 3,380+ tests) | Agent-B | Pending |
| 3D pilot E2E | Generate all pages with LLM enabled | Agent-B | Pending |
| Note pilot E2E | Generate all pages with LLM enabled | Agent-B | Pending |
| Manual content audit | Review all 45 pages against 9 blockers | Agent-B | Pending |
| Zero-blocker verification | Systematic check of success criteria | Agent-B | Pending |

**Dependencies**: All Phases 0-5 must complete

---

## Acceptance Criteria (Cross-Workstream)

- [ ] All 3,380+ tests pass (3,338 baseline + ~42 new tests)
- [ ] Both pilots complete end-to-end with exit code 0
- [ ] Zero occurrences of "Refer to the repository" in any page
- [ ] Zero visible `[claim:` markers in any page (HTML comments OK)
- [ ] Every troubleshooting entry has substantive solution (>50 words)
- [ ] Every developer-guide workflow has a code example
- [ ] Every tutorial step has working Python code
- [ ] Every page scores ≥3/5 on all quality dimensions (SEO, UX, intent, depth, technical density, examples, human-written feel)
- [ ] Every page has substantive content (>200 words for non-index pages)
- [ ] Zero broken code fences
- [ ] Zero raw data structures in prose
- [ ] Zero truncated sentences ending with "..."

---

## Dependency Graph

```
Phase 0 (TC-1650, TC-1651)           ────────────────────┐
                                                          │
Phase 2 (TC-1658, TC-1659)           ────────────────────┤
                                                          ├──> Phase 4 (TC-1663, TC-1664) ──> Phase 5 (TC-1665, TC-1666) ──> Phase 6 (VFV)
Phase 1 (TC-1652–TC-1657)            ────────────────────┤
    (depends on Phase 2)                                  │
                                                          │
Phase 3 (TC-1660–TC-1662)            ────────────────────┘
```

**Execution Strategy**:
1. **Parallel wave 1**: Phase 0, Phase 2, Phase 3 (all independent)
2. **Sequential**: Phase 1 (depends on Phase 2 complete)
3. **Sequential**: Phase 4 (depends on Phase 1 + Phase 2 complete)
4. **Sequential**: Phase 5 (depends on Phase 0 complete)
5. **Final**: Phase 6 VFV (depends on all phases)

**Optimal Agent Allocation**:
- Agent-B: All phases (single agent ensures consistency across W5 codebase)
- Potential parallelization: Could split Phase 1's 6 TCs across multiple agents, but TC-1652/TC-1653 are highest priority

---

## Execution Order (Recommended)

### Wave 1 (Parallel — Foundation)
1. **TC-1658** (LLM integration layer) — Foundation for all enhanced generators
2. **TC-1659** (prompt templates) — Needed by all enhanced generators
3. **TC-1650** (claim marker cleanup) — Quick win, eliminates BLOCKER-2
4. **TC-1651** (data structure leakage) — Quick win, eliminates BLOCKER-6
5. **TC-1660** (smart truncation) — Foundation for quality improvements
6. **TC-1661** (_first_sentence_bullets fix) — Post-processing fix
7. **TC-1662** (code fence fix) — Post-processing fix

### Wave 2 (Sequential — High-Impact Generators)
8. **TC-1652** (comprehensive guide) — Highest impact, eliminates BLOCKER-1 + BLOCKER-4
9. **TC-1653** (troubleshooting) — Eliminates BLOCKER-3

### Wave 3 (Parallel — Remaining Generators)
10. **TC-1654** (FAQ) — Parallel with 11-13
11. **TC-1655** (best practices) — Parallel with 10, 12-13
12. **TC-1656** (tutorial) — Parallel with 10-11, 13
13. **TC-1657** (feature showcase) — Parallel with 10-12

### Wave 4 (Sequential — Integration)
14. **TC-1663** (thread LLM client) — Wires everything together
15. **TC-1664** (enriched_text in prompts) — Critical bug fix

### Wave 5 (Sequential — Validation)
16. **TC-1665** (W7 gate_14 update) — Parallel with 17
17. **TC-1666** (W5.5 ContentReviewer update) — Parallel with 16

### Wave 6 (Final — VFV)
18. Test suite + pilots + manual audit

---

## Critical Files

| File | TCs | LOC Change Estimate |
|------|-----|---------------------|
| `src/launch/workers/w5_section_writer/worker.py` | TC-1650–TC-1664 | ~800 lines |
| `src/launch/workers/w5_section_writer/prompts/*.txt` | TC-1659 | ~300 lines (6 new files) |
| `src/launch/workers/w7_validator/gates/gate_14_content_distribution.py` | TC-1665 | ~10 lines |
| `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py` | TC-1666 | ~10 lines |
| `tests/unit/workers/test_w5_section_writer.py` | All phases | ~300 lines |
| `tests/unit/workers/test_w5_specialized_generators.py` | Phase 1 | ~200 lines (new file) |
| `tests/unit/workers/test_gate_14.py` | TC-1665 | ~30 lines |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM output non-determinism | HIGH | Medium | Use PYTHONHASHSEED=0, seed LLM where possible, accept minor variation |
| LLM generates placeholder text | MEDIUM | High | Validate output length (>100 words), retry with stricter prompt |
| Breaking existing deterministic generators | LOW | High | Backward compat: LLM path only when llm_client provided |
| Test suite regression | LOW | High | Run full suite after each TC, fix immediately |
| HTML comment markers break W7 | MEDIUM | Medium | Update W7 gate_14 regex in same TC as marker change |
| Performance degradation (LLM calls) | MEDIUM | Low | LLM only for specialized generators (~10-15 pages), not all pages |

---

## Evidence Collection Strategy

Each TC must produce:
1. **Code changes**: Git diff showing all modifications
2. **Test results**: pytest output showing new tests passing + zero regressions
3. **Pilot verification**: Specific pages demonstrating fix (e.g., TC-1650: show HTML comments in view-source, no visible markers in rendered view)
4. **Before/after comparison**: Content quality metrics (word count, blocker presence, etc.)

---

## Rollback Plan

If VFV fails (either pilot exits non-zero OR manual audit finds publication blockers):
1. Identify failing TC via git bisect or evidence review
2. Revert TC changes: `git revert <commit-sha>`
3. Determine root cause: LLM prompt issue, code logic bug, or test gap
4. Harden TC: Fix issue, add more tests, re-run pilot
5. Route back through self-review (12D assessment) before re-attempting VFV

---

## Success Definition

**Minimum viable (GO for publication)**:
- All 9 blockers eliminated
- Every page ≥3/5 on all quality dimensions
- Zero test regressions

**Target (A-grade content)**:
- Every page ≥4/5 on all quality dimensions
- Real Python code examples on 90%+ of pages
- Troubleshooting solutions average >100 words (substantive, not generic)
- FAQ answers 3-5 sentences with code snippets
- Developer guide workflows have step-by-step code walkthroughs
