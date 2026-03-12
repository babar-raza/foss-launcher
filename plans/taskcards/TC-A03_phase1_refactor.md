---
id: TC-A03
title: "Refactor Phase 1 to single trustworthy acquisition path"
status: In-Progress
priority: High
owner: "Refactor Engineer"
updated: "2026-03-13"
tags: [phase1, refactor, acquisition, scout]
depends_on:
  - TC-A02
allowed_paths:
  - plans/taskcards/TC-A03_phase1_refactor.md
  - reports/TC-A03/evidence.md
  - src/launcher/phase1/__init__.py
  - src/launcher/phase1/acquisition.py
  - src/launcher/phase1/classification.py
  - src/launcher/phase1/config_generator.py
  - src/launcher/phase1/config_loader.py
  - src/launcher/phase1/discovery.py
  - src/launcher/phase1/inspection.py
  - src/launcher/phase1/scheduler.py
  - src/launcher/cli/intake.py
  - src/launcher/intake/__init__.py
  - src/launcher/intake/config_generator.py
  - src/launcher/intake/config_loader.py
  - src/launcher/intake/org_scanner.py
  - src/launcher/intake/repo_classifier.py
  - src/launcher/intake/scheduler.py
  - src/launcher/workers/intake/clone.py
  - src/launcher/workers/intake/worker.py
evidence_required:
  - reports/TC-A03/evidence.md
---

# Taskcard TC-A03 - Refactor Phase 1 to single trustworthy acquisition path

## Objective

Implement the TC-A02 architecture decision so Phase 1 becomes one coherent acquisition/scout domain instead of a pipeline intake worker plus a separate semantic intake subsystem.

## Required spec references

- `agents.md`
- `plans/twinkly-puzzling-minsky.md`
- `configs/pipeline.yaml`
- `reports/TC-A02/evidence.md`

## Scope

### In scope
- Create a shared Phase 1 domain package
- Move or wrap conflicting operator-facing intake logic under the new domain
- Route runtime intake worker and CLI entrypoints through the shared Phase 1 domain

### Out of scope
- Final Phase 1 verification
- Phase 2 Understand changes

## Inputs

- Current runtime and CLI Phase 1 modules
- TC-A01 and TC-A02 evidence

## Outputs

- Refactored Phase 1 shared domain
- Updated worker/CLI imports
- Evidence report

## Allowed paths

- plans/taskcards/TC-A03_phase1_refactor.md
- reports/TC-A03/evidence.md
- src/launcher/phase1/__init__.py
- src/launcher/phase1/acquisition.py
- src/launcher/phase1/classification.py
- src/launcher/phase1/config_generator.py
- src/launcher/phase1/config_loader.py
- src/launcher/phase1/discovery.py
- src/launcher/phase1/inspection.py
- src/launcher/phase1/scheduler.py
- src/launcher/cli/intake.py
- src/launcher/intake/__init__.py
- src/launcher/intake/config_generator.py
- src/launcher/intake/config_loader.py
- src/launcher/intake/org_scanner.py
- src/launcher/intake/repo_classifier.py
- src/launcher/intake/scheduler.py
- src/launcher/workers/intake/clone.py
- src/launcher/workers/intake/worker.py

### Allowed paths rationale

These are the Phase 1 domain files whose ownership and imports must change to remove the conflicting boundary.

## Implementation steps

### Step 1: Create shared Phase 1 domain modules

### Step 2: Route runtime worker and CLI through the shared domain

### Step 3: Reduce old `src/launcher/intake/` package to compatibility wrappers only if still needed

## Failure modes

### Failure mode 1: Refactor changes names but preserves duplicate logic

**Detection**: Old and new modules both contain active classification/platform logic.
**Resolution**: Consolidate the logic into shared Phase 1 modules and leave only thin wrappers.
**Gate**: TC-A03 exit criteria.

### Failure mode 2: Runtime acquisition path still bypasses shared Phase 1 services

**Detection**: `IntakeWorker` continues to own clone/provenance logic independently.
**Resolution**: Move acquisition logic behind a shared service and use it from the worker.
**Gate**: Single trustworthy acquisition path requirement.

### Failure mode 3: CLI breaks because wrappers and imports drift

**Detection**: intake CLI or unit tests fail after the package move.
**Resolution**: Update imports and add compatibility shims only where required.
**Gate**: Verification in TC-A07.

## Task-specific review checklist

1. [ ] Shared Phase 1 package exists
2. [ ] Runtime intake worker uses shared acquisition logic
3. [ ] CLI uses shared Phase 1 domain modules
4. [ ] Duplicate/conflicting flow removed or demoted to wrappers
5. [ ] Responsibility map is explicit in evidence
6. [ ] No Phase 2 files changed
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map - update if triggered
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Refactored Phase 1 source files
2. `reports/TC-A03/evidence.md`

## Acceptance checks

1. [ ] Duplicate or conflicting flow removed
2. [ ] Acquisition path explicit and coherent
3. [ ] CLI and runtime Phase 1 now share one domain

## Self-review

### Verification results
- [ ] Tests: pending
- [ ] Validation: pending
- [ ] Evidence captured: `reports/TC-A03/evidence.md`
- [ ] Doc freshness: pending

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake tests/unit/workers/test_intake.py -v
```

**Expected results**:
- Shared Phase 1 imports work
- Runtime intake and CLI intake both use the same refactored domain

## Integration boundary proven

**Upstream**: TC-A02 architecture decision.
**Downstream**: TC-A04 through TC-A07.
**Contract**: One coherent Phase 1 domain with a strict runtime acquisition/scout seam.
