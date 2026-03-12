---
id: TC-3798
title: "Content Quality Fixes for GO Verdict"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [content-quality, go-verdict, prompt-fix, post-processing]
depends_on: [TC-3782, TC-3783]
allowed_paths:
  - plans/taskcards/TC-3798_content_quality_go_verdict.md
  - src/launcher/prompts/section_writer.txt
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/evaluate/checks/code.py
  - src/launcher/workers/evaluate/checks/artifacts.py
  - src/launcher/workers/evaluate/checks/safety.py
  - src/launcher/workers/evaluate/checks/structure.py
  - tests/test_content_quality_fixes.py
evidence_required:
  - reports/TC-3798/evidence.md
---

# Taskcard TC-3798 — Content Quality Fixes for GO Verdict

## Objective

Fix 4 root causes driving 58% D+F rate to achieve GO verdict (A+B >= 50%, D+F <= 30%). Current pilot produces 6B/5C/15D with 10 factual_accuracy, 9 code_correctness, and 5 completeness high-severity findings.

## Required spec references

- `specs/content_quality.md` (Section: grading criteria)
- `specs/sandwich_model.md` (Section: post-LLM validation)

## Scope

### In scope
- Fix contradictory section_writer.txt prompt (says "NEVER use import X" when X is the canonical import)
- Fix product name casing in prose (display_name vs canonical_import)
- Add API surface context to section prompt (class names from understand bundle)
- Fix evaluate false positives: structure H1-in-code, safety XSS-in-code, code pip-as-python
- Raise artifacts repeated opener threshold from 3 to 4

### Out of scope
- Planner claim assignment logic (separate TC)
- LLM model changes or fine-tuning
- Template modifications

## Inputs

- Pilot run `pilot_cells_20260306T223447` evaluate results
- Understanding bundle (product identity, API surface, claims)
- Current section_writer.txt prompt template
- Current section_validator.py post-LLM validation

## Outputs

- Fixed section_writer.txt prompt
- Fixed section_prompt.py with API surface context
- Fixed section_validator.py product name normalization
- Fixed evaluate deterministic checks (structure, safety, code, artifacts)
- Test file for fixes

## Allowed paths

- plans/taskcards/TC-3798_content_quality_go_verdict.md
- src/launcher/prompts/section_writer.txt
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/evaluate/checks/code.py
- src/launcher/workers/evaluate/checks/artifacts.py
- src/launcher/workers/evaluate/checks/safety.py
- src/launcher/workers/evaluate/checks/structure.py
- tests/test_content_quality_fixes.py

### Allowed paths rationale
- section_writer.txt: Fix contradictory canonical import instruction
- section_prompt.py: Inject API surface classes into prompt context
- section_validator.py: Fix product name normalization (display_name for prose)
- evaluate checks: Fix false positives in deterministic checks
- tests: Verify fixes

## Implementation steps

### Step 1: Fix contradictory prompt in section_writer.txt

The prompt says "NEVER use 'import aspose.cells'" but when canonical_import IS aspose.cells, this contradicts itself. Remove hardcoded negative examples and make them dynamic.

### Step 2: Fix product name normalization in section_validator.py

`_normalize_product_name` currently replaces `aspose.cells` with canonical_import (same value). It should replace lowercase product name references in prose with the display_name (e.g., `Aspose.Cells`).

### Step 3: Add API surface to section prompt

Include public_classes from the understanding bundle in the prompt so the LLM knows which classes/methods actually exist and doesn't hallucinate.

### Step 4: Fix evaluate false positives

- structure.py: Strip code blocks before scanning for H1 headings
- safety.py: Strip code blocks before XSS pattern matching
- code.py: Skip AST validation for shell commands in python blocks
- artifacts.py: Raise repeated opener threshold from 3 to 4

### Step 5: Write tests and verify

## Failure modes

### Failure mode 1: Prompt too long with API surface context

**Detection**: LLM returns empty/truncated responses, or max_tokens exceeded
**Resolution**: Limit API surface to top 10 classes with max 5 methods each
**Gate**: Generate worker fallback count stays < 20%

### Failure mode 2: Product name normalization over-replaces in code blocks

**Detection**: Code blocks have display_name where canonical_import should be
**Resolution**: Only normalize outside backtick-quoted text and code fences
**Gate**: code_correctness check passes

### Failure mode 3: Evaluate check changes mask real issues

**Detection**: Grades inflate without actual content improvement
**Resolution**: Only fix demonstrated false positives, not legitimate findings
**Gate**: Re-run evaluate and manually verify sample pages

## Task-specific review checklist

1. [ ] section_writer.txt no longer contains hardcoded "aspose.cells" negative example
2. [ ] _normalize_product_name uses display_name for prose, not canonical_import
3. [ ] API surface context added to section prompt with reasonable token budget
4. [ ] structure.py strips code blocks before H1 scan
5. [ ] safety.py strips code blocks before XSS scan
6. [ ] code.py skips AST for pip/shell commands in python blocks
7. [ ] All existing tests pass

## Deliverables

1. Modified prompt, validator, and evaluate check files
2. Test file at tests/test_content_quality_fixes.py
3. Evidence at reports/TC-3798/evidence.md

## Acceptance checks

1. [ ] All existing tests pass (PYTHONHASHSEED=0)
2. [ ] No contradictory instructions in section_writer.txt
3. [ ] Product name appears as display_name in prose
4. [ ] Evaluate false positives eliminated for code-in-headings, XSS-in-code, pip-as-python

## Self-review

### Verification results
- [ ] Tests: PASS
- [ ] Validation: pilot re-run
- [ ] Evidence captured: reports/TC-3798/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
```

**Expected results**:
- All tests pass
- Pilot re-run shows improved grade distribution

## Integration boundary proven

**Upstream**: Understanding bundle (product, claims, API surface)
**Downstream**: Evaluate worker (grade assignment)
**Contract**: BlockIR JSON schema, PageIR model, Finding model
