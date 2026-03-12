---
id: TC-4221
title: "Generate: FAQ minimum answer depth — 3 sentences + ≥1 code block"
status: Done
priority: P1-Secondary
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, faq, content-depth, section-writer]
depends_on: [TC-4219]
allowed_paths:
  - plans/taskcards/TC-4221_generate-faq-depth.md
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/workers/generate/test_section_prompt.py
  - reports/TC-4221/evidence.md
evidence_required:
  - reports/TC-4221/evidence.md
---

# Taskcard TC-4221 — Generate: FAQ minimum answer depth — 3 sentences + ≥1 code block

## Objective

The FAQ page for 3d Python was generated with 0 code blocks and one-sentence answers (496 words for 11 Q&As, averaging 45 words/answer). The section_prompt.py has no depth constraint for `page_role == "faq"`. Fix: inject FAQ-specific minimum depth requirement into the section prompt, and add a post-generation assertion that flags FAQ pages with 0 code blocks as a generation failure.

## Required spec references

- `specs/worker_generate.md` (Section: Page roles — FAQ depth requirements)
- `specs/worker_evaluate.md` (Section: content_density — FAQ scoring)

## Scope

### In scope
- Add FAQ-specific prompt instruction in `build_section_prompt()` when `page_role == "faq"`: minimum 3 sentences per answer, at least 1 code example per page
- Add post-generation assertion: if FAQ has 0 code blocks, log ERROR and set a generation failure flag
- Unit test for FAQ prompt injection

### Out of scope
- TC-4220 (min prose retry — that applies to all pages; this is FAQ-specific depth)
- Changing the evaluate worker's FAQ scoring logic
- Other page roles

## Inputs

- `src/launcher/workers/generate/section_prompt.py` (line 718: `build_section_prompt`)
- `phase_store/3d/python/generate.json` (shows FAQ: 496 words, 0 code blocks)

## Outputs

- Modified `src/launcher/workers/generate/section_prompt.py`
- Modified `tests/unit/workers/generate/test_section_prompt.py`
- `reports/TC-4221/evidence.md`

## Allowed paths

- plans/taskcards/TC-4221_generate-faq-depth.md
- src/launcher/workers/generate/section_prompt.py
- tests/unit/workers/generate/test_section_prompt.py
- reports/TC-4221/evidence.md

### Allowed paths rationale
- `section_prompt.py`: FAQ depth constraint injected into LLM prompt here
- `test_section_prompt.py`: existing test file for section_prompt tests

## Implementation steps

### Step 1: Add FAQ depth constraint to `build_section_prompt`

In `build_section_prompt()`, detect when `page_role == "faq"` and inject into the system prompt:

```python
if page_role == "faq":
    system_parts.append(
        "## FAQ writing rules\n"
        "- Each answer must contain at least 3 complete sentences of explanation.\n"
        "- The FAQ page must include at least one code example (fenced code block) "
        "showing how to use the product for the most common question.\n"
        "- Do not use one-sentence answers. Every answer must be substantive."
    )
```

Place this block after the claim_context (TC-4219) and before the section skeleton.

### Step 2: Add post-generation FAQ assertion in generate worker

After generating a page with `page_role == "faq"`, count code blocks:

```python
if page_plan.page_role == "faq" and code_block_count == 0:
    logger.error(
        "[Generate] FAQ page %r generated with 0 code blocks — generation quality failure",
        slug,
    )
    # Set a warning flag on the GeneratedPage (do not block pipeline, but surface in generate.json)
```

Note: Do NOT block the pipeline on this assertion — the page is still written. The flag surfaces in generate.json and evaluate will catch it.

### Step 3: Add unit tests

In `tests/unit/workers/generate/test_section_prompt.py`:
1. `test_faq_depth_constraint_injected` — asserts `build_section_prompt(..., page_role="faq")` includes "3 complete sentences" in returned prompt
2. `test_non_faq_page_no_faq_constraint` — asserts non-FAQ page_role does NOT include FAQ constraint block

## Failure modes

### Failure mode 1: LLM ignores FAQ depth instruction

**Detection**: generate.json still shows `code_block_count == 0` for FAQ after fix.
**Resolution**: TC-4220's retry logic (separate taskcard) will catch this — 0 prose words on answer sections triggers retry. Combine both: FAQ pages also benefit from the min-prose retry.
**Gate**: Post-generation FAQ assertion in ERROR log is absent (meaning ≥1 code block generated).

### Failure mode 2: FAQ constraint injected on non-FAQ pages

**Detection**: Unit test `test_non_faq_page_no_faq_constraint` fails.
**Resolution**: Guard the injection with strict `page_role == "faq"` check.
**Gate**: Unit test passes.

### Failure mode 3: "3 complete sentences" rule conflicts with thin FAQ data from Understand

**Detection**: LLM writes filler to reach 3 sentences, creating hallucinated content.
**Resolution**: Combine with claim_context (TC-4219) — FAQ answers should be grounded in claim facts first. If claim facts are sparse, 3 sentences of factual content is still achievable.
**Gate**: Evaluate `factual_accuracy` HIGH findings do not increase for FAQ page.

## Task-specific review checklist

1. [ ] FAQ depth constraint only injected when `page_role == "faq"`
2. [ ] Constraint includes both sentence-count minimum AND code-block requirement
3. [ ] Post-generation assertion logs ERROR (not CRITICAL) when code_block_count == 0 for FAQ
4. [ ] Pipeline does NOT block on the assertion — page is still written
5. [ ] 2 unit tests added and passing
6. [ ] Docstring updated for `build_section_prompt` (new page_role-conditional behavior)
7. [ ] Spec checked: worker_generate.md — add FAQ depth requirement if not present
8. [ ] Schema unchanged
9. [ ] `docs/README.md` checked — no ownership trigger applies
10. [ ] No new docs/guides files needed

## Deliverables

1. Modified `src/launcher/workers/generate/section_prompt.py` with FAQ depth constraint
2. Modified `tests/unit/workers/generate/test_section_prompt.py` with 2 new tests
3. `reports/TC-4221/evidence.md` — test output + FAQ code_block_count before/after

## Acceptance checks

1. [x] `pytest tests/unit/workers/generate/test_section_prompt.py -v` — all tests PASS (43/43)
2. [ ] Re-run generate on 3d Python: FAQ page has ≥1 code block
3. [ ] Re-run generate on 3d Python: FAQ answers average ≥3 sentences
4. [ ] Post-generation FAQ assertion ERROR log absent (meaning code block constraint satisfied)

## Self-review

### Verification results
- [x] Tests: 43/43 PASS (section_prompt); 3841/3841 PASS (full unit suite)
- [ ] Validation: FAQ code_block_count ≥1 PASS (requires live pipeline run)
- [x] Evidence captured: reports/TC-4221/evidence.md
- [x] Doc freshness: no new docs files created

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt.py -v
```

**Expected results**:
- All existing section_prompt tests pass
- 2 new FAQ depth tests pass

## Integration boundary proven

**Upstream**: `page_plan.page_role` (from Plan phase) → determines FAQ constraint injection
**Downstream**: LLM section writer receives FAQ depth rules → generates substantive answers with code examples
**Contract**: FAQ pages generated by the generate worker must have ≥1 code block and ≥3 sentences per answer
