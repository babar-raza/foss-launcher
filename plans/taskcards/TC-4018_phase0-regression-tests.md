---
id: TC-4018
title: "Phase 0 regression tests — 5 patches, one test each in TestPhase0Regressions"
status: Done
priority: Medium
owner: "orchestrator"
updated: "2026-03-11"
tags: [humming-greeting-kay, hg-08, regression, tests]
depends_on: [TC-4001]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4018_phase0-regression-tests.md
  - tests/unit/workers/test_evaluate.py
evidence_required:
  - phase_store/TC-4018_evidence.md
---

# Taskcard TC-4018 — Phase 0 Regression Tests

## Objective

Phase 0 fixed 5 bugs (P1-P5) in the evaluate worker. No regression tests were written.
This taskcard adds a `TestPhase0Regressions` class with exactly 5 regression tests,
one per patch, so any future regression to these bugs would be caught.

Individual test classes (TestPhase0P1, P2, P3, P5) already exist from prior work but
are not in the required unified class, and P4 is missing entirely.

## Required spec references

- `src/launcher/workers/evaluate/worker.py` (P1: coverage, P4: page_content_cache)
- `src/launcher/workers/evaluate/checks/contradiction.py` (P2: m.group(1))
- `src/launcher/workers/evaluate/cross_page_review.py` (P3: negation)
- `src/launcher/workers/evaluate/checks/format_truth.py` (P5: dynamic format list)

## Scope

### In scope

- Create `TestPhase0Regressions` class in `test_evaluate.py`
- Exactly 5 test methods (one per P1-P5 bug)
- P4 is the new one: `test_page_content_cache_populated_before_early_return`

### Out of scope

- Changing any production code
- Removing existing TestPhase0P1/P2/P3/P5 classes

## Inputs

- Existing evaluate code (all bugs already fixed — tests confirm fixes)
- HG-08 spec: `plans/healing/HG-08-phase0-regression-tests.md`

## Outputs

- 5 new tests in `TestPhase0Regressions` in `tests/unit/workers/test_evaluate.py`

## Allowed paths

- plans/taskcards/TC-4018_phase0-regression-tests.md
- tests/unit/workers/test_evaluate.py

### Allowed paths rationale

Only the test file needs changes.

## Implementation steps

### Step 1: Add TestPhase0Regressions class

Add at end of `test_evaluate.py` with 5 test methods.

### Step 2: Verify all 5 pass

Run: `pytest tests/unit/workers/test_evaluate.py -k "Phase0" -v`

## Failure modes

### Failure mode 1: P4 test is hard to write without running worker.py

**Detection**: Test requires complex mocking
**Resolution**: Test `_compute_api_surface_coverage` with a cache that simulates early-return population
**Gate**: Unit test

### Failure mode 2: Test imports not available

**Detection**: ImportError on _compute_api_surface_coverage or check functions
**Resolution**: Use venv python; functions are already imported in other test classes
**Gate**: pytest collection

### Failure mode 3: P4 test is brittle (relies on internal worker structure)

**Detection**: Test fails with unrelated changes
**Resolution**: Test only the public _compute_api_surface_coverage behavior, not internal cache
**Gate**: Unit test

## Task-specific review checklist

- [ ] `TestPhase0Regressions` class exists in test_evaluate.py
- [ ] Exactly 5 test methods (one per P1-P5)
- [ ] Each test has comment documenting which bug it covers
- [ ] All 5 tests pass
- [ ] No new failures in full suite

## Deliverables

1. 5 regression tests in `TestPhase0Regressions` in `tests/unit/workers/test_evaluate.py`

## Acceptance checks

- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -k "Phase0" -v` — all pass
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — zero new failures

## Self-review

(to be filled after implementation)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py \
  -k "Phase0Regressions" -v
# Expected: 5 passed
```

**Expected artifacts**:
- `tests/unit/workers/test_evaluate.py` — `TestPhase0Regressions` class appended

## Integration boundary proven

**Upstream**: Phase 0 bug fixes in evaluate worker (P1-P5)
**Downstream**: These tests act as regression guards — any future regression to P1-P5 bugs will be caught by CI
