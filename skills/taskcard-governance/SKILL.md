---
name: taskcard-governance
description: Use this skill before making any code changes in foss-launcher. It enforces the taskcard-first workflow by guiding you through creating or finding a taskcard, setting it to In-Progress, and verifying coverage. Activate whenever the user asks to fix a bug, add a feature, refactor code, update tests, modify workers, change specs, or make any source code changes — even if they don't mention taskcards. Also activate when the user says "create a taskcard" or "what taskcard do I need."
---

# Taskcard Governance — Enforcement Skill

This skill enforces foss-launcher's taskcard-first governance model. Every code change
must be traceable to an In-Progress taskcard before any files are modified.

## Taskcard-First Decision Tree

When the user requests a code change, follow this decision tree:

```
User requests a code change
  |
  +-- Search plans/taskcards/ for relevant TC-*.md
  |     |
  |     +-- Found with status "In-Progress"
  |     |     -> Verify allowed_paths cover the files you need to modify
  |     |     -> If covered: reference the taskcard and proceed
  |     |     -> If not covered: update allowed_paths, re-validate, then proceed
  |     |
  |     +-- Found with status "Draft" or "Ready"
  |     |     -> Set status to "In-Progress"
  |     |     -> Verify allowed_paths, update if needed
  |     |     -> Run: python tools/validate_taskcards.py
  |     |     -> Proceed
  |     |
  |     +-- Found with status "Done"
  |     |     -> Do NOT reuse. Create a NEW taskcard for the new work.
  |     |
  |     +-- Not found
  |           -> Create a new taskcard (see "Creating a Taskcard" below)
  |
  +-- Never skip this step unless the user explicitly says "skip the taskcard"
```

## Creating a Taskcard

### Option A: Interactive Script (Recommended)

```bash
python scripts/create_taskcard.py
```

Follow the prompts to set TC number, title, and paths.

### Option B: Manual Creation

Copy the template and fill in all required fields:

```bash
cp plans/_templates/taskcard.md plans/taskcards/TC-<NUMBER>_<slug>.md
```

### Required Frontmatter Fields (all 14)

```yaml
---
id: TC-<NUMBER>
title: "<descriptive title>"
status: In-Progress
owner: "<agent or human>"
updated: "<YYYY-MM-DD>"
depends_on: []
allowed_paths:
  - <specific file or glob pattern>
evidence_required:
  - <path to evidence file>
spec_ref: "<7-40 hex chars commit SHA>"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---
```

### Required Body Sections (all 14)

Every taskcard must contain these sections:

1. `## Objective`
2. `## Required spec references`
3. `## Scope` (with `### In scope` and `### Out of scope`)
4. `## Inputs`
5. `## Outputs`
6. `## Allowed paths`
7. `## Implementation steps`
8. `## Failure modes` (minimum 3, each with detection signal + resolution + spec/gate link)
9. `## Task-specific review checklist` (minimum 6 items)
10. `## Deliverables`
11. `## Acceptance checks`
12. `## Self-review`
13. `## E2E verification` (concrete commands, expected artifacts)
14. `## Integration boundary proven` (upstream/downstream explicitly documented)

### Validate

Always validate after creating or modifying a taskcard:

```bash
python tools/validate_taskcards.py
```

## Allowed Paths Rules

The `allowed_paths` field defines the write fence for a taskcard. Only modify files
that match these patterns.

### Principles

- List only the specific paths this taskcard needs — no ultra-broad patterns
- Glob patterns are allowed: `src/launch/workers/w10_fixer/**`, `tests/unit/workers/test_w10*.py`
- Always include the taskcard file itself: `plans/taskcards/TC-<NUMBER>*.md`
- Always include the reports path: `reports/agents/<agent>/TC-<NUMBER>/**`

### Shared Library Restrictions

These directories have single designated owners. Do not add them to your taskcard
unless you are working on the owning taskcard:

| Path | Owner |
|------|-------|
| `src/launch/io/**` | TC-200 |
| `src/launch/util/**` | TC-200 |
| `src/launch/models/**` | TC-250 |
| `src/launch/clients/**` | TC-500 |

### Blocked Patterns

The validator rejects overly broad patterns:
- `src/**`, `tests/**`, `scripts/**`, `.github/**`
- These catch too many files and defeat the purpose of the write fence

## Completion Rules

Before setting a taskcard's status to "Done":

1. All acceptance criteria items are checked: `[x]` (not `[ ]`)
2. All evidence files exist at the paths listed in `evidence_required`
3. Evidence files are non-trivial (>100 bytes, not stubs)
4. No pending markers remain: `TODO`, `FIXME`, `Deferred`
5. E2E verification section has concrete commands with actual results
6. Integration boundary section documents upstream and downstream impacts
7. For W2/W4/W5/W7/W9 changes: pilot run results must be documented

Only then: set `status: Done` and `updated: <today>`.

## Guardrails

- Never make code changes without an active In-Progress taskcard
- Never mark a taskcard "Done" with unchecked acceptance criteria
- Never use `git commit --no-verify` to bypass the pre-commit hook
  (CI/CD detects bypasses and blocks the PR)
- Never use ultra-broad `allowed_paths` patterns
- If the user explicitly says "skip the taskcard" — note the exception but comply
- Reading existing code is always allowed regardless of `allowed_paths`
  (the write fence only restricts modifications)

## Reference Files

- Contract: `plans/taskcards/00_TASKCARD_CONTRACT.md`
- Template: `plans/_templates/taskcard.md`
- Governance spec: `specs/30_ai_agent_governance.md`
- Validator source: `tools/validate_taskcards.py`
- Coverage checker: `tools/check_taskcard_coverage.py`
- AI rules: `.claude_code_rules`
