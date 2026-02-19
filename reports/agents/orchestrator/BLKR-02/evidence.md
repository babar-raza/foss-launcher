# Evidence: BLKR-02 — Fix gate_17 FQ-1/3/4/7 Formatting Defects

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Branch:** `healing/blkr-01-03-04-rd06`
**Status:** DONE

---

## Summary of Changes

Added two-layer prevention for gate_17 formatting defect failures (FQ-1, FQ-3, FQ-4, FQ-7):

1. **Layer 1 (Prevention)**: Added `## FORMATTING RULES` section to all 12 W5 prompt files, explicitly warning the LLM not to produce each defect type.
2. **Layer 2 (Detection + Auto-fix)**: Added 4 deterministic check functions to W7 `technical_accuracy.py` and 3 auto-fix functions to `auto_fixes.py`, so any defects that slip through are caught and repaired before gate_17 runs.

---

## Root Cause

`gate_17_formatting_quality.py` uses an LLM oracle to detect FQ defects in generated pages.
W7 had no deterministic checks for FQ-1/3/4/7, so defects produced by the W5 LLM passed
through to gate_17 unchecked, causing avoidable gate failures.

Additionally, the W5 prompts contained no explicit guidance about these defect types,
so the LLM had no incentive to avoid them.

---

## FQ Code Definitions (from `format_fixer.txt`)

| Code | Name | Description |
|------|------|-------------|
| FQ-1 | NAKED_CODE | Code lines (`import`, `pip install`, `$ cmd`) outside fenced code blocks |
| FQ-3 | TRUNCATED | Bullet point ends mid-sentence or with trailing comma/dangling word |
| FQ-4 | DOUBLE_HEADING | Heading line >70 chars (paragraph text merged into heading) |
| FQ-7 | INCOHERENT | Section heading text verbatim repeated as first sentence of body |

---

## Layer 1: W5 Prompt Guards

Added identical `## FORMATTING RULES` block to all 12 W5 prompt files (before `## Output Format`):

```
## FORMATTING RULES

Avoid these formatting defects that cause pipeline validation failures:

- **FQ-1 Naked code**: All code — including single commands — must be in a fenced code
  block with a language tag (e.g., ```python or ```bash).
- **FQ-3 Truncated bullets**: Every bullet point must be a complete sentence ending with
  a period. Do not end bullets mid-sentence or with dangling words.
- **FQ-4 Double heading**: Always place a blank line between a heading and the following
  paragraph. Never write heading text and paragraph text on the same line.
- **FQ-7 Incoherent sentences**: Every sentence must be grammatically complete and
  logically coherent. Do not repeat the section heading verbatim as the opening sentence.
```

FAQ prompt also includes FQ-2 (FAQ_CONCAT) since FAQ pages are uniquely susceptible.

### Prompt files updated (12 total)

| File | Notes |
|------|-------|
| `prompts/tutorial.txt` | Standard FQ-1/3/4/7 block |
| `prompts/comprehensive_guide.txt` | Standard block |
| `prompts/faq.txt` | Standard block + FQ-2 (FAQ_CONCAT) |
| `prompts/best_practices.txt` | Standard block |
| `prompts/feature_showcase.txt` | Standard block |
| `prompts/troubleshooting.txt` | Standard block |
| `prompts/api_reference.txt` | Standard block |
| `prompts/feature_blog.txt` | Standard block |
| `prompts/format_conversion.txt` | Standard block |
| `prompts/howto_article.txt` | Standard block |
| `prompts/landing.txt` | Standard block |
| `prompts/workflow_page.txt` | Standard block |

---

## Layer 2: W7 Deterministic Checks

### New check functions in `checks/technical_accuracy.py`

| Function | FQ | Severity | Auto-fixable |
|----------|----|----------|--------------|
| `_check_fq1_naked_code()` | FQ-1 | error | Yes |
| `_check_fq3_truncated_bullets()` | FQ-3 | error | Yes |
| `_check_fq4_double_heading()` | FQ-4 | error | Yes |
| `_check_fq7_incoherent_headings()` | FQ-7 | warn | No |

All four functions are called from `check_all()` after existing check_15.

**FQ-7 limitation**: Full FQ-7 detection requires LLM (arbitrary incoherence is not pattern-matchable).
The deterministic check covers the most common detectable case: heading text verbatim repeated as
the first sentence of the body, which accounts for a significant fraction of FQ-7 failures.

### New auto-fix functions in `fixes/auto_fixes.py`

| Function | Behavior |
|----------|----------|
| `fix_fq1_naked_code()` | Wraps naked code line in ` ```python ` or ` ```bash ` fence |
| `fix_fq3_truncated_bullets()` | Removes trailing comma and adds period, or adds missing period |
| `fix_fq4_double_heading()` | Splits oversized heading at sentence boundary; fallback: split at capital letter |

Routing added in `apply_auto_fixes()` dispatcher for all three check names.

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/prompts/tutorial.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/comprehensive_guide.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/faq.txt` | Added FORMATTING RULES + FQ-2 |
| `src/launch/workers/w5_section_writer/prompts/best_practices.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/feature_showcase.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/troubleshooting.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/api_reference.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/feature_blog.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/format_conversion.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/howto_article.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/landing.txt` | Added FORMATTING RULES |
| `src/launch/workers/w5_section_writer/prompts/workflow_page.txt` | Added FORMATTING RULES |
| `src/launch/workers/w7_content_reviewer/checks/technical_accuracy.py` | Added 4 FQ check functions + `check_all()` calls |
| `src/launch/workers/w7_content_reviewer/fixes/auto_fixes.py` | Added 3 FQ fix functions + routing in dispatcher |
| `tests/unit/workers/test_content_reviewer_scoring.py` | Added 19 new FQ unit tests |

---

## Test Results

```
TestFQ1NakedCode:         5/5 pass
TestFQ3TruncatedBullets:  6/6 pass
TestFQ4DoubleHeading:     4/4 pass
TestFQ7IncoherentHeadings: 4/4 pass
Total new tests: 19

Full suite: 4557 passed, 9 skipped, 0 failed
(+19 new FQ tests vs BLKR-04 baseline of 4538)
```

---

## Acceptance Criteria

| Check | Result |
|-------|--------|
| All 12 W5 prompts contain FORMATTING RULES section | ✅ |
| `_check_fq1_naked_code` detects import/pip/$ outside fences | ✅ |
| `_check_fq3_truncated_bullets` detects trailing comma + dangling prepositions | ✅ |
| `_check_fq4_double_heading` detects headings >70 chars | ✅ |
| `_check_fq7_incoherent_headings` detects verbatim heading repetition | ✅ |
| Auto-fixes for FQ-1, FQ-3, FQ-4 applied and routed | ✅ |
| FQ-7 correctly marked `auto_fixable: False` | ✅ |
| False positive checks pass (valid content not flagged) | ✅ |
| Full test suite: 0 failures | ✅ 4557/4557 |
| No regressions in pre-existing tests | ✅ |
