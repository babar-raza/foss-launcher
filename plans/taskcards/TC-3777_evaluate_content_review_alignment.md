---
id: TC-3777
title: "Align Evaluate worker with content_review.md findings"
status: In-Progress
priority: High
owner: "claude-agent"
updated: "2026-03-07"
tags: [evaluate, content-review, quality-gates]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3777_evaluate_content_review_alignment.md
  - src/launcher/workers/evaluate/checks/repetition.py
  - src/launcher/workers/evaluate/checks/product_names.py
  - src/launcher/workers/evaluate/checks/semantic_structure.py
  - src/launcher/workers/evaluate/checks/artifacts.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/diagnosis.py
  - src/launcher/prompts/review_prompt.txt
  - tests/unit/workers/test_evaluate.py
evidence_required:
  - reports/TC-3777/evidence.md
---

# Taskcard TC-3777 — Align Evaluate worker with content_review.md findings

## Objective

Close the gap between automated evaluation and human content review. Manual review (plans/content_review.md) found 70% D/F grades across 60 files while all passed 42/42 automated gates. Add 3 new deterministic checks, enhance 1 existing check, update the LLM review prompt, and add manifest-level permalink validation so the Evaluate worker produces honest quality signals.

## Required spec references

- `plans/content_review.md` (Section: The 7 Systemic Defects, Recommendations)
- `specs/schemas/evaluation_report.schema.json` (Section: Finding model)

## Scope

### In scope
- New check: `check_repetition` (intra-page content repetition detection)
- New check: `check_product_names` (product name misspelling detection)
- New check: `check_semantic_structure` (duplicate sections, content after See Also, section order)
- Enhanced: `check_artifacts` (add "When working with" pattern, repeated opener detection, keyword stuffing)
- Enhanced: `review_prompt.txt` (add API consistency + audience appropriateness criteria)
- Plumbing: `worker.py`, `checks/__init__.py`, `diagnosis.py` updates
- Manifest-level permalink collision check in `worker.py`
- Tests for all new and modified checks

### Out of scope
- P2 content strategy changes (evidence diversification, reference templates) — belongs in Generate worker
- Changes to upstream workers (Understand, Generate)
- Changes to grader.py or go_criteria.py thresholds

## Inputs

- `ContentManifest` with `GeneratedPage` items containing markdown content
- `plans/content_review.md` defect patterns as detection targets

## Outputs

- 3 new check modules in `src/launcher/workers/evaluate/checks/`
- Enhanced `check_artifacts.py` with new patterns
- Enhanced `review_prompt.txt` with 2 new criteria
- Updated `worker.py`, `checks/__init__.py`, `diagnosis.py`
- Tests covering all changes in `tests/unit/workers/test_evaluate.py`

## Allowed paths

- plans/taskcards/TC-3777_evaluate_content_review_alignment.md
- src/launcher/workers/evaluate/checks/repetition.py
- src/launcher/workers/evaluate/checks/product_names.py
- src/launcher/workers/evaluate/checks/semantic_structure.py
- src/launcher/workers/evaluate/checks/artifacts.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/diagnosis.py
- src/launcher/prompts/review_prompt.txt
- tests/unit/workers/test_evaluate.py

### Allowed paths rationale
- checks/*.py: new and modified check modules
- __init__.py: registration of new checks
- worker.py: plumbing to call new checks + permalink check
- diagnosis.py: root-cause mapping for new check names
- review_prompt.txt: LLM review criteria expansion
- test_evaluate.py: test coverage for all changes
- taskcard: this file

## Implementation steps

### Step 1: Create check_repetition.py
Implement intra-page sentence repetition detection using Jaccard similarity from `src/launcher/shared/jaccard.py`.

### Step 2: Create check_product_names.py
Implement product name misspelling detection with configurable product_name parameter.

### Step 3: Create check_semantic_structure.py
Implement duplicate section detection, content-after-terminal-section detection, and section order validation.

### Step 4: Enhance check_artifacts.py
Add "when working with" and related patterns. Add repeated section opener detection. Add keyword stuffing detection.

### Step 5: Update plumbing
Expand `_run_deterministic_checks` signature, update `checks/__init__.py`, update `diagnosis.py`.

### Step 6: Add manifest-level permalink check
Add permalink collision and doubled-segment detection in `worker.py` run method.

### Step 7: Enhance review_prompt.txt
Add criteria 8 (API consistency) and 9 (audience appropriateness).

### Step 8: Write tests
Add test classes for all new checks and enhanced functionality.

### Step 9: Run full test suite
Verify all existing + new tests pass with PYTHONHASHSEED=0.

## Failure modes

### Failure mode 1: False positives on repetition check
**Detection**: Good content (_GOOD_CONTENT fixture) triggers repetition findings
**Resolution**: Tune Jaccard threshold (start at 0.7, raise if needed) and minimum sentence count
**Gate**: TestCheckRepetition.test_clean_content_no_findings

### Failure mode 2: Product name check triggers on code blocks
**Detection**: Code like `from aspose.cells import Workbook` flagged as misspelling
**Resolution**: Strip code blocks before scanning prose
**Gate**: TestCheckProductNames.test_code_blocks_ignored

### Failure mode 3: Semantic structure breaks on TOC/index pages
**Detection**: TOC pages with minimal structure flagged for missing content after sections
**Resolution**: Skip or soften checks when page_role=="toc"
**Gate**: TestCheckSemanticStructure.test_toc_page_lenient

## Task-specific review checklist

1. [ ] All 3 new check files follow existing pattern (function returning list[Finding])
2. [ ] _GOOD_CONTENT fixture passes all new checks with zero high/critical findings
3. [ ] Each new check has positive tests (defect triggers finding) and negative tests (clean content passes)
4. [ ] check_artifacts enhancement doesn't break existing tests
5. [ ] worker.py plumbing threads product_name correctly
6. [ ] diagnosis.py maps all new check names to responsible workers
7. [ ] review_prompt.txt JSON output format updated for new criteria
8. [ ] Full test suite passes with PYTHONHASHSEED=0

## Deliverables

1. 3 new check modules: repetition.py, product_names.py, semantic_structure.py
2. Modified: artifacts.py, __init__.py, worker.py, diagnosis.py, review_prompt.txt
3. Test coverage in test_evaluate.py
4. Evidence at reports/TC-3777/evidence.md

## Acceptance checks

1. [ ] All new checks detect their target defects (positive tests pass)
2. [ ] Clean content passes all checks without false positives (negative tests pass)
3. [ ] Full test suite passes: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest
4. [ ] New checks registered in __init__.py and callable from worker.py
5. [ ] Diagnosis maps new checks to responsible workers

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3777/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
```

**Expected results**:
- All existing tests continue to pass
- New test classes for repetition, product_names, semantic_structure pass
- Enhanced artifacts tests pass

## Integration boundary proven

**Upstream**: ContentManifest from Generate worker provides markdown content
**Downstream**: EvaluationReport consumed by pipeline for GO/NO-GO decision
**Contract**: Finding model (check, message, severity, location) — unchanged schema
