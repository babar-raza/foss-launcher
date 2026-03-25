# TC-PILOT-300: Phase Artifact Review

## Overview

Deep artifact review of 4 post-fix completed runs: Cells/Python 163f, Cells/Python d131, Note/Python da73, 3D/.NET 5c10.

---

## Cells/Python (163f — single cycle)

| Artifact | Status | Key Metrics |
|----------|--------|-------------|
| scout_bundle.json | Healthy | 95 files, 92 read, 1.59 MB, 0 budget overflow |
| understanding_bundle.json | Mixed — empty docstrings | 56 classes, 132 claims (all grounded), 31 snippets, richness A (score 89) |
| evaluation_report.json | NO_GO | B:3, C:16, D:1, F:2. Avg 379 words/page |
| promotion_report.json | 7 promoted, 15 skipped | 3 grade_low, 12 no_improvement |
| pipeline_metrics.json | 44 LLM calls, 1.59M tokens, 725s, 0 fallbacks |

**Key findings:**
- **All 56 class_briefs have empty docstrings** — the deterministic extractor captures class names and method signatures but does not populate docstring text. This is a universal gap affecting all families.
- Identifier repair log: 3 pages had identifiers repaired (ProtectionType, AutoFilter, NoneType) — evidence the repair step is functioning for Python.
- F-grade pages: `_index` (scaffold text, keyword stuffing) and `installation` (insufficient content).

---

## Cells/Python (d131 — 3 generate/evaluate cycles)

| Artifact | Status | Key Metrics |
|----------|--------|-------------|
| understanding_bundle.json | Same as 163f | 56 classes, 135 claims, 31 snippets, richness A (89) |
| evaluation_report.json | NO_GO | B:3, C:19. Avg 471 words/page |
| promotion_report.json | 6 promoted, 16 no_improvement | 0 grade_low skips |
| pipeline_metrics.json | **197 LLM calls, 5.68M tokens, 1952s** — 4.5x cost vs 163f |

**Key findings:**
- **Grade oscillation, not convergence**: Pages like `how-to-save-spreadsheets` went B→C (regression). `_index` oscillated across 12 grade changes before landing on C. The multi-cycle approach does not reliably improve quality.
- `how-to-fix-spreadsheets-errors` and `troubleshooting` **regressed** from B to C across cycles.
- 4.5x higher token cost produced only marginally different results from 163f (same A+B%, 0 D+F in both best cases).
- keyword_stuffing emerged as a top-12 finding type (not present in 163f) — suggesting regeneration introduced new SEO-related defects.

---

## Note/Python (da73 — single cycle)

| Artifact | Status | Key Metrics |
|----------|--------|-------------|
| understanding_bundle.json | Mixed | 34 classes, 128 claims (all grounded), 37 snippets, richness A (76) |
| evaluation_report.json | NO_GO | B:1, C:21. Avg **239 words/page** — thinnest content of all runs |
| promotion_report.json | 6 promoted, 16 no_improvement |
| pipeline_metrics.json | 50 LLM calls, 297K tokens, 926s |

**Key findings:**
- **Lowest docstring saturation**: Only 10.9% of claims from docstrings vs 78.5% for Cells. 114/128 claims come from non-docstring sources (README, comments). The Note source repo has sparse inline documentation.
- **All 34 class_briefs have empty docstrings** — same universal gap.
- Average 239 words/page is far below the ~500-word minimum for substantive content.
- `semantic_structure` is the top evaluator finding (24 instances across 22 pages) — more than one per page on average.
- keyword_stuffing is the 3rd most common finding (17 instances).
- **Run-to-run stability confirmed**: second run (f880) produced identical B:1, C:21 — same grades, same distribution. This is deterministic but deterministically mediocre.

---

## 3D/.NET (5c10 — 2 generate/evaluate cycles)

| Artifact | Status | Key Metrics |
|----------|--------|-------------|
| understanding_bundle.json | **CRITICAL: 0 classes extracted** | 40 claims, 6 snippets, richness C (32) |
| evaluation_report.json | NO_GO | C:17, D:1. Avg 314 words/page |
| promotion_report.json | 13 promoted (highest rate), 5 skipped |
| pipeline_metrics.json | 80 LLM calls, 446K tokens, 1259s |

**CRITICAL finding: Zero public classes extracted**

The C# analyzer extracted **0 class_briefs** from 115 source files. `code_evidence_sparse: True`, `code_evidence_score: 1` (vs 20 for Cells). The generate worker had no API surface to work with — it hallucinated class names and method signatures, which the identifier repair step then stripped as unrecognized identifiers, producing `[identifier omitted]` everywhere.

This is the root cause of the 67% human D+F on the .NET run:
1. C# extraction → 0 classes (extractor fails silently on C# code)
2. Generate worker → hallucinated API to fill the void
3. Identifier repair → strips hallucinated identifiers → `[identifier omitted]`
4. Evaluator → doesn't detect `[identifier omitted]` as CRITICAL → grades C

The identifier repair step is actually functioning correctly — it correctly rejects identifiers not in the known API surface. The upstream failure is the C# extractor not populating that surface.

**Generator repair log**: Extensive identifier repairs across 10 pages (RootNode, ThreeD, NuGet, FileFormat, etc.) — confirms the hallucination-then-strip pipeline.

**Highest promotion rate** (13/18 = 72%) despite worst human quality — confirms the promotion threshold is calibrated to evaluator grades which don't reflect human quality.

---

## Cross-Run Systematic Findings

### Finding 1: Empty docstrings is UNIVERSAL (not a 3D-specific problem)

| Run | Classes | With Docstrings | Rate |
|-----|:-------:|:---------------:|:----:|
| Cells 163f | 56 | 0 | 0% |
| Cells d131 | 56 | 0 | 0% |
| Note da73 | 34 | 0 | 0% |
| 3D/.NET 5c10 | 0 | 0 | — |

The deterministic extractor captures class names and method signatures but doesn't extract docstring text for any family. This is a pipeline-wide gap in `_deterministic.py` or `_api_surface.py`, not a source repo problem (Cells has rich docstrings per manual inspection).

### Finding 2: C# API extraction is non-functional

Zero class_briefs from 115 C# source files. The Python AST extractor cannot parse C#. There is no C# analyzer wired into the extraction pipeline. This is exactly RC-5 from the plan and must be addressed before .NET output is usable.

### Finding 3: Multi-cycle regeneration causes grade oscillation, not improvement

The d131 run (3 cycles, 4.5x cost) shows that regeneration loops do not converge toward quality. Pages oscillate: the LLM produces different content each cycle, some better, some worse. The retry mechanism for NO_GO evaluations is spending significant token budget without reliable improvement.

**Implication**: The fix for low-quality output is not more regeneration cycles — it's fixing the generation prompts and evidence quality that produce the initial C-grade output. More cycles of the same broken process don't improve the result.

### Finding 4: All runs are NO_GO — the quality ceiling is consistent

No run across any family passes the GO criteria. The pipeline consistently produces C-dominated distributions. The note that "evaluator D+F = 0%" was always false comfort — the human D+F rate across all families ranges 32-68%.

### Finding 5: Scout bundle does not contain claims

The `scout_bundle.json` / `scout.json` is a **file inventory** (categories, byte counts, build systems). Claims are extracted in the understand worker and stored in `understanding_bundle.json`. All claims across all runs are grounded with source file evidence.

---

## Revised Key Findings

1. **Empty docstrings is a pipeline bug, not a repo quality gap** — the extractor should be populating docstrings for Cells (which has them) but isn't
2. **C# extraction is broken** — 0 classes from 115 files; root cause of all .NET quality failures
3. **Multi-cycle regeneration degrades token efficiency without improving quality** — single-cycle is preferable until prompt quality is fixed
4. **All evaluator "0% D+F" results are false** — human review finds 32-68% D+F across all families
5. **The quality ceiling is C** — pipeline produces mediocre content consistently and reproducibly
6. **Promotion gate is calibrated to evaluator, not human quality** — 72% promotion on .NET despite 67% human D+F
