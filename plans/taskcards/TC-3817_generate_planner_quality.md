---
id: TC-3817
title: "Generate/Planner quality: rich API prompts + adaptive pages + FAQ fix + method validation"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [generate, planner, content-quality, prompt-engineering]
depends_on: [TC-3816]
allowed_paths:
  - plans/taskcards/TC-3817_generate_planner_quality.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/planner/worker.py
  - src/launcher/provenance/provenance.py
  - tests/unit/workers/test_generate.py
  - tests/unit/workers/test_planner.py
  - tests/unit/workers/generate/test_section_prompt.py
  - tests/unit/workers/generate/test_section_validator.py
  - reports/TC-3817/evidence.md
evidence_required:
  - reports/TC-3817/evidence.md
---

# Taskcard TC-3817 — Generate/Planner Quality: Rich API Prompts + Adaptive Pages + FAQ Fix + Method Validation

## Objective

Complete the downstream half of the adaptive content quality plan. TC-3816 produced clean API surface with ClassBriefs, docstring claims, and synthetic snippets. This taskcard ensures the generator and planner USE that data correctly: rich API prompts (Change A completion), adaptive page count (Change B), empty-claims fix (Change C), FAQ heading fix (Change D), method name validation (Change F), and ENGINE_VERSION bump.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md` (API surface in prompts)
- `specs/03_product_facts_and_evidence.md` (Claims distribution)

## Scope

### In scope
- **Change A (completion)**: Rewrite `_format_api_surface()` to emit rich ClassBrief data; pass class_briefs through generate worker
- **Change B**: Density-based page pruning in planner — prune optional pages with density < 2
- **Change C**: Fix empty-claims prompt contradiction — replace "write general content" with constrained fallback
- **Change D**: Fix FAQ heading-as-content bug — tighten FAQ directive + post-LLM heading length check
- **Change F**: Post-LLM method name validation — check backticked identifiers against api_identifiers
- **ENGINE_VERSION bump**: 2.2.0 → 2.3.0

### Out of scope
- Understand-phase changes (done in TC-3816)
- Pilot verification runs (separate step after merge)

## Inputs

- `ApiSurface.class_briefs` (from TC-3816)
- `Snippet.source_type="synthetic"` (from TC-3816)
- Existing generate worker, section_prompt, planner

## Outputs

- Updated `section_prompt.py` with rich API surface formatting + empty-claims fix + FAQ directive
- Updated `worker.py` (generate) with class_briefs passthrough + heading length check + method validation
- Updated `plan.py` with density-based page pruning
- Updated `provenance.py` with ENGINE_VERSION 2.3.0

## Allowed paths

- plans/taskcards/TC-3817_generate_planner_quality.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/planner/plan.py
- src/launcher/workers/planner/worker.py
- src/launcher/provenance/provenance.py
- tests/unit/workers/test_generate.py
- tests/unit/workers/test_planner.py
- tests/unit/workers/generate/test_section_prompt.py
- tests/unit/workers/generate/test_section_validator.py
- reports/TC-3817/evidence.md

### Allowed paths rationale
- `section_prompt.py`: Changes A, C, D all modify prompt building
- `worker.py` (generate): Changes A, D, F modify the generate worker
- `section_validator.py`: Change D adds heading length check
- `plan.py`: Change B adds density-based pruning
- `worker.py` (planner): May need self-review updates for pruned pages
- `provenance.py`: ENGINE_VERSION bump

## Implementation steps

### Step 1: Change A — Rich API surface in prompts
Rewrite `_format_api_surface()` to accept ClassBrief objects and emit structured lines.
Update `build_section_prompt()` signature to accept `class_briefs`.
Update generate worker to pass `class_briefs` from understand bundle.

### Step 2: Change C — Fix empty-claims prompt contradiction
Replace `"(No specific claims for this section -- write general introductory content)"` with constrained fallback text.

### Step 3: Change D — Fix FAQ heading-as-content bug
Tighten FAQ directive in `_STRUCTURE_DIRECTIVES`.
Add heading length check in `section_validator.py`.

### Step 4: Change B — Adaptive page count
Add density-based pruning after claim assignment in `run_plan()`.

### Step 5: Change F — Post-LLM method name validation
Add backtick identifier validation in generate worker.

### Step 6: ENGINE_VERSION bump
Update `provenance.py` from 2.2.0 to 2.3.0.

### Step 7: Write tests + run full suite

## Failure modes

### Failure mode 1: Rich API surface exceeds token budget
**Detection**: Prompt length > 4000 tokens for single section.
**Resolution**: Cap class_briefs to 15 per page, methods to 5 per class in prompt.
**Gate**: No gate — LLM truncation may silently drop context.

### Failure mode 2: Density pruning removes too many pages
**Detection**: After pruning, fewer than 5 pages remain.
**Resolution**: Keep minimum 5 pages — if pruning would reduce below 5, keep highest-density optional pages.
**Gate**: Planner self-review checks total_pages >= 5.

### Failure mode 3: Method validation strips legitimate identifiers
**Detection**: Post-validation blocks have no backticked identifiers remaining.
**Resolution**: Only strip in paragraph blocks, not code blocks. Log warnings for review.
**Gate**: factual_accuracy check in evaluator.

## Task-specific review checklist

1. [ ] `_format_api_surface()` emits class names with methods/properties/docstrings
2. [ ] Empty-claims fallback text is constrained (no "write general content")
3. [ ] FAQ directive explicitly separates question heading from answer paragraph
4. [ ] Heading blocks > 80 chars are split into heading + paragraph
5. [ ] Density-based pruning preserves mandatory pages
6. [ ] Method name validation checks against api_identifiers
7. [ ] ENGINE_VERSION is 2.3.0
8. [ ] All existing tests still pass

## Deliverables

1. Updated `src/launcher/workers/generate/section_prompt.py`
2. Updated `src/launcher/workers/generate/worker.py`
3. Updated `src/launcher/workers/generate/section_validator.py`
4. Updated `src/launcher/workers/planner/plan.py`
5. Updated `src/launcher/provenance/provenance.py`
6. Tests passing
7. Evidence at `reports/TC-3817/evidence.md`

## Acceptance checks

1. [ ] Rich API surface includes methods/properties in prompt
2. [ ] Empty-claims sections use constrained fallback
3. [ ] FAQ heading blocks are < 80 chars
4. [ ] Optional pages with density < 2 are pruned
5. [ ] Backticked identifiers not in api_identifiers are stripped
6. [ ] ENGINE_VERSION = 2.3.0
7. [ ] Full test suite passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3817/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

**Expected results**:
- All tests pass
- ENGINE_VERSION = 2.3.0

## Integration boundary proven

**Upstream**: TC-3816 provides `ApiSurface.class_briefs`, docstring claims, synthetic snippets
**Downstream**: Evaluate worker grades generated content; Publish worker renders final output
**Contract**: `ApiSurface` pydantic model with `class_briefs` field; `PlannedPage` list after pruning; `BlockIR` with validated identifiers
