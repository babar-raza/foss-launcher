# runbooks/taskcards.md (FOSS Launcher v2)

Use this **before** making changes to app core / production paths.

Aligned to: `.claude_code_rules` (AG-002), `CLAUDE.md` (Taskcard-First Workflow)

## 1) Decide if a taskcard is required

Taskcard is **REQUIRED** if you will edit any of:
- `src/launcher/**`
- `configs/**`
- `specs/schemas/**`
- any gate/CI enforcement scripts if present

If you will only edit docs outside production paths, taskcard is optional.

## 2) Create the taskcard file

Target path + naming: `plans/taskcards/TC-<id>_<slug>.md`

**Start from template:**
```bash
cp plans/taskcards/TC-000_TEMPLATE.md plans/taskcards/TC-<id>_<slug>.md
```

Replace all `TC-NNNN` placeholders with your actual TC number.

## 3) Fill frontmatter correctly (MUST)

Required frontmatter fields:
- `id`: TC-NNNN
- `title`: quoted descriptive string
- `status`: Draft | In-Progress | Done
- `priority`: Normal | High | Critical
- `owner`: agent or human name
- `updated`: quoted string `"YYYY-MM-DD"`
- `tags`: list of tags
- `depends_on`: list of TC IDs (or empty)
- `allowed_paths`: list of glob patterns (MUST match body section exactly)
- `evidence_required`: list of repo-relative paths (NOT boolean)

## 4) The 14 mandatory body sections

Every taskcard MUST contain all 14 sections. The template has them pre-filled:

| # | Section | Minimum requirement |
|---|---------|-------------------|
| 1 | `## Objective` | 1-2 sentence outcome |
| 2 | `## Required spec references` | specs with section numbers |
| 3 | `## Scope` | `### In scope` + `### Out of scope` subsections |
| 4 | `## Inputs` | files/data consumed |
| 5 | `## Outputs` | files/artifacts produced |
| 6 | `## Allowed paths` | must match frontmatter exactly |
| 7 | `## Implementation steps` | numbered with commands + expected output |
| 8 | `## Failure modes` | **minimum 3**, each with Detection + Resolution + Gate |
| 9 | `## Task-specific review checklist` | **minimum 6 items** |
| 10 | `## Deliverables` | concrete files at specific paths |
| 11 | `## Acceptance checks` | measurable criteria (all `[x]` for Done) |
| 12 | `## Self-review` | verification results |
| 13 | `## E2E verification` | concrete commands with actual results |
| 14 | `## Integration boundary proven` | upstream/downstream contracts |

## 5) Set status to In-Progress before core edits

Draft status is NOT authorized for writes. You must:
1. Fill all 14 body sections
2. Set `status: In-Progress`
3. Get user approval
4. Only then write code

## 6) Allowed paths guidance

Examples:
- Exact file: `configs/pipeline.yaml`
- Recursive: `src/launcher/util/**`
- Patterned worker: `src/launcher/workers/evaluate/**`

All files you modify MUST match at least one `allowed_paths` pattern.

**Shared library restrictions** — only add with explicit justification:

| Path | Typical Owner |
|------|---------------|
| `src/launcher/io/**` | Infrastructure TC |
| `src/launcher/models/**` | Models TC |
| `src/launcher/clients/**` | Clients TC |
| `src/launcher/util/**` | Utilities TC |

## 7) Completion — Pre-Done Validation

Before updating status from "In-Progress" to "Done", **YOU MUST** verify ALL:

### A. Acceptance Checks State
- [ ] Every acceptance item is `[x]` (not `[ ]`)
- [ ] No pending markers: `TODO`, `FIXME`, `Deferred`, `Pending`
- [ ] If any item unchecked or pending: **CANNOT mark Done**

### B. Evidence Files Existence
- [ ] Every `evidence_required` file exists on disk (>= 100 bytes)
- [ ] No evidence file contains "Pending", "TODO", "Not executed"
- [ ] If any evidence missing or incomplete: **CANNOT mark Done**

### C. E2E Verification (Critical Workers)

If taskcard modifies Understand, Generate, Evaluate, or Publish workers:
- [ ] `## E2E verification` contains actual execution results
- [ ] Pilot runs executed and passed
- [ ] If pilots not executed or failed: **CANNOT mark Done**

### D. Test Results
- [ ] All tests pass with `PYTHONHASHSEED=0`
- [ ] New code has test coverage
- [ ] If tests fail: **CANNOT mark Done**

### Summary

**"Completed" means "Executed":**
- Commands **RUN** (not just documented)
- Results **CAPTURED** (exit codes, metrics)
- Artifacts **COMMITTED**
- NOT "will run later" or "section exists with examples"

**"Acceptance checks satisfied" means:**
- ALL items `[x]`
- Evidence EXISTS and is complete
- Zero PENDING markers

When in doubt: **RUN THE PILOTS**.

## 8) Decision tree for agents

```
User requests code change
  |
  +-- Is the change in a taskcard-required path?
  |     |
  |     +-- YES: Search plans/taskcards/ for relevant TC-*.md
  |     |     |
  |     |     +-- Found In-Progress -> verify allowed_paths -> proceed
  |     |     +-- Found Draft -> fill sections, set In-Progress, get approval
  |     |     +-- Found Done -> create NEW taskcard (never reuse Done)
  |     |     +-- Not found -> create from TC-000_TEMPLATE.md
  |     |
  |     +-- NO: proceed (but consider tracking formally)
  |
  +-- NEVER skip unless user explicitly says "skip the taskcard"
```
