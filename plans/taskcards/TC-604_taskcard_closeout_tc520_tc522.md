---
id: TC-604
title: "Taskcard closeout for TC-520 and TC-522"
status: In-Progress
owner: "CLOSEOUT_AGENT"
updated: "2026-01-29"
depends_on:
  - TC-520
  - TC-522
allowed_paths:
  - plans/taskcards/TC-520_pilots_and_regression.md
  - plans/taskcards/TC-522_pilot_e2e_cli.md
  - plans/taskcards/TC-604_taskcard_closeout_tc520_tc522.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-604/**
evidence_required:
  - reports/agents/<agent>/TC-604/report.md
  - reports/agents/<agent>/TC-604/self_review.md
spec_ref: 718bca53173dd5e27a819d24a63e9afbd303b709
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-604 — Taskcard closeout for TC-520 and TC-522

## Objective
Mark TC-520 (Pilots and regression harness) and TC-522 (Pilot E2E CLI execution) as Done after verifying all acceptance criteria are met, all tests pass, and comprehensive evidence reports exist.

## Required spec references
- plans/taskcards/00_TASKCARD_CONTRACT.md (Definition of done)
- specs/09_validation_gates.md (Gate B - taskcard validation, Gate C - status board generation)

## Scope
### In scope
- Verify TC-520 and TC-522 completion status
- Change TC-520 frontmatter status from "In-Progress" to "Done"
- Change TC-522 frontmatter status from "In-Progress" to "Done"
- Add TC-604 to INDEX.md
- Regenerate STATUS_BOARD.md via Gate C
- Document verification evidence

### Out of scope
- Modifying implementation code for TC-520 or TC-522
- Creating new tests or evidence (must already exist)
- Modifying any shared libraries

## Inputs
- plans/taskcards/TC-520_pilots_and_regression.md (current status: In-Progress)
- plans/taskcards/TC-522_pilot_e2e_cli.md (current status: In-Progress)
- reports/agents/TELEMETRY_AGENT/TC-520/report.md (status: COMPLETE)
- reports/agents/TELEMETRY_AGENT/TC-522/report.md (status: COMPLETE)
- plans/taskcards/00_TASKCARD_CONTRACT.md (definition of done)

## Outputs
- TC-520 with status: Done
- TC-522 with status: Done
- TC-604 added to INDEX.md
- STATUS_BOARD.md regenerated with updated statuses
- Evidence report documenting verification and changes

## Allowed paths

- `plans/taskcards/TC-520_pilots_and_regression.md`
- `plans/taskcards/TC-522_pilot_e2e_cli.md`
- `plans/taskcards/TC-604_taskcard_closeout_tc520_tc522.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-604/**`## Preconditions / dependencies
- TC-520: Implementation complete, tests passing, reports exist
- TC-522: Implementation complete, tests passing, reports exist
- All validation gates passing

## Implementation steps
1) Verify TC-520 completion:
   - Read report.md and self_review.md
   - Confirm all acceptance criteria met
   - Verify test results show 100% pass
2) Verify TC-522 completion:
   - Read report.md and self_review.md
   - Confirm all acceptance criteria met
   - Verify test results show 100% pass
3) Run validate_swarm_ready.py to confirm all gates pass
4) Edit TC-520: Change `status: In-Progress` to `status: Done` in frontmatter
5) Edit TC-522: Change `status: In-Progress` to `status: Done` in frontmatter
6) Add TC-604 entry to INDEX.md
7) Run validate_swarm_ready.py again to regenerate STATUS_BOARD.md and verify gates still pass
8) Create evidence report with verification results and git diffs

## Test plan
- Validate changes with git diff
- Verify frontmatter-only changes (no body modifications)
- Run validate_swarm_ready.py before and after changes
- Confirm STATUS_BOARD.md reflects Done status

## E2E verification
**Concrete command(s) to run:**
```bash
.venv\Scripts\python.exe tools/validate_swarm_ready.py
git diff plans/taskcards/TC-520_pilots_and_regression.md
git diff plans/taskcards/TC-522_pilot_e2e_cli.md
git diff plans/taskcards/INDEX.md
```

**Expected artifacts:**
- Modified files: TC-520, TC-522, TC-604, INDEX.md, STATUS_BOARD.md
- reports/agents/<agent>/TC-604/report.md
- reports/agents/<agent>/TC-604/self_review.md

**Success criteria:**
- [ ] TC-520 and TC-522 verified as complete (reports show COMPLETE, tests pass)
- [ ] TC-520 status changed to Done in frontmatter
- [ ] TC-522 status changed to Done in frontmatter
- [ ] TC-604 added to INDEX.md
- [ ] STATUS_BOARD.md regenerated showing Done status
- [ ] All validation gates still pass

## Integration boundary proven
- Upstream: TC-520 and TC-522 implementation complete
- Downstream: STATUS_BOARD.md generation, taskcard validation
- Contracts: Taskcard frontmatter schema, definition of done, Gate C

## Failure modes

### Failure mode 1: Taskcards marked Done prematurely despite incomplete deliverables
**Detection:** Reports show incomplete status, tests failing, or missing evidence files; acceptance criteria not all met
**Resolution:** Do not mark as Done; review taskcard contract definition of done (all deliverables complete, all tests passing, all evidence reports exist); return taskcards to owners for completion
**Spec/Gate:** plans/taskcards/00_TASKCARD_CONTRACT.md (definition of done)

### Failure mode 2: Validation gates fail after status change to Done
**Detection:** validate_swarm_ready.py exits non-zero after marking taskcards Done; new gate failures introduced
**Resolution:** Review specific gate failure messages; verify status change didn't break dependencies or contracts; revert status changes if gates fail; fix underlying issue before re-attempting closeout
**Spec/Gate:** specs/09_validation_gates.md (all gates must pass)

### Failure mode 3: STATUS_BOARD.md not auto-regenerated after status changes
**Detection:** STATUS_BOARD.md does not reflect updated Done statuses; still shows In-Progress
**Resolution:** Manually run Gate C via validate_swarm_ready.py to force regeneration; verify STATUS_BOARD.md is not in .gitignore; check file permissions allow writing
**Spec/Gate:** specs/09_validation_gates.md (Gate C - status board generation)

## Task-specific review checklist
- [ ] TC-520 report confirms COMPLETE status
- [ ] TC-522 report confirms COMPLETE status
- [ ] All tests passing for both taskcards
- [ ] Only frontmatter status field changed
- [ ] TC-604 added to INDEX.md
- [ ] STATUS_BOARD.md regenerated
- [ ] All gates still passing
- [ ] Evidence report includes verification details

## Deliverables
- Modified files:
  - plans/taskcards/TC-520_pilots_and_regression.md
  - plans/taskcards/TC-522_pilot_e2e_cli.md
  - plans/taskcards/TC-604_taskcard_closeout_tc520_tc522.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
- Reports (required):
  - reports/agents/<agent>/TC-604/report.md
  - reports/agents/<agent>/TC-604/self_review.md

## Acceptance checks
- [ ] TC-520 frontmatter status is "Done"
- [ ] TC-522 frontmatter status is "Done"
- [ ] TC-604 listed in INDEX.md
- [ ] STATUS_BOARD.md shows TC-520 and TC-522 as Done
- [ ] Only allowed paths modified
- [ ] All validation gates pass
- [ ] Evidence report documents verification

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
