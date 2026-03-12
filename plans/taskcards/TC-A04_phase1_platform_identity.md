---
id: TC-A04
title: "Remove Python-default assumptions from generic intake"
status: In-Progress
priority: High
owner: "Refactor Engineer"
updated: "2026-03-13"
tags: [phase1, platform, identity, cross-platform]
depends_on:
  - TC-A03
allowed_paths:
  - plans/taskcards/TC-A04_phase1_platform_identity.md
  - reports/TC-A04/evidence.md
  - src/launcher/phase1/classification.py
  - src/launcher/phase1/config_generator.py
  - src/launcher/phase1/config_loader.py
  - src/launcher/phase1/inspection.py
  - src/launcher/cli/intake.py
  - src/launcher/intake/config_generator.py
  - src/launcher/intake/config_loader.py
  - src/launcher/intake/repo_classifier.py
  - src/launcher/shared/identity.py
  - src/launcher/workers/intake/worker.py
  - tests/unit/intake/test_classifier.py
  - tests/unit/intake/test_config_generator.py
  - tests/unit/workers/test_intake.py
evidence_required:
  - reports/TC-A04/evidence.md
---

# Taskcard TC-A04 - Remove Python-default assumptions from generic intake

## Objective

Ensure generic Phase 1 identity, platform resolution, and classification do not degrade non-Python repositories through Python-default assumptions.

## Required spec references

- `reports/TC-A02/evidence.md`
- `configs/families.yaml`

## Scope

### In scope
- platform resolution
- canonical identity derivation
- classifier defaults
- config generation defaults that affect cross-platform correctness

### Out of scope
- Understand extraction logic

## Inputs

- Phase 1 domain modules
- worker intake identity handling
- intake-related tests

## Outputs

- Cross-platform-hardended Phase 1 logic
- Tests and evidence report

## Allowed paths

- plans/taskcards/TC-A04_phase1_platform_identity.md
- reports/TC-A04/evidence.md
- src/launcher/phase1/classification.py
- src/launcher/phase1/config_generator.py
- src/launcher/phase1/config_loader.py
- src/launcher/phase1/inspection.py
- src/launcher/cli/intake.py
- src/launcher/intake/config_generator.py
- src/launcher/intake/config_loader.py
- src/launcher/intake/repo_classifier.py
- src/launcher/shared/identity.py
- src/launcher/workers/intake/worker.py
- tests/unit/intake/test_classifier.py
- tests/unit/intake/test_config_generator.py
- tests/unit/workers/test_intake.py

### Allowed paths rationale

These files contain the current cross-platform and Python-default behavior.

## Implementation steps

### Step 1: Remove Python-default classifier and config behavior

### Step 2: Ensure identity/platform resolution is platform-aware across CLI and runtime

### Step 3: Add Python and non-Python fixture coverage

## Failure modes

### Failure mode 1: Python-specific defaults survive in generic paths

**Detection**: non-Python fixtures still derive Python-shaped imports or classifications.
**Resolution**: replace generic defaults with explicit platform-aware rules and provenance.
**Gate**: TC-A04 exit criteria.

### Failure mode 2: Runtime and CLI disagree on platform/identity

**Detection**: same repo resolves differently depending on entrypoint.
**Resolution**: force both to use the same shared functions.
**Gate**: Cross-platform correctness requirement.

### Failure mode 3: Removing Python defaults breaks Python repos

**Detection**: Python fixtures regress.
**Resolution**: keep Python as one supported platform, not the implicit generic baseline.
**Gate**: Fixture coverage for both Python and non-Python repos.

## Task-specific review checklist

1. [ ] No generic `require_python` primary path remains
2. [ ] Non-Python canonical identity no longer degrades to Python-shaped defaults
3. [ ] Runtime and CLI share platform resolution
4. [ ] Python fixture still passes
5. [ ] Non-Python fixture now behaves correctly
6. [ ] Before/after behavior recorded
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map - update if triggered
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Cross-platform Phase 1 source changes
2. `reports/TC-A04/evidence.md`

## Acceptance checks

1. [ ] Python and non-Python fixtures covered
2. [ ] Non-Python fixture no longer degrades due to Python assumptions
3. [ ] Runtime and CLI identities are aligned

## Self-review

### Verification results
- [ ] Tests: pending
- [ ] Validation: pending
- [ ] Evidence captured: `reports/TC-A04/evidence.md`
- [ ] Doc freshness: pending

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_classifier.py tests/unit/intake/test_config_generator.py tests/unit/workers/test_intake.py -v
```

**Expected results**:
- Python and non-Python fixtures both resolve correctly
- No Python-shaped fallback contaminates generic intake

## Integration boundary proven

**Upstream**: TC-A03 shared Phase 1 domain.
**Downstream**: TC-A05 failure/rescan hardening and final verification.
**Contract**: Platform/identity logic is shared and cross-platform-correct.
