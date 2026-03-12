---
id: TC-A02
title: "Decide target Phase 1 architecture"
status: In-Progress
priority: High
owner: "Orchestrator + Repo Analyst + Reviewer"
updated: "2026-03-13"
tags: [phase1, intake, scout, architecture, review]
depends_on:
  - TC-A01
allowed_paths:
  - plans/taskcards/TC-A02_target_phase1_architecture.md
  - reports/TC-A02/evidence.md
evidence_required:
  - reports/TC-A02/evidence.md
---

# Taskcard TC-A02 - Decide target Phase 1 architecture

## Objective

Choose the target Phase 1 architecture for Intake/acquisition/upstream scouting based on the TC-A01 before-state, and explicitly decide which current boundaries are kept, merged, renamed, or removed.

## Required spec references

- `CLAUDE.md` (Section: AG-002 taskcard-first workflow)
- `agents.md` (Section 2: worker order and entrypoint ownership)
- `plans/twinkly-puzzling-minsky.md` (Rule 2, Rule 4, Rule 7, Rule 9)
- `configs/pipeline.yaml` (current runtime topology)

## Scope

### In scope
- Review the runtime `intake` plus `scout` seam
- Review the `src/launcher/intake/` subsystem boundary against runtime Phase 1
- Define the target ownership model for acquisition, discovery, classification, and scout artifacts
- State which current structure is unacceptable to preserve

### Out of scope
- Code implementation of the new architecture
- Phase 2 Understand contract redesign
- Detailed test implementation

## Inputs

- `reports/TC-A01/evidence.md`
- `src/launcher/workers/intake/worker.py`
- `src/launcher/workers/intake/clone.py`
- `src/launcher/workers/scout/worker.py`
- `src/launcher/workers/scout/scout.py`
- `src/launcher/intake/*.py`
- `configs/pipeline.yaml`

## Outputs

- This taskcard with the approved architecture decision
- `reports/TC-A02/evidence.md` capturing the decision, rationale, and review result

## Allowed paths

- plans/taskcards/TC-A02_target_phase1_architecture.md
- reports/TC-A02/evidence.md

### Allowed paths rationale

TC-A02 is a design gate. It records the architecture decision and reviewer verdict before protected-path source edits begin in TC-A03 and later cards.

## Implementation steps

### Step 1: Reconcile the current runtime and operator-facing boundaries

Use TC-A01 evidence to compare:
- runtime `intake` plus `scout`
- operator-facing `src/launcher/intake/` plus `cli/intake.py`

### Step 2: Decide the target ownership model

State which responsibilities belong to:
- deterministic repo discovery/classification
- deterministic acquisition/clone
- runtime scout inventory
- artifact/report production

### Step 3: Produce reviewer decision

Record the explicit reviewer judgement on whether the current split should be preserved. If not, define the replacement boundary clearly enough to guide TC-A03.

## Failure modes

### Failure mode 1: The decision preserves current naming and package splits without justification

**Detection**: The target design keeps `src/launcher/intake/` and runtime `intake` semantics separate solely because they already exist.
**Resolution**: Re-state Phase 1 around domain ownership and downstream trust, then remove or rename conflicting boundaries.
**Gate**: Reviewer acceptance for TC-A02.

### Failure mode 2: The decision merges stages that have a valid deterministic seam

**Detection**: Acquisition and scout inventory are collapsed without showing why the separate checkpoint or contract is harmful.
**Resolution**: Keep the seam only if it is strict, coherent, and backed by a single Phase 1 domain model.
**Gate**: Architectural clarity and determinism review.

### Failure mode 3: The decision ignores downstream trust artifacts

**Detection**: No unified artifact/report chain is specified for identity, inclusion/exclusion, classification, and acquisition.
**Resolution**: Add an explicit artifact contract to the target Phase 1 design.
**Gate**: Phase 1 inspectability requirement.

## Task-specific review checklist

1. [x] Decision uses TC-A01 evidence rather than preference
2. [x] Runtime `intake` and `scout` seam is explicitly evaluated
3. [x] `src/launcher/intake/` boundary is explicitly accepted, renamed, or rejected
4. [x] Cross-platform correctness is included in the design decision
5. [x] Failure semantics and artifact inspectability are included
6. [x] Reviewer verdict is explicit, not implied
7. [x] Docstrings updated for all new/changed public functions
8. [x] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [x] Schema `"description"` fields present for all new/changed properties
10. [x] Checked `docs/README.md` ownership map - no trigger event applies
11. [x] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `plans/taskcards/TC-A02_target_phase1_architecture.md`
2. `reports/TC-A02/evidence.md`

## Acceptance checks

1. [x] Before-state summary is captured
2. [x] Target architecture decision is written clearly
3. [x] Reviewer has accepted or rejected the target design explicitly

## Self-review

### Verification results
- [x] Tests: not applicable for architecture decision
- [x] Validation: decision cross-checked against current runtime topology and TC-A01 evidence
- [x] Evidence captured: `reports/TC-A02/evidence.md`
- [x] Doc freshness: not applicable; no protected source/config/schema edits

## E2E verification

```bash
Get-Content reports\TC-A01\evidence.md
Get-Content configs\pipeline.yaml
Get-Content src\launcher\workers\scout\worker.py
```

**Expected results**:
- The target design directly answers the current split shown by Phase 1 evidence
- The reviewer verdict is explicit enough to drive TC-A03 implementation

## Integration boundary proven

**Upstream**: TC-A01 before-state evidence.
**Downstream**: TC-A03 refactor and all later Phase 1 implementation/verification cards.
**Contract**: TC-A02 defines the authoritative Phase 1 architecture that implementation must match.
