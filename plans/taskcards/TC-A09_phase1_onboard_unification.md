---
id: TC-A09
title: "Unify Phase 1 batch onboarding with source-grounded inspection"
status: Done
priority: High
owner: "Refactor Engineer + Verification Engineer"
updated: "2026-03-13"
tags: [phase1, onboard, refactor]
depends_on:
  - TC-A08
allowed_paths:
  - plans/taskcards/TC-A09_phase1_onboard_unification.md
  - reports/TC-A09/evidence.md
  - src/launcher/cli/intake.py
  - src/launcher/intake/scheduler.py
  - src/launcher/phase1/onboarding.py
  - tests/unit/intake/test_intake_cli.py
evidence_required:
  - reports/TC-A09/evidence.md
---

# Taskcard TC-A09 - Unify Phase 1 batch onboarding with source-grounded inspection

## Objective

Move `launch intake onboard` onto the same source-grounded inspection and classification contract already used by repo-level classify/generate so batch onboarding no longer bypasses Phase 1 trust checks.

## Required spec references

- `reports/TC-A07/evidence.md`
- `reports/TC-A08/evidence.md`

## Scope

### In scope
- onboarding control flow
- batch inspection/classification
- onboarding artifact emission
- targeted CLI verification

### Out of scope
- scan transport changes
- Phase 2 understand work

## Inputs

- `src/launcher/cli/intake.py`
- `src/launcher/intake/scheduler.py`
- `src/launcher/phase1/inspection.py`
- `src/launcher/phase1/classification.py`
- `tests/unit/intake/test_intake_cli.py`

## Outputs

- unified batch onboarding path
- onboarding evidence report

## Allowed paths

- plans/taskcards/TC-A09_phase1_onboard_unification.md
- reports/TC-A09/evidence.md
- src/launcher/cli/intake.py
- src/launcher/intake/scheduler.py
- src/launcher/phase1/onboarding.py
- tests/unit/intake/test_intake_cli.py

### Allowed paths rationale

TC-A09 is limited to the remaining Phase 1 blocker: onboarding still bypasses source-grounded inspection.

## Implementation steps

### Step 1: Replace metadata-only batch classification with source-grounded inspection

### Step 2: Emit reviewable onboarding artifacts and explicit processed/skipped reasons

### Step 3: Add targeted tests for dry-run, generation, and negative onboarding cases

## Failure modes

### Failure mode 1: onboarding still generates configs without clone-backed inspection

**Detection**: tests pass without `inspect_repo` being called.
**Resolution**: make inspection mandatory before classification/generation.
**Gate**: Phase 1 stop gate on trustworthy acquisition path.

### Failure mode 2: onboarding hides repo-level decisions inside summary counts only

**Detection**: report lacks per-repo classification reasons or artifact paths.
**Resolution**: emit explicit processed and classification entries.
**Gate**: artifact inspectability requirement.

### Failure mode 3: negative repo states remain batch-silent

**Detection**: ineligible repos disappear without source-grounded reason.
**Resolution**: persist classification decisions from inspection for all inspected repos.
**Gate**: Output Auditor trust requirement.

## Task-specific review checklist

1. [x] `onboard` uses source-grounded inspection before classification
2. [x] generated configs require eligible inspection result
3. [x] dry-run still exposes artifact and decision details
4. [x] targeted CLI tests cover positive and negative batch cases
5. [x] evidence report records commands and artifact paths

## Deliverables

1. `reports/TC-A09/evidence.md`

## Acceptance checks

1. [x] batch onboarding no longer bypasses inspection
2. [x] per-repo onboarding decisions are inspectable
3. [x] targeted verification passes

## Self-review

### Verification results
- [x] Tests
- [x] Validation
- [x] Evidence captured
- [x] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~1` EXIT 1; flagged unrelated pre-existing drift in `src/launcher/workers/generate/section_validator.py` vs `specs/worker_generate.md`. No Phase 1 onboarding spec drift was reported for the files changed in this taskcard.

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_intake_cli.py -q
```

**Expected results**:
- batch onboarding uses the same source-grounded contract as single-repo flows

## Integration boundary proven

**Upstream**: org scanning still provides candidate repos.
**Downstream**: onboarding output becomes trustworthy enough for final Phase 1 review.
**Contract**: no batch candidate is generated without source-grounded inspection and explicit artifact evidence.
