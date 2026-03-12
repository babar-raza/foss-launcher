---
id: TC-HO-07
title: "Verify keyword_research.per_page planner flow and seo_keywords injection"
status: Done
priority: Normal
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [planner, section_prompt, seo_keywords, wave4b]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HO-07_keyword-per-page-planner.md
  - tests/unit/workers/generate/test_tc_ho07_keyword_per_page.py
  - reports/agents/wave4b/TC-HO-07/evidence.md
evidence_required:
  - reports/agents/wave4b/TC-HO-07/evidence.md
---

# Taskcard TC-HO-07 — Verify keyword per_page planner flow

## Objective

Verify that `keyword_research.per_page[page_role]` is already copied onto `PlannedPage.seo_keywords`
in the planner and that `page.seo_keywords` is already injected into the section prompt. Add
a test asserting both behaviors to prevent future regressions.

## Required spec references

- `specs/worker_generate.md` (Section: SEO keyword injection)

## Scope

### In scope
- Audit `src/launcher/workers/planner/plan.py` for per_page → seo_keywords copy
- Audit `section_prompt.py` for seo_keywords injection
- Add regression test

### Out of scope
- Changing planner behavior (it already works)
- Modifying keyword_research models

## Inputs

- `src/launcher/workers/planner/plan.py` — current implementation
- `src/launcher/workers/generate/section_prompt.py` — current seo_keywords handling

## Outputs

- Test file `tests/unit/workers/generate/test_tc_ho07_keyword_per_page.py`
- Evidence markdown

## Allowed paths

- plans/taskcards/TC-HO-07_keyword-per-page-planner.md
- tests/unit/workers/generate/test_tc_ho07_keyword_per_page.py
- reports/agents/wave4b/TC-HO-07/evidence.md

### Allowed paths rationale

Audit-only for planner; test file for regression prevention.

## Implementation steps

### Step 1: Audit planner/plan.py

Confirm `_generate_seo_keywords()` reads `per_page[slug]` (already verified at line 1711-1713).
Confirm `seo_keywords=seo` is passed to `PlannedPage` construction.

### Step 2: Audit section_prompt.py

Confirm `getattr(page, "seo_keywords", None) or []` is already injected (line 682-686).
Both are already in place — no code changes needed.

### Step 3: Write test

Assert that when a PlannedPage has `seo_keywords=["convert", "export"]`, the keywords appear
in the `build_section_prompt()` output.

## Failure modes

### Failure mode 1: seo_keywords not on PlannedPage

**Detection**: AttributeError in section_prompt.py
**Resolution**: `getattr(page, "seo_keywords", None) or []` already safe

### Failure mode 2: Test creates PlannedPage without seo_keywords field

**Detection**: Pydantic validation error
**Resolution**: Verify PlannedPage has seo_keywords as an optional field with default []

### Failure mode 3: Keywords appear in wrong prompt position

**Detection**: Assertion failure in test
**Resolution**: Check `{seo_keywords_block}` placeholder position in section_writer.txt

## Task-specific review checklist

1. [ ] Planner per_page lookup confirmed working (line 1711-1713)
2. [ ] section_prompt.py seo_keywords injection confirmed (line 682-686)
3. [ ] Test asserts keywords from PlannedPage appear in prompt output
4. [ ] Test covers None/empty seo_keywords → fallback message
5. [ ] No code changes to planner (already correct)
6. [ ] Test file added to the test suite
7. [ ] Docstrings N/A (no new code)
8. [ ] Spec confirmed — no drift
9. [ ] Schema N/A
10. [ ] docs/README.md checked — no update needed
11. [ ] No new docs/guides/ file

## Deliverables

1. `tests/unit/workers/generate/test_tc_ho07_keyword_per_page.py`
2. `reports/agents/wave4b/TC-HO-07/evidence.md`

## Acceptance checks

1. [ ] Test asserting seo_keywords appear in prompt passes
2. [ ] Test asserting empty seo_keywords → fallback message passes
3. [ ] No regressions in `tests/unit/workers/generate/`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/wave4b/TC-HO-07/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc_ho07_keyword_per_page.py -v
```

**Expected results**:
- All tests pass

## Integration boundary proven

**Upstream**: `KeywordResearchBundle.per_page` populated by Understand worker
**Downstream**: `PlannedPage.seo_keywords` → `build_section_prompt()` → LLM prompt
**Contract**: planner copies per_page[slug] to PlannedPage.seo_keywords; section_prompt injects it
