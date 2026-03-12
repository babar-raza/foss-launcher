---
id: TC-A06
title: "Add inspectable Phase 1 artifacts"
status: In-Progress
priority: High
owner: "Refactor Engineer"
updated: "2026-03-13"
tags: [phase1, artifacts, auditability]
depends_on:
  - TC-A03
allowed_paths:
  - plans/taskcards/TC-A06_phase1_artifacts.md
  - reports/TC-A06/evidence.md
  - src/launcher/phase1/acquisition.py
  - src/launcher/phase1/classification.py
  - src/launcher/phase1/inspection.py
  - src/launcher/phase1/scheduler.py
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/scout/scout.py
  - src/launcher/workers/scout/worker.py
  - tests/unit/workers/test_intake.py
  - tests/unit/workers/test_scout.py
  - tests/integration/test_intake_understand_flow.py
evidence_required:
  - reports/TC-A06/evidence.md
---

# Taskcard TC-A06 - Add inspectable Phase 1 artifacts

## Objective

Produce Phase 1 artifacts that a human can inspect to understand identity, platform, inclusion/exclusion, classification, acquisition result, and scout inventory without reading code.

## Required spec references

- `reports/TC-A02/evidence.md`
- `agents.md`

## Scope

### In scope
- acquisition artifact content
- classification/selection artifact content
- scout artifact content
- integration tests proving those artifacts exist

### Out of scope
- Understand artifacts

## Inputs

- Refactored Phase 1 domain
- runtime intake and scout workers

## Outputs

- Inspectable Phase 1 artifacts
- Tests and evidence report

## Allowed paths

- plans/taskcards/TC-A06_phase1_artifacts.md
- reports/TC-A06/evidence.md
- src/launcher/phase1/acquisition.py
- src/launcher/phase1/classification.py
- src/launcher/phase1/inspection.py
- src/launcher/phase1/scheduler.py
- src/launcher/workers/intake/worker.py
- src/launcher/workers/scout/scout.py
- src/launcher/workers/scout/worker.py
- tests/unit/workers/test_intake.py
- tests/unit/workers/test_scout.py
- tests/integration/test_intake_understand_flow.py

### Allowed paths rationale

These files own the Phase 1 artifact content, including scout shared-facts fidelity, and the tests that prove inspectability.

## Implementation steps

### Step 1: Define shared human-reviewable artifact fields

### Step 2: Emit those artifacts from acquisition and scout paths

### Step 3: Add tests for artifact presence and core fields

## Failure modes

### Failure mode 1: artifacts exist but still require code reading to interpret

**Detection**: artifact fields lack reasons, provenance, or explicit decisions.
**Resolution**: add self-describing keys and reason fields.
**Gate**: Phase 1 manual inspectability requirement.

### Failure mode 2: runtime and operator artifacts cannot be correlated

**Detection**: artifacts lack shared repo identifiers or consistent field names.
**Resolution**: align identifiers and field naming.
**Gate**: Single trustworthy Phase 1 foundation requirement.

### Failure mode 3: artifact coverage ignores negative cases

**Detection**: failure-mode artifact output cannot be reviewed.
**Resolution**: include explicit failure state or report paths in tests/manual audit.
**Gate**: Output Auditor requirements.

## Task-specific review checklist

1. [ ] Acquisition artifact is human-readable
2. [ ] Classification/selection artifact is human-readable
3. [ ] Scout artifact is human-readable
4. [ ] Shared identifiers connect the artifact chain
5. [ ] Failure mode output is inspectable
6. [ ] Artifact tests exist
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map - update if triggered
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Improved Phase 1 artifacts
2. `reports/TC-A06/evidence.md`

## Acceptance checks

1. [ ] Human can inspect identity, platform, inclusion/exclusion, and acquisition result
2. [ ] Artifact paths and samples are captured
3. [ ] Artifact tests pass

## Self-review

### Verification results
- [ ] Tests: pending
- [ ] Validation: pending
- [ ] Evidence captured: `reports/TC-A06/evidence.md`
- [ ] Doc freshness: pending

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py tests/unit/workers/test_scout.py tests/integration/test_intake_understand_flow.py -v
```

**Expected results**:
- Phase 1 artifacts are emitted and reviewable
- Integration flow exposes Phase 1 outputs cleanly

## Integration boundary proven

**Upstream**: TC-A03 through TC-A05.
**Downstream**: TC-A07 manual audit.
**Contract**: Phase 1 artifact chain is reviewable by humans and usable by downstream agents.
