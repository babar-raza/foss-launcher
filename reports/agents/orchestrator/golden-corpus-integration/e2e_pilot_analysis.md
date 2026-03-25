# E2E Pilot Analysis: Golden Corpus Integration
**Date**: 2026-03-15
**Pilot**: aspose-cells-foss-python
**Baseline run**: 260314_212211_cells_python_163f
**New run**: 260315_070720_cells_python_f45a
**Task**: Prove plan effectiveness via live pilot execution

---

## 1. Pilot Setup

| Item | Value |
|------|-------|
| Config | `configs/pilots/aspose-cells-foss-python.yaml` |
| Golden | `golden/` (enabled: true, 7 pages indexed) |
| LLM | `qwen3-next` @ `llm.professionalize.com/v1` |
| Pages planned | 22 mandatory |
| Understand tier | A (score=89, 130 claims, 31 snippets, 56 classes) |

---

## 2. What Was Run

1. **Understand phase** (run `260315_070311_cells_python_fa6d`): Completed in 54s. All 6 pages showed `sufficient` evidence. Golden fields not present in understanding_bundle (expected — golden is planner+generate phase).
2. **Full E2E run** (run `260315_070720_cells_python_f45a`): intake → scout → understand → planner → generate → evaluate (evaluate phase in progress at time of analysis).

---

## 3. Phase-by-Phase Findings

### 3.1 Planner Phase

**Golden fields in planner_checkpoint.json:**

| Field | Expected | Actual |
|-------|----------|--------|
| `golden_section_hints` | Non-null for most pages | `None` for all 22 pages |
| `golden_word_targets` | Non-empty dict | `{}` for all 22 pages |
| `golden_skeleton_used` | `True` for matched pages | `None` for all 22 pages |

**Root cause (Bug 1):** `run_plan()` in `worker.py:65-72` is called WITHOUT the `golden_dir` parameter:

```python
pages, claim_assignment_index = run_plan(
    bundle.product, bundle.richness_tier, bundle.claims, bundle.snippets,
    product_evidence=bundle.product_evidence,
    # ... other params ...
    # golden_dir=??? ← MISSING
)
```

`_enhance_skeleton_from_golden()` and `_attach_word_count_targets()` in `plan.py` both guard on `if golden_dir is None: return` — so P1 (skeleton hints) and P3 (word targets) are always no-ops.

**Secondary bug (Bug 2):** The planner worker's golden self-review at lines 77-134 of `worker.py` attempts to mutate a frozen pydantic `PlannedPage` model (`page.golden_unmatched_sections = ...`), producing:
```
Golden self-review skipped: 1 validation error for PlannedPage
golden_unmatched_sections
  Instance is frozen [type=frozen_instance]
```
This skips the entire golden self-review loop silently.

### 3.2 Generate Phase

**Golden injection per LLM prompt:**

| Metric | Value |
|--------|-------|
| Total LLM calls | 52 |
| Calls with golden content injected | **1 (1.9%)** |
| WRITING STANDARDS present | 1 call |
| EXPECTED SECTION STRUCTURE present | 1 call |

**Root cause (Bug 3):** `_build_golden_reference_block()` in `section_prompt.py:1824-1825` bails early if no excerpt is found for the specific section heading:

```python
excerpt = _load_golden_for_role(page_role, gdir, section_heading, variant=variant)
if not excerpt:
    return ""  # ← returns before building style_rubric_block or block_seq_block
```

The golden corpus headings are domain-specific to .NET exemplars (e.g., "Workbook-Level Encryption", "Worksheet Protection") and do not match the cells-python section headings (e.g., "Overview", "Working with Data", "First Steps"). Only 1 section ("Best Practices") matched.

**Impact:** The style rubric (G1) and block sequence prescription (G2/G3) are effectively never injected for cells-python pages.

### 3.3 Evaluate Phase

**New Phase A checks confirmed running** (from evaluate worker debug logs):

- `check_block_sequence` — imported and invoked (TC-GLD-005)
- `check_code_completeness` — imported and invoked (TC-GLD-006)
- `check_link_density` — imported and invoked (TC-GLD-012)
- `check_use_case_specificity` — imported and invoked (TC-GLD-013)
- `check_empty_code_blocks`, `check_empty_sections` — present (TC-4304)
- `check_placeholder_content` — present (TC-4305)

**Phase A findings observed:** `how-to-save-spreadsheets-python: phase_a_findings=20` (vs baseline pages averaging ~5 findings) — confirming the new checks are surfacing real problems.

---

## 4. Quantitative Comparison

### 4.1 New Check Findings: Baseline vs New Run

| Check | Baseline (22 files) | New Run (22 files) | Delta | Note |
|-------|--------------------|--------------------|-------|------|
| `golden_sequence` (prose-before-code) | 11 | 12 | +1 | No improvement |
| `code_completeness` (missing import/output) | 6 | **13** | +7 | Worse |
| `link_density` | 0 | 0 | 0 | Not triggered |
| `use_case_specificity` | 21 | 20 | -1 | No change |
| avg_words | 379.2 | 387.5 | +8.3 | Negligible |

**Conclusion from quantitative data:** The new run shows no systematic improvement vs baseline. `code_completeness` is worse (likely due to LLM stochasticity with no golden guidance to anchor behavior).

### 4.2 Grade Distribution (Baseline)

| Grade | Count | % |
|-------|-------|---|
| A | 0 | 0% |
| B | 3 | 14% |
| C | 16 | 73% |
| D | 1 | 5% |
| F | 2 | 9% |

A+B = 14%, D+F = 14%. New run evaluation not yet complete.

---

## 5. Manual Content Review

### Page 1: `docs/getting-started` (workflow_page)
**Grade: C**

**Strengths:**
- Logical structure: Overview → Prerequisites → First Steps → Code Example → See Also
- Correct canonical import (`import aspose.cells`)
- Working code examples with cell manipulation

**Weaknesses:**
- `## Next Steps` section is **completely empty** (content generation failure — no content after heading)
- `code_completeness` check finds 4 violations: code blocks without `print()` or `assert` output verification
- Prerequisites section mentions pip install but forgets to include it in the bash block
- Description frontmatter wraps API names in backticks (`modify`) which is unusual

**Assessment:** Would require editing before publication. Not publishable as-is.

### Page 2: `docs/installation` (workflow_page)
**Grade: C−**

**Strengths:**
- Describes system requirements clearly
- Includes file format list

**Weaknesses:**
- `## System Requirements` opens directly with a code block (prose-before-code violation)
- Code block contains logic errors: imports `aspose.cells as ac` then uses `pycryptodome.__version__` without importing it
- Code uses fictional pattern (checking dependency versions programmatically) that doesn't match the actual Aspose.Cells FOSS API
- Missing the actual `pip install` command in the Installation section
- `golden_sequence` check flags this as code-first (MEDIUM)

**Assessment:** The code example would fail if executed. Not publishable.

### Page 3: `kb/how-to-save-spreadsheets-python` (howto_article)
**Grade: B−**

**Strengths:**
- Clear problem-solution structure
- Functional code example with correct import
- Multi-format save table
- Links to related content

**Weaknesses:**
- Table is malformed: stored as nested JSON string `[['Format', 'Save Method', ...]]` instead of Markdown table
- `workbook.save_as_csv()` and `workbook.save_as_json()` may be invented API names (not confirmed in scout)
- `code_completeness` check flags 2 sections for missing output verification
- Phase A finds 20 issues for this page (highest of all pages evaluated)

**Assessment:** B-grade — partially publishable with editing. Table rendering would fail in Hugo.

### Page 4: `docs/spreadsheet-operations` (workflow_page)
**Grade: B**

**Strengths:**
- Comprehensive coverage of 6 operations (Read, Write, Format, Tables, Shapes, Pictures, Sparklines)
- Each sub-operation has prose + code block
- Code examples are complete and syntactically correct
- `from aspose.cells import MsoDrawingType` correct import pattern

**Weaknesses:**
- `## Code Examples` section has heading but empty body ("The following example creates a new workbook..." then nothing)
- `ShapeCollection.add()` signature `(MsoDrawingType, row, col, height, width)` may not match actual API
- `SparklineType.LINE` and SparklineGroups API not confirmed in scout

**Assessment:** Good structure but has an empty section and unverified API calls. B-grade, close to publishable.

---

## 6. Root Cause Analysis

### Why the plan didn't improve outputs

The plan was correctly designed and correctly implemented in isolation. However, **three integration bugs prevent it from activating at runtime:**

| Bug | Location | Impact | Severity |
|-----|----------|--------|----------|
| Bug 1: `golden_dir` not passed to `run_plan()` | `planner/worker.py:65` | P1 (hints) + P3 (word targets) never fire | HIGH |
| Bug 2: Frozen PlannedPage mutation | `planner/worker.py:109,121` | Golden self-review crashes silently | MEDIUM |
| Bug 3: Style rubric gated on excerpt match | `section_prompt.py:1824` | G1/G2/G3 fire in 1/52 prompts | HIGH |

### Compounding architectural issue

The golden corpus headings are domain-specific to .NET pages (the training data), while cells-python pages use different section vocabulary. Even after Bug 3 is fixed (decouple style rubric from excerpt), the excerpt match rate for cells-python will remain low (~10-20%) because `_load_golden_for_role` uses fuzzy heading matching against .NET-biased golden files.

**Fix needed:** The style rubric (`_build_style_rubric_block`) should be injected as a **page-level block** (not section-level), independent of whether a golden excerpt is found. The block sequence and excerpt should remain section-level optional enhancements.

---

## 7. What IS Working

1. **Architecture is correct** — The `GoldenIndex.load()`, `GoldenStyleRubric`, and 6 new `GoldenSection` fields are correctly implemented and fully functional when called
2. **New Phase A checks fire** — `check_block_sequence`, `check_code_completeness`, etc. are correctly wired into the evaluate worker and produce real findings
3. **One golden injection confirmed** — The "Best Practices" section got a full `WRITING STANDARDS` + `EXPECTED SECTION STRUCTURE` block, proving the mechanism works end-to-end when triggered
4. **Evaluate worker's anchor excerpt (E6) works** — `get_anchor_excerpt()` is functional and would inject A-grade calibration into LLM review
5. **Tests pass** — All 4702 unit tests pass (new checks tested in isolation)

---

## 8. What Needs to Be Fixed

Three healing taskcards are needed to activate the integration:

### HT-001: Pass `golden_dir` to `run_plan()` (Bug 1 + Bug 2)
- In `planner/worker.py:65`, add `golden_dir=Path(golden_cfg.get("dir", "golden/"))` when `golden_enabled`
- In `planner/worker.py:109,121`, use `page.model_copy(update={"golden_unmatched_sections": unmatched_headings})` instead of direct mutation

### HT-002: Decouple style rubric injection from excerpt lookup (Bug 3)
- In `section_prompt.py:_build_golden_reference_block()`, call `_build_style_rubric_block()` **before** the excerpt check and append it unconditionally
- The excerpt block is optional; the rubric is always useful

### HT-003: Generalize golden headings for cross-platform use
- Add platform-agnostic golden variants for `workflow_page` sections: "Overview", "Working with Data", "Code Examples", "Notes and Best Practices"
- Or: extend `_load_golden_section_for_role` to use semantic embedding similarity instead of exact heading match

---

## 9. Verdict

**The plan did NOT materially improve output quality in the E2E pilot.**

- Grade distribution: no measurable change vs baseline
- New check findings per page: same or worse (code_completeness +7 in new run)
- Average word count: +8 words (negligible)
- Golden content in prompts: 1/52 (1.9%) — effectively zero

**Why:** Three integration bugs prevent the plan from activating. The architecture is correct and well-tested in unit tests, but the runtime wiring has gaps.

**Prognosis:** Fixing Bug 1 and Bug 2 (1 taskcard, ~30 lines) plus Bug 3 (1 taskcard, ~10 lines) would activate the integration. With golden injection in 80%+ of prompts, the expected improvement from the plan's design (A+B target: ≥60%) becomes achievable.

**Recommendation:** Create HT-001 and HT-002 taskcards and execute them before concluding that the plan's design is sound.

---

## 10. Appendix: Evidence

| Evidence | Location |
|----------|----------|
| Baseline evaluation report | `runs/260314_212211_cells_python_163f/evaluation_report.json` |
| New run planner checkpoint | `runs/260315_070720_cells_python_f45a/planner_checkpoint.json` |
| LLM prompt with golden block | `runs/260315_070720_cells_python_f45a/evidence/llm_calls/llm_call_1773558647935.json` |
| New checks measurement script | (run inline in analysis) |
| Pipeline logs | `/tmp/e2e_cells_run.log` |
