# Plan Sources Resolution — Round 17 Pipeline Quality Improvement

**Generated**: 2026-02-18T17:00:00Z
**Protocol**: Orchestrator Protocol Step 0 (Plan Sources Resolution)

---

## Primary Plan Source

**Path**: `C:\Users\prora\.claude\plans\iridescent-swinging-pumpkin.md`
**Type**: Pipeline Quality Improvement (6 phases, checklisted)
**Status**: EXECUTING

**Why Selected**:
- Addresses critical publication blockers identified in Round 10 VFV manual audit
- W2 produces A-grade content (FAQ: 12/12 Q&A, Best practices: 14/14 actionable, enriched_text: 95% effective)
- W5 SectionWriter is the bottleneck — deterministic claim-wrapper without LLM enhancement
- Contains 17 taskcards (TC-1650 through TC-1666) across 6 phases
- User explicitly approved LLM usage anywhere in pipeline ("more LLM usage may increase all dimensions")
- Transforms W5 from claim-wrapper into LLM-powered content generator

**9 Critical Blockers Identified (NO-GO for publication)**:
1. **BLOCKER-1**: "Refer to repository" placeholder on 10+ pages
2. **BLOCKER-2**: Visible `[claim: hash]` markers in user content
3. **BLOCKER-3**: Troubleshooting pages have 0 real solutions
4. **BLOCKER-4**: Developer guide workflows are empty shells
5. **BLOCKER-5**: Best practices/tutorials truncated mid-sentence with "..."
6. **BLOCKER-6**: Raw Python dicts leaked into prose
7. **BLOCKER-7**: No real code examples (pseudocode or nothing)
8. **SERIOUS**: Thin stub pages (<50 words)
9. **SERIOUS**: Broken code fences

**Key Phases**:
- **Phase 0**: Claim marker cleanup (TC-1650, TC-1651) — Independent quick wins
- **Phase 1**: LLM-enhanced specialized generators (TC-1652–TC-1657) — Core transformation
- **Phase 2**: LLM prompt infrastructure (TC-1658, TC-1659) — Foundation
- **Phase 3**: Truncation & post-processing fixes (TC-1660–TC-1662) — Quality improvements
- **Phase 4**: W5 integration (TC-1663, TC-1664) — Wire everything together
- **Phase 5**: Validation alignment (TC-1665, TC-1666) — Update W7/W5.5
- **Phase 6**: VFV pilots + manual review

---

## ChatExtractedSteps

1. Strip visible `[claim: id]` markers → HTML comments `<!-- claim: id -->`
2. Fix raw data structure leakage in comprehensive guide (dict/list serialization)
3. Add LLM integration layer: `_call_llm_for_content()`, `_build_enriched_claim_context()`, `_inject_claim_markers_as_comments()`
4. Create 6 prompt templates for specialized generators (comprehensive_guide, troubleshooting, faq, best_practices, tutorial, feature_showcase)
5. Enhance `generate_comprehensive_guide_content()` with LLM — eliminate "Refer to repository", generate real workflow sections
6. Enhance `generate_troubleshooting_content()` with LLM — generate real solutions, not generic fallback
7. Enhance `generate_faq_content()` with LLM — expand Q&A to 3-5 sentences with code
8. Enhance `generate_best_practices_content()` with LLM — explain WHY, show DO/DON'T comparisons
9. Enhance `generate_tutorial_content()` with LLM — generate complete working code for each step
10. Enhance `generate_feature_showcase_content()` with LLM — feature deep-dive with code
11. Replace `MAX_CLAIM_TEXT_LENGTH=200` hard-cut with `_smart_truncate()` using LLM summarization
12. Fix `_first_sentence_bullets()` to handle HTML comment claim markers
13. Add `_fix_code_fences()` post-processor for broken fences
14. Thread `llm_client` through all specialized generators from `run()`
15. Update `_build_section_prompt()` line 2771 to use `_get_display_text()` instead of raw claim_text
16. Update W7 gate_14 claim marker regex for HTML comments
17. Update W5.5 ContentReviewer to recognize HTML comment claim markers

## ChatExtractedGapsAndFixes

| Gap | Root Cause | Fix | TC |
|-----|-----------|-----|----|
| "Refer to repository" on 10+ pages | W5 gives up when snippet_catalog empty (lines 1416, 1432, 1639, 1917) | LLM generates illustrative code from claim context | TC-1652–TC-1657 |
| Visible `[claim: hash]` markers | W5/W6 never strips backend metadata | Convert to HTML comments | TC-1650 |
| Troubleshooting: 0 real solutions | W5 line 1917 emits same generic fallback | LLM generates problem-solution with code | TC-1653 |
| Developer guide workflows empty | W5 loops through workflows but only emits 1 sentence + placeholder | LLM generates full workflow sections | TC-1652 |
| Truncated sentences "..." | MAX_CLAIM_TEXT_LENGTH=200 hard-cuts mid-sentence | LLM summarization or sentence-boundary truncation | TC-1660 |
| Raw Python dicts in prose | comprehensive_guide uses repr() for workflow data | Serialize as prose ("Supports OBJ to GLTF") | TC-1651 |
| No real code examples | snippet_catalog sparse → W5 fallback triggers | LLM generates code from claim context | TC-1652–TC-1657 |
| LLM gets un-enriched claims | _build_section_prompt() line 2771 uses raw claim_text | Use _get_display_text() for enriched_text | TC-1664 |

## ChatMentionedFiles

- `src/launch/workers/w5_section_writer/worker.py` (all phases)
- `src/launch/workers/w9_validator/gates/gate_14_content_distribution.py`
- `src/launch/workers/w7_content_reviewer/checks/technical_accuracy.py`
- `src/launch/workers/w5_section_writer/prompts/comprehensive_guide.txt` (new)
- `src/launch/workers/w5_section_writer/prompts/troubleshooting.txt` (new)
- `src/launch/workers/w5_section_writer/prompts/faq.txt` (new)
- `src/launch/workers/w5_section_writer/prompts/best_practices.txt` (new)
- `src/launch/workers/w5_section_writer/prompts/tutorial.txt` (new)
- `src/launch/workers/w5_section_writer/prompts/feature_showcase.txt` (new)
- `tests/unit/workers/test_w5_section_writer.py`
- `tests/unit/workers/test_w5_specialized_generators.py` (new)
- `tests/unit/workers/test_gate_14.py`

## SubstantialityCheck

- >=5 actionable steps: YES (17 steps)
- >=3 concrete gaps with plausible fixes: YES (8 gaps)
- Acceptance criteria + evidence commands: YES
- **Verdict**: SUBSTANTIAL

## ResolutionStrategy

Chat-derived plan already materialized at `C:\Users\prora\.claude\plans\dazzling-hugging-patterson.md`.
Execute via Steps 2-7 of Orchestrator Protocol.

---

## Execution Status

**Current Phase**: Step 0 Complete → Moving to Step 2 (TASK_BACKLOG materialization)
**Baseline**: 3,338 tests passed, 9 skipped, 0 failures (Round 10 complete)
**Target**: Content quality D+ → A (≥3/5 on all dimensions), zero blockers, publication-ready

---

## Evidence Commands

```bash
# Baseline test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x

# 3D pilot verification
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/3d-round11

# Note pilot verification
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output tmp/note-round11

# Manual content quality audit (verify zero blockers)
# Check all .md files in output for:
# - No "Refer to repository" placeholders
# - No visible [claim: markers
# - Every troubleshooting entry has substantive solution (>50 words)
# - Every workflow has code example
# - Every tutorial step has working Python code
```

---

## Secondary Sources

- Round 10 TASK_BACKLOG.md — Shows all 15 TCs complete, new claim_groups wired, 3,338 tests passing
- Manual audit evidence from 3 Explore agents (W2 A-grade, W5 bottleneck, 45 pages reviewed)
- Round 9 evidence — LLM synthesis working but claims not routed to pages (fixed in Round 10)

## MissingCandidates

None — Plan fully specified with 17 TCs, clear phases, execution order, and success criteria.
