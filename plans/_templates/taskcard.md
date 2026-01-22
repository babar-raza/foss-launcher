---
id: __TASK_ID__
title: "__TITLE__"
status: Draft
owner: "unassigned"
updated: "__YYYY-MM-DD__"
depends_on: []
allowed_paths:
  - __PATH_1__
  - __PATH_2__
  - reports/agents/**/__TASK_ID__/**
evidence_required:
  - reports/agents/<agent>/__TASK_ID__/report.md
  - reports/agents/<agent>/__TASK_ID__/self_review.md
---

# Taskcard __TASK_ID__ — __TITLE__

## Objective
State the **single, measurable** outcome this task delivers.

## Required spec references
List **binding** specs the agent MUST read before writing code. Use repo-relative paths only.
- __SPEC_PATH_1__
- __SPEC_PATH_2__

## Scope
### In scope
- __ITEM__
### Out of scope
- __ITEM__

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue (see Deliverables) and stop that path.
- **Write fence:** you MAY ONLY change files under **Allowed paths** below.
- **Determinism:** no time-based behavior or content; stable ordering; stable serialization.
- **Evidence:** any decision that narrows ambiguous behavior must be tied to a spec reference (or recorded as a blocker).

## Preconditions / dependencies
- What must already exist (other taskcards completed, files present, services reachable).

## Inputs
- Required files/dirs and their expected state.
- Required environment (Python version, CLI tools) if applicable.
- External services (telemetry/commit service) and fallback behavior if applicable.

## Outputs
List exact files/artifacts this task MUST produce (with schema constraints if applicable).

## Allowed paths
- __PATH_1__
- __PATH_2__
- reports/agents/**/__TASK_ID__/**

### Allowed paths rationale
(Optional: Add explanation for why these specific paths are needed. Do NOT list additional paths here - only explanations for the paths listed above which must exactly match the frontmatter `allowed_paths` list.)

## Implementation steps
1) __STEP__
2) __STEP__

## Test plan
- Unit tests to add:
- Integration tests to add:
- Determinism proof (what is compared, how):

## Deliverables
- Code:
- Tests:
- Docs/specs/plans (if any):
- Reports (required):
  - reports/agents/__AGENT__/__TASK_ID__/report.md
  - reports/agents/__AGENT__/__TASK_ID__/self_review.md
  - (if blocked) reports/agents/__AGENT__/__TASK_ID__/blockers/<timestamp>_<slug>.issue.json  (must validate against specs/schemas/issue.schema.json)

## Acceptance checks
- [ ] All acceptance criteria in this taskcard are met
- [ ] Tests added and passing (list commands in the agent report)
- [ ] Determinism concerns addressed (and demonstrated)
- [ ] Schemas validated where applicable
- [ ] Reports are written and include commands + outputs
- [ ] Self-review 12D written; any dimension <4 includes a concrete fix plan

## Self-review
Use `reports/templates/self_review_12d.md`.
