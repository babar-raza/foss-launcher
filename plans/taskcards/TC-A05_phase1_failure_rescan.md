---
id: TC-A05
title: "Harden failure behavior and rescan behavior"
status: In-Progress
priority: High
owner: "Refactor Engineer + Verification Engineer"
updated: "2026-03-13"
tags: [phase1, failures, rescan, verification]
depends_on:
  - TC-A03
allowed_paths:
  - plans/taskcards/TC-A05_phase1_failure_rescan.md
  - reports/TC-A05/evidence.md
  - src/launcher/phase1/acquisition.py
  - src/launcher/phase1/discovery.py
  - src/launcher/phase1/inspection.py
  - src/launcher/phase1/scheduler.py
  - src/launcher/intake/org_scanner.py
  - src/launcher/intake/scheduler.py
  - src/launcher/workers/intake/clone.py
  - src/launcher/workers/intake/worker.py
  - tests/unit/intake/test_org_scanner.py
  - tests/unit/intake/test_scheduler.py
  - tests/unit/workers/intake/test_clone.py
  - tests/unit/workers/test_intake.py
evidence_required:
  - reports/TC-A05/evidence.md
---

# Taskcard TC-A05 - Harden failure behavior and rescan behavior

## Objective

Replace silent or ambiguous bad-state continuation in Phase 1 with explicit hard-fail or explicit-state handling, and make rescan behavior intentional and reviewable.

## Required spec references

- `reports/TC-A02/evidence.md`
- `agents.md`

## Scope

### In scope
- clone/acquisition failures
- unusable local state
- rescan behavior and skipped/seen repo semantics
- tests for negative cases

### Out of scope
- Understand failure semantics

## Inputs

- acquisition/discovery modules
- current scanner and clone tests

## Outputs

- Hardened Phase 1 failure behavior
- Rescan handling tests
- Evidence report

## Allowed paths

- plans/taskcards/TC-A05_phase1_failure_rescan.md
- reports/TC-A05/evidence.md
- src/launcher/phase1/acquisition.py
- src/launcher/phase1/discovery.py
- src/launcher/phase1/inspection.py
- src/launcher/phase1/scheduler.py
- src/launcher/intake/org_scanner.py
- src/launcher/intake/scheduler.py
- src/launcher/workers/intake/clone.py
- src/launcher/workers/intake/worker.py
- tests/unit/intake/test_org_scanner.py
- tests/unit/intake/test_scheduler.py
- tests/unit/workers/intake/test_clone.py
- tests/unit/workers/test_intake.py

### Allowed paths rationale

These files own the current failure and rescan semantics.

## Implementation steps

### Step 1: Enforce hard-fail on unusable acquisition state

### Step 2: Make rescan behavior explicit in reports and tests

### Step 3: Add negative-case verification

## Failure modes

### Failure mode 1: broken clone still yields downstream-usable state

**Detection**: worker artifacts or bundles exist after a failed acquisition.
**Resolution**: fail before bundle creation and assert in tests.
**Gate**: Phase 1 stop gate.

### Failure mode 2: rescan still hides skipped/seen repo behavior

**Detection**: reports do not show whether repos were skipped due to prior state or intentionally rescanned.
**Resolution**: make state transitions and counts explicit in artifacts/tests.
**Gate**: TC-A05 exit criteria.

### Failure mode 3: failure hardening only logs warnings

**Detection**: code logs warning where downstream trust depends on stopping.
**Resolution**: raise exceptions for unusable states; reserve warnings for non-authoritative auxiliary writes.
**Gate**: Failure semantics requirement.

## Task-specific review checklist

1. [ ] Unusable acquisition state cannot continue
2. [ ] Negative clone case is tested
3. [ ] Rescan behavior is explicit and tested
4. [ ] Skipped/seen state is reviewable in output
5. [ ] No silent bad-state continuation remains
6. [ ] Before/after failure behavior is documented
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map - update if triggered
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Hardened failure/rescan code
2. `reports/TC-A05/evidence.md`

## Acceptance checks

1. [ ] Clone failure test exists and passes
2. [ ] Rescan behavior test exists and passes
3. [ ] Unusable acquisition state cannot silently proceed

## Self-review

### Verification results
- [ ] Tests: pending
- [ ] Validation: pending
- [ ] Evidence captured: `reports/TC-A05/evidence.md`
- [ ] Doc freshness: pending

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_org_scanner.py tests/unit/intake/test_scheduler.py tests/unit/workers/intake/test_clone.py tests/unit/workers/test_intake.py -v
```

**Expected results**:
- Clone failure hard-stops
- Rescan behavior is intentional and transparent

## Integration boundary proven

**Upstream**: TC-A03/TC-A04.
**Downstream**: TC-A06/TC-A07.
**Contract**: Phase 1 failure state and rescan state are explicit and testable.
