---
id: TC-603
title: "Taskcard status hygiene - correct TC-520 and TC-522 status"
status: In-Progress
owner: "HYGIENE_AGENT"
updated: "2026-01-29"
depends_on: []
allowed_paths:
  - plans/taskcards/TC-520_pilots_and_regression.md
  - plans/taskcards/TC-522_pilot_e2e_cli.md
  - plans/taskcards/INDEX.md
  - reports/agents/**/TC-603/**
evidence_required:
  - reports/agents/<agent>/TC-603/report.md
  - reports/agents/<agent>/TC-603/self_review.md
spec_ref: 718bca53173dd5e27a819d24a63e9afbd303b709
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-603 — Taskcard status hygiene

## Objective
Correct the status of TC-520 and TC-522 from "Done" to "In-Progress" because required evidence deliverables are missing, ensuring taskcard statuses accurately reflect completion state per the taskcard contract.

## Required spec references
- plans/taskcards/00_TASKCARD_CONTRACT.md (Definition of done, lines 105-109)
- specs/09_validation_gates.md (Gate B - taskcard validation)

## Scope
### In scope
- Change TC-520 frontmatter status from "Done" to "In-Progress"
- Change TC-522 frontmatter status from "Done" to "In-Progress"
- Add TC-603 to INDEX.md in appropriate location
- Document before/after status changes with evidence

### Out of scope
- Implementing the missing deliverables for TC-520 or TC-522
- Modifying STATUS_BOARD.md directly (it is auto-generated)
- Changing any runtime code
- Modifying any shared libraries

## Inputs
- plans/taskcards/TC-520_pilots_and_regression.md (current status: Done)
- plans/taskcards/TC-522_pilot_e2e_cli.md (current status: Done)
- plans/taskcards/00_TASKCARD_CONTRACT.md (definition of done)
- plans/taskcards/INDEX.md

## Outputs
- TC-520 with status: In-Progress
- TC-522 with status: In-Progress
- INDEX.md updated with TC-603 entry
- Evidence report with before/after excerpts

## Allowed paths
- plans/taskcards/TC-520_pilots_and_regression.md
- plans/taskcards/TC-522_pilot_e2e_cli.md
- plans/taskcards/INDEX.md
- reports/agents/**/TC-603/**

### Allowed paths rationale
This task corrects taskcard status fields to reflect actual completion state per the taskcard contract definition of done. It requires modifying TC-520 and TC-522 frontmatter status fields, updating INDEX.md to register this new taskcard, and producing evidence reports.

## Preconditions / dependencies
- None (this is a hygiene taskcard)

## Implementation steps
1) Read TC-520 and TC-522 to capture current frontmatter status (Done)
2) Edit TC-520: Change `status: Done` to `status: In-Progress` in frontmatter only
3) Edit TC-522: Change `status: Done` to `status: In-Progress` in frontmatter only
4) Read INDEX.md and add TC-603 entry in "Additional critical hardening" section
5) Create evidence report with:
   - Before/after frontmatter excerpts (lines 1-23 only)
   - Git diff output showing exact changes
   - Justification based on taskcard contract definition of done

## Test plan
- Validate changes with git diff
- Verify frontmatter-only changes (no body modifications)
- Run `python tools/validate_taskcards.py` to ensure taskcards still validate
- Check that STATUS_BOARD.md reflects changes after regeneration (informational only)

## E2E verification
**Concrete command(s) to run:**
```bash
git diff plans/taskcards/TC-520_pilots_and_regression.md
git diff plans/taskcards/TC-522_pilot_e2e_cli.md
git diff plans/taskcards/INDEX.md
python tools/validate_taskcards.py
```

**Expected artifacts:**
- Modified files: TC-520_pilots_and_regression.md, TC-522_pilot_e2e_cli.md, INDEX.md
- reports/agents/HYGIENE_AGENT/TC-603/report.md
- reports/agents/HYGIENE_AGENT/TC-603/self_review.md

**Expected output:**
- Diffs show only frontmatter status changes (line 4 in each file)
- validate_taskcards.py passes (all taskcards valid)

**Success criteria:**
- [ ] TC-520 status changed to In-Progress in frontmatter
- [ ] TC-522 status changed to In-Progress in frontmatter
- [ ] TC-603 added to INDEX.md
- [ ] No other changes made
- [ ] Taskcard validation passes

## Integration boundary proven
- Upstream: Taskcard contract enforcement (definition of done)
- Downstream: STATUS_BOARD.md auto-generation will reflect corrected statuses
- Contracts: Taskcard frontmatter schema, definition of done

## Failure modes

### Failure mode 1: Accidentally modify taskcard body content
**Detection:** Git diff shows changes beyond frontmatter status field; body sections modified unintentionally
**Resolution:** Revert and re-apply edit to frontmatter only (lines 1-23 typically); use precise Edit tool old_string matching to target only YAML frontmatter
**Spec/Gate:** plans/taskcards/00_TASKCARD_CONTRACT.md (write fence rule)

### Failure mode 2: Taskcard validation fails after status change
**Detection:** `python tools/validate_taskcards.py` exits non-zero after status update
**Resolution:** Review validation error message; ensure frontmatter fields remain valid YAML syntax; verify status value is one of allowed enum (Done, In-Progress, Blocked, Cancelled); check all required frontmatter keys still present
**Spec/Gate:** specs/09_validation_gates.md (Gate B - taskcard validation)

### Failure mode 3: STATUS_BOARD.md manually edited instead of auto-regenerated
**Detection:** Git diff shows STATUS_BOARD.md changes directly; board doesn't reflect latest frontmatter statuses
**Resolution:** Revert STATUS_BOARD.md changes; it will auto-regenerate from taskcard frontmatter via Gate C; never manually edit STATUS_BOARD.md (header warns "auto-generated, do not edit")
**Spec/Gate:** STATUS_BOARD.md header (auto-generated), specs/09_validation_gates.md (Gate C)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Only frontmatter status field changed (line 4 in TC-520 and TC-522)
- [ ] No body content changed in TC-520 or TC-522
- [ ] TC-603 added to INDEX.md in appropriate section
- [ ] Git diff output captured in evidence report
- [ ] Before/after excerpts included in evidence report
- [ ] Justification cites taskcard contract definition of done
- [ ] No changes to STATUS_BOARD.md (will auto-regenerate)
- [ ] Taskcard validation still passes

## Deliverables
- Modified files:
  - plans/taskcards/TC-520_pilots_and_regression.md
  - plans/taskcards/TC-522_pilot_e2e_cli.md
  - plans/taskcards/INDEX.md
- Reports (required):
  - reports/agents/<agent>/TC-603/report.md
  - reports/agents/<agent>/TC-603/self_review.md

## Acceptance checks
- [ ] TC-520 frontmatter status is "In-Progress"
- [ ] TC-522 frontmatter status is "In-Progress"
- [ ] TC-603 listed in INDEX.md
- [ ] Only allowed paths modified
- [ ] Evidence report includes before/after excerpts and git diffs
- [ ] Taskcard validation passes

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
