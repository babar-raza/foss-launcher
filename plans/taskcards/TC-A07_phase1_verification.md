---
id: TC-A07
title: "Verify Phase 1 with fixtures and manual review"
status: Done
priority: High
owner: "Verification Engineer + Output Auditor"
updated: "2026-03-13"
tags: [phase1, verification, manual-audit]
depends_on:
  - TC-A03
  - TC-A04
  - TC-A05
  - TC-A06
allowed_paths:
  - plans/taskcards/TC-A07_phase1_verification.md
  - reports/TC-A07/evidence.md
evidence_required:
  - reports/TC-A07/evidence.md
---

# Taskcard TC-A07 - Verify Phase 1 with fixtures and manual review

## Objective

Run Phase 1 on controlled Python, non-Python, and edge-case repositories; inspect the produced artifacts manually; and recommend GO or NO-GO.

## Required spec references

- `reports/TC-A03/evidence.md`
- `reports/TC-A04/evidence.md`
- `reports/TC-A05/evidence.md`
- `reports/TC-A06/evidence.md`

## Scope

### In scope
- test execution
- local fixture inspection
- artifact review
- recommendation

### Out of scope
- additional refactors

## Inputs

- Phase 1 code and tests
- local controlled repos for audit

## Outputs

- verification evidence report

## Allowed paths

- plans/taskcards/TC-A07_phase1_verification.md
- reports/TC-A07/evidence.md

### Allowed paths rationale

TC-A07 is verification-only.

## Implementation steps

### Step 1: Run Phase 1-focused tests

### Step 2: Produce manual audit artifacts from controlled repos

### Step 3: Record Output Auditor notes and recommendation

## Failure modes

### Failure mode 1: verification relies only on unit tests

**Detection**: no manual artifact notes are present.
**Resolution**: inspect actual JSON artifacts from controlled repos.
**Gate**: Output Auditor requirement.

### Failure mode 2: verification ignores negative cases

**Detection**: no failure-mode artifact or error output is recorded.
**Resolution**: include a bad repository case.
**Gate**: Phase 1 audit requirement.

### Failure mode 3: recommendation omits remaining weaknesses

**Detection**: GO/NO-GO is stated without residual risks.
**Resolution**: write remaining weakness list explicitly.
**Gate**: stop-decision quality bar.

## Task-specific review checklist

1. [x] Python controlled repo audited
2. [x] Non-Python controlled repo audited
3. [x] Edge-case repo audited
4. [x] Negative failure case recorded
5. [x] Tests run with `PYTHONHASHSEED=0`
6. [x] Recommendation is explicit
7. [x] Docstrings updated for all new/changed public functions
8. [x] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [x] Schema `"description"` fields present for all new/changed properties
10. [x] Checked `docs/README.md` ownership map - no trigger event applies
11. [x] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `reports/TC-A07/evidence.md`

## Acceptance checks

1. [x] Outputs reviewed manually
2. [x] Findings written
3. [x] Recommendation explicitly written

## Self-review

### Verification results
- [x] Tests: Phase 1 slice passed
- [x] Validation: manual artifact review completed
- [x] Evidence captured: `reports/TC-A07/evidence.md`
- [x] Doc freshness: not run; no `src/launcher/**` behavior is being marked Done outside the Phase 1 evidence pack itself

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_classifier.py tests/unit/intake/test_intake_cli.py tests/unit/workers/test_intake.py tests/unit/workers/test_scout.py tests/integration/test_intake_understand_flow.py -q
```

**Expected results**:
- Phase 1 test slice passes
- manual artifacts exist for controlled repos

## Integration boundary proven

**Upstream**: TC-A03 through TC-A06.
**Downstream**: TC-A08 final review.
**Contract**: verification states whether Phase 1 is trustworthy enough to proceed.
