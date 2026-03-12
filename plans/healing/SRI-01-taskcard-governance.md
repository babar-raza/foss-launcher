# SRI-01: AG-002 Taskcard Governance Retrofix

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 1 (Directive Completeness)
**Role:** Governance
**Scope:** Retroactively create the TC that should have existed before intake code was written

---

## Problem

The intake module port (org_scanner, repo_classifier, config_generator, scheduler, config_loader + CLI wiring) was executed without a prior taskcard, violating AG-002 which mandates taskcard-first for all changes under `src/launcher/**`, `configs/**`, `specs/schemas/**`.

## Acceptance Checks

- [ ] A full 14-section taskcard exists at `plans/taskcards/TC-INTAKE-PORT.md`
- [ ] Taskcard references all 5 ported modules + CLI changes + schema + config changes
- [ ] Taskcard status is `Done` (retroactive — work already completed)
- [ ] All 14 mandatory sections filled: Objective, Spec refs, Scope, Inputs, Outputs, Allowed paths, Steps, Failure modes (min 3), Review checklist (min 6), Deliverables, Acceptance checks, Self-review, E2E verification, Integration boundary proven
- [ ] Commit message references the taskcard ID

## Deliverables

1. `plans/taskcards/TC-INTAKE-PORT.md` — full taskcard

## Hard Rules

- Must follow `plans/taskcards/TC-000_TEMPLATE.md` format exactly
- Retroactive status is acceptable but must be noted in the taskcard body

## Review Dimensions

- Governance compliance
- Template completeness (all 14 sections)

## Runbook

1. Copy TC-000_TEMPLATE.md
2. Fill all 14 sections describing the intake port work already done
3. Set status to Done with note: "Retroactive — work completed before taskcard creation"
4. Commit
