# TC-PILOT-300: Final Assessment

## Executive Summary

The Session 10 structural fixes produced **measurable infrastructure improvements** but **did not materially improve content quality**. The pipeline went from "silently producing bad content and calling it good" to "honestly reporting that content is mediocre."

## What Improved (Proven by Pilots)

### 1. Slug/Route Correctness: FIXED
- **Before**: 82% of Cells pages had wrong slugs (18/22 mismatches)
- **After**: 0% mismatches across ALL families
- **Root cause**: `sorted()` in Gemini cache key (gemini_client.py:189)
- **Impact**: Every page now has the correct URL, canonical, and navigation path

### 2. Evaluator Honesty: PARTIALLY IMPROVED (still miscalibrated on D+F)
- **Before**: Evaluator gave 30% A+B to pages a human would grade C/D
- **After (Python families)**: Evaluator gives ~10% A+B, ~85% C, ~5% D+F — closer to human
- **After (.NET)**: Evaluator gives 0% A+B, 6% D+F — **human review finds 67% D+F** (61pp gap)
- **After (Cells human review)**: Evaluator D+F=14%, human D+F=32% — 18pp gap
- **After (3D/Python human review)**: Evaluator D+F=33%, human D+F=43% — 10pp gap
- **Root cause of remaining gap**: The evaluator does not check empty code blocks, `[identifier omitted]` placeholders, or LLM generation failures — only structural/formal properties. Pages with empty-but-valid structure score C when they should score D/F.
- **Impact**: GO/NO-GO gate is more honest than before, but still passes pages that humans would reject.

### 3. D+F Elimination: EVALUATOR SAYS IMPROVED, HUMAN REVIEW CONTRADICTS
- **Evaluator before**: Average 13-21% D+F depending on family
- **Evaluator after**: Best runs achieve 0% D+F (Cells d131, 3D/Python 9986, Note da73)
- **Human review reality**:
  - Note/Python (da73): Evaluator 0% → Human **68%** D+F
  - 3D/.NET (5c10): Evaluator 6% → Human **67%** D+F
  - Cells/Python (163f): Evaluator 14% → Human 32% D+F
- **Root cause**: The evaluator doesn't check for empty code blocks or empty section bodies. A page with `\`\`\`python\n\n\`\`\`` (empty fence) passes all structural checks and scores C. A human reader sees a broken page with no code.
- **Impact**: The evaluator's D+F metric is not reliable. Human D+F is consistently 10-68pp higher than evaluator D+F.

### 4. Run Determinism: IMPROVED
- **Before**: Same config produced wildly different grade distributions
- **After**: Note/Python produced identical grades (21C, 1B) across two independent runs
- **Impact**: Quality is predictable and reproducible

### 5. Platform Portability: PARTIALLY CONFIRMED (with critical .NET defect)
- **3D/TypeScript**: Most dramatic improvement of the sprint — A+B 3%→14% (+11pp), D+F 17%→5% (-12pp). The 3 re-run cycles improved page quality (Prerequisites section in getting-started filled in on cycle 3).
- **3D/.NET**: Pipeline ran to completion without code changes, but human review reveals **67% D+F** vs evaluator's 6%. The `[identifier omitted]` defect affects 61% of pages — C#/.NET identifiers stripped by the Python-only identifier repair step. The pipeline *ran* but the output is not usable.
- **Impact**: Pipeline supports Python and TypeScript to C-grade quality. .NET requires platform adapter completion (Change 5) before it produces usable output.

### 6. Schema Completeness: FIXED
- **Fixed**: evidence_score and golden_word_targets fields added to plan_bundle schema
- **Impact**: Pipeline runs to completion instead of crashing at planner output validation

## What Did NOT Improve

### Content Quality (The Thing That Actually Matters)
Human-grade quality of generated pages is still C-level:

| Defect | Prevalence | Status |
|--------|:----------:|--------|
| Broken table rendering | ~25% | NOT FIXED (generation bug) |
| Backtick pollution | ~40-60% | NOT FIXED (Change 6 not implemented) |
| Empty sections | ~20-40% | NOT FIXED (whole-page gen incomplete) |
| Keyword stuffing | ~15-30% | NOT FIXED (prompt-side issue) |
| Wrong class in metadata | ~15% (reference pages) | NOT FIXED (claim routing issue) |
| Missing code examples (ref pages) | ~100% | NOT FIXED (Change 2 not implemented) |
| Empty code blocks | Cells 32%, Note **64%**, .NET 67% | NOT FIXED — evaluator does NOT detect this |
| `[identifier omitted]` in .NET code | 61% of .NET pages | ROOT CAUSE: C# extractor returns 0 classes; generator hallucinates, repair strips |
| Empty docstrings in class_briefs | **100% of classes in all families** | NOT FIXED — extractor captures signatures but not docstring text |
| C# class extraction | 0 classes from 115 .NET source files | NOT FIXED — no C# analyzer wired into extraction pipeline |
| Grade oscillation in multi-cycle runs | d131: 4.5x tokens, marginal improvement | NOT FIXED — retry loops don't converge; some pages regress |

### What's Needed Next (Priority Order)

1. **Broken table rendering** — The generate worker or section_validator is emitting Python list-of-lists instead of markdown table syntax. This is likely a simple rendering bug.

2. **Backtick pollution fix** (Change 6) — `_backtick_api_names()` in section_validator.py wraps common words in backticks. Needs context-aware matching.

3. **Empty section elimination** — Whole-page generation should prevent empty sections by giving the LLM full page context, but sections like Prerequisites and Next Steps still come out empty.

4. **Reference page code examples** (Change 2) — Reference pages need at least one code example per major operation. Currently they have none.

5. **Platform adapter for .NET/TypeScript** (Change 5) — The `[identifier omitted]` defect makes 61% of .NET pages unusable. `_DOTNET_BUILTINS` and `_TYPESCRIPT_BUILTINS` exempt sets must be added to `_identifier_repair.py`.

6. **Keyword stuffing reduction** — Remove or limit SEO keyword injection in generation prompts.

## Pilot Status Summary

| Pilot | Status | Pages | Best A+B | Best D+F |
|-------|--------|:-----:|:-------:|:-------:|
| Cells/Python | COMPLETE (3 runs) | 22 | 14% | 0% |
| 3D/Python | COMPLETE (2 runs) | 21 | 0% | 0% |
| Note/Python | COMPLETE (2 runs) | 22 | 5% (eval) / 14% (human) | 0% (eval) / **68% (human)** |
| 3D/TypeScript | COMPLETE (1 run, 3 eval cycles) | 21 | 14% | 5% |
| 3D/.NET | COMPLETE (1 run) | 18 | 0% (eval) / 11% (human) | 6% (eval) / **67% (human)** |
| Slides/Python | BLOCKED | 0 | n/a | n/a |

### Slides/Python — Why Blocked
The Understand worker correctly identifies that the Slides FOSS Python repo has no extractable public API surface. The pipeline refuses to generate documentation from nothing — this is the evidence gating (Change 4) working as designed. Fix requires either: (a) the Slides repo adding proper Python package structure, or (b) the AST extractor being enhanced to handle the repo's non-standard layout.

## Verdict

**The infrastructure improvements are real but the evaluator is still not trustworthy.** Human review across 4 families shows the evaluator understates D+F by 10-68pp. The pipeline is producing far more broken content than the evaluator reports.

**Revised priority order for next steps (updated after human review + artifact review):**

1. **Fix docstring extraction** — `_api_surface.py` or `_deterministic.py` is not populating `docstring_snippet` for any family. Cells has rich docstrings in source; they should appear in class_briefs. This is a pipeline bug, not a source quality problem. Without docstrings, the generator fills the void with hallucinations.

2. **Fix C# class extraction** — The .NET run extracted 0 classes from 115 source files. Add a C# AST extractor (or wire the existing adapter) to populate class_briefs for .NET repos. Until this is fixed, .NET output will always have `[identifier omitted]` throughout.

3. **Empty content detection in evaluator** — Empty code blocks and empty section bodies must be CRITICAL findings. Implement `check_empty_code_blocks()` and `check_empty_sections()` in `evaluate/checks/`. This alone would surface the 8 F-grade Note pages and 5 F-grade .NET pages that are currently rated C.

4. **Fix empty code block generation** — 64% of Note pages and 67% of .NET pages have empty code fences. With docstrings fixed (#1), evidence should improve. Also investigate whether the fallback path or whole-page generation is silently omitting code sections.

5. **Broken table rendering** — Python list-of-lists instead of markdown tables across 15-25% of pages per family.

6. **Backtick pollution fix** (Change 6) — 100% of 3D/Python pages, 68% of Cells pages.

7. **Disable multi-cycle regeneration** until generation quality improves — artifact review shows grade oscillation (d131: B→C regressions, 4.5x token cost for marginal change). Single-cycle with correct prompts is more efficient.

**The evaluator recalibration (TC-EVAL-200) was necessary but insufficient.** It moved from 30% false A+B to ~10% false A+B — that's real progress. But it still passes shell pages (empty code, empty sections) as C. Until empty-content checks are added, the evaluator's D+F rate cannot be trusted.
