---
id: TC-4058
title: "Phase 2 — Understand silent failure removal + self-review strengthening"
status: Done
priority: High
owner: "agent"
updated: "2026-03-11"
tags: [understand, self-review, artifact, evidence]
depends_on: [TC-4057]
allowed_paths:
  - plans/taskcards/TC-4058_understand_silent_failure_and_self_review.md
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_understand.py
evidence_required:
  - reports/TC-4058/evidence.md
---

# Taskcard TC-4058 — Phase 2: Understand silent failure removal + self-review strengthening

## Objective

Fix three structural weaknesses in the Understand worker that allow degraded or empty outputs
to pass self-review undetected: (1) `_extract_product_evidence` (Phase B.5) silently swallows
ALL exceptions including import errors and returns empty `ProductEvidence`, making analysis
failures invisible; (2) `self_review()` never checks whether `product_evidence` is empty or
whether any fields were actually populated; (3) `scout_inventory.json` reports skip counts but
not a breakdown by skip reason, making it hard for a human reviewer to assess what was missed
and why.

## Required spec references

- `specs/worker_understand.md` (Phase A Scout, Phase B.5 evidence enrichment)
- `specs/system_contract.md` (Error severity levels, silent failure prohibition)

## Scope

### In scope
- Distinguish import-level failures (hard stop) from analysis-level failures (logged at ERROR)
  in `_extract_product_evidence`
- Add `ProductEvidence` emptiness check to `self_review()` (medium severity, not blocking)
- Add `skip_reason_counts` breakdown to `scout_inventory.json`
- Update tests to verify the new self-review check and the skip reason breakdown

### Out of scope
- Removing Phase B.5 entirely (it still provides capabilities/workflows from code_analyzer)
- Fixing Phase B.5 duplicate manifest parsing (separate refactor)
- Changing the ProductEvidence model

## Inputs

- `src/launcher/workers/understand/worker.py` — current Phase B.5 + self_review

## Outputs

- Updated `src/launcher/workers/understand/worker.py`
- Updated `tests/unit/workers/test_understand.py` with new self-review checks

## Allowed paths

- plans/taskcards/TC-4058_understand_silent_failure_and_self_review.md
- src/launcher/workers/understand/worker.py
- tests/unit/workers/test_understand.py

### Allowed paths rationale
- worker.py: contains both `_extract_product_evidence` and `self_review` and artifact writing
- test_understand.py: must verify new behavior

## Implementation steps

### Step 1: Harden _extract_product_evidence failure visibility

Change the outer `try/except Exception` to:
1. Allow `ImportError` and `ModuleNotFoundError` to propagate (broken install = hard stop)
2. Catch all other exceptions but log at `ERROR` level (not `WARNING`) with full traceback
3. Record the failure in the scout artifact so it's visible to human reviewers

### Step 2: Add ProductEvidence check to self_review

Add a `medium`-severity finding when `product_evidence` has zero limitations AND zero
capabilities AND zero supported_formats AND install_recipe is None. This strongly suggests
Phase B.5 failed silently or code_analyzer found nothing.

Do NOT make this `high` severity (it would block the pipeline for repos where code_analyzer
genuinely finds nothing — e.g., sparse repos without format enums).

### Step 3: Add skip_reason_counts to scout_inventory.json

After writing `scout_inventory.json`, augment it with a `skip_reason_counts` dict that
counts how many files were skipped for each reason (budget_exceeded, doc_cap_reached,
source_reserve, file_too_large_for_remaining_budget).

This allows a reviewer to immediately see: "40 files were skipped because the doc cap was
reached — was the cap too aggressive for this repo?"

## Failure modes

### Failure mode 1: ImportError from code_analyzer now propagates and kills pipeline

**Detection**: Pipeline fails at Phase B.5 with ImportError for missing module
**Resolution**: This is CORRECT behavior — a broken import indicates installation issue.
If this blocks a legitimate run, fix the code_analyzer module, not the error handling.
**Gate**: test_understand.py::test_product_evidence_import_error_propagates

### Failure mode 2: ProductEvidence medium finding triggers false positive on sparse repos

**Detection**: Self-review emits medium finding for a genuinely sparse repo
**Resolution**: Medium severity does not block the pipeline — it's informational.
The check is designed to be visible, not blocking.
**Gate**: test_understand.py::test_self_review_passes_with_empty_product_evidence_medium_only

### Failure mode 3: skip_reason_counts fails on large budget_log overflow

**Detection**: budget_log may not have all entries if overflow happened (budget_log_overflow > 0)
**Resolution**: skip_reason_counts is computed from what's IN budget_log; overflow count is
separately recorded. Acknowledge the approximation in the artifact comment.
**Gate**: test_understand.py::test_scout_inventory_has_skip_reason_counts

## Task-specific review checklist

1. [ ] ImportError from code_analyzer now propagates (not swallowed)
2. [ ] Analysis-level errors in Phase B.5 logged at ERROR (not WARNING)
3. [ ] ProductEvidence emptiness finding appears in self_review at medium severity
4. [ ] Finding does NOT block pipeline (severity = "medium", not "high")
5. [ ] scout_inventory.json contains `skip_reason_counts` dict with per-reason counts
6. [ ] All existing 394 understand tests still pass
7. [ ] Docstrings updated for _extract_product_evidence to document new error handling
8. [ ] Spec confirmed no drift (worker_understand.md Phase B.5 still correct)
9. [ ] Schema description fields: scout_inventory.json is not schema-governed (informal)
10. [ ] docs/README.md ownership: no new guides triggered

## Deliverables

1. Updated `src/launcher/workers/understand/worker.py`
2. Updated `tests/unit/workers/test_understand.py` with ≥4 new tests
3. `reports/TC-4058/evidence.md`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v` — all pass
2. [ ] A self_review run on an empty ProductEvidence bundle produces a medium finding
3. [ ] scout_inventory.json written in a test run contains `skip_reason_counts`
4. [ ] ImportError in Phase B.5 propagates (test passes with pytest.raises)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-4058/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k "product_evidence or skip_reason"
```

## Integration boundary proven

**Upstream**: UnderstandWorker receives IntakeBundle from Intake
**Downstream**: Planner receives UnderstandingBundle — product_evidence feeds page generation
**Contract**: UnderstandingBundle.product_evidence must have visible health signal in self_review
