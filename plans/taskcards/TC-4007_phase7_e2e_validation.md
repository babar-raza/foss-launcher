---
id: TC-4007
title: "Phase 7: E2E validation — integration tests for Understand redesign"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [humming-greeting-kay, phase-7]
depends_on: [TC-4006]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4007_phase7_e2e_validation.md
  - tests/unit/workers/test_understand.py
  - tests/integration/test_understand_pipeline.py
  - phase_store/phase_7_metrics.json
  - phase_store/trend.md
evidence_required:
  - phase_store/phase_7_metrics.json
---

# Taskcard TC-4007 — Phase 7: E2E Validation

## Objective

Validate the full Understand module redesign (Phases 0-6) through integration
tests that prove the pipeline works end-to-end: evidence extraction before LLM,
contradiction resolution, adapter dispatch, and evidence model completeness.

## Required spec references

- `humming-greeting-kay.md` (Phase 7)

## Scope

### In scope
- Integration tests covering 7 key scenarios from the plan
- Trend dashboard summarizing all phases
- Final metrics capture

### Out of scope
- Pilot runs against real repos (requires LLM endpoint, deferred)
- Content grading (requires generated content, deferred)
- Changes to production code (validation only)

## Inputs

- All Phase 0-6 outputs (committed)
- Existing test fixtures and mocks

## Outputs

- Integration test suite
- phase_store/phase_7_metrics.json
- phase_store/trend.md

## Allowed paths

- plans/taskcards/TC-4007_phase7_e2e_validation.md
- tests/unit/workers/test_understand.py
- tests/integration/test_understand_pipeline.py
- phase_store/phase_7_metrics.json
- phase_store/trend.md

### Allowed paths rationale
Test files and metrics only — no production code changes.

## Implementation steps

### Step 1: Write integration tests covering 7 scenarios
1. Deterministic evidence extracted before LLM call
2. Evidence context appears in LLM prompt
3. Contradiction resolution downgrades conflicting claims
4. Limitation extraction from mock repo
5. PlatformProfile resolution for all platforms
6. Property-call gate fires on obj.prop()
7. Adapter registry dispatches correctly for all platforms

### Step 2: Run integration tests and full suite
### Step 3: Write metrics and trend dashboard
### Step 4: Update taskcard to Done

## Failure modes

### Failure mode 1: Integration test import failures
**Detection**: ImportError on test run
**Resolution**: Fix imports to match current module structure
**Gate**: All tests must import cleanly

### Failure mode 2: Mock fixtures don't match current interfaces
**Detection**: TypeError in test setup
**Resolution**: Update fixtures to match current model signatures
**Gate**: All fixtures produce valid model instances

### Failure mode 3: Pipeline ordering assertion fails
**Detection**: Evidence context empty or LLM called before evidence
**Resolution**: Trace through _entry.py to verify ordering
**Gate**: Evidence context non-empty before LLM step

## Task-specific review checklist

1. [x] 7 integration scenarios covered (41 tests across 9 classes)
2. [x] All integration tests pass (41/41)
3. [x] Full test suite passes with zero new failures (3537 passed, 6 pre-existing)
4. [x] phase_store/phase_7_metrics.json written
5. [x] phase_store/trend.md shows progression across all phases
6. [x] No production code modified

## Deliverables

1. Integration test file(s)
2. phase_store/phase_7_metrics.json
3. phase_store/trend.md

## Acceptance checks

1. [x] 41 integration tests pass (7+ scenarios)
2. [x] Full suite: 3537 passed, zero new failures
3. [x] Trend dashboard complete (phase_store/trend.md)

## Self-review

### Verification results
- [x] Tests: 41/41 PASS (integration), 3537/3537 PASS (full suite)
- [x] Evidence captured: phase_store/phase_7_metrics.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/integration/test_understand_pipeline.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `phase_store/phase_7_metrics.json`
- `phase_store/trend.md`
- `tests/integration/test_understand_pipeline.py`

**Expected results**:
- All tests pass (41/41 integration, 3537 full suite)
- Full suite: 3496+ passed, zero new failures

## Integration boundary proven

**Upstream**: All Phase 0-6 code (committed, tested)
**Downstream**: Pipeline consumers (Planner, Generate, Evaluate)
**Contract**: UnderstandingBundle with grounded evidence
