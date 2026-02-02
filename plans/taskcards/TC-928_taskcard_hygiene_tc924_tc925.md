---
id: TC-928
title: "Fix taskcard hygiene for TC-924 and TC-925"
status: In-Progress
priority: Critical
owner: "SUPERVISOR"
updated: "2026-02-02"
tags: ["hygiene", "taskcard", "gates"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-928_taskcard_hygiene_tc924_tc925.md
  - plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md
  - plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-928/**
evidence_required:
  - reports/agents/SUPERVISOR/TC-928/hygiene_fix.diff
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-928 — Fix taskcard hygiene for TC-924 and TC-925

## Objective
Add missing required sections to TC-924 and TC-925 taskcards to pass Gate A2 and Gate B validation, restoring validate_swarm_ready to 21/21 PASS.

## Problem Statement
validate_swarm_ready.py currently fails with 5/21 gates FAILED due to:

1. **TC-924** missing:
   - `## E2E verification` section
   - `## Integration boundary proven` section

2. **TC-925** has E2E and Integration sections but validator reports:
   - "E2E verification must specify expected artifacts"
   - "Integration boundary must specify upstream integration"
   - "Integration boundary must specify downstream integration"

3. **Both TC-924 and TC-925** missing from `plans/taskcards/INDEX.md`

## Required spec references
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format and required sections)
- tools/validate_swarm_ready.py (Gate A2 and Gate B validation logic)

## Scope

### In scope
- Add `## E2E verification` and `## Integration boundary proven` sections to TC-924
- Enhance TC-925's E2E and Integration sections to explicitly specify expected artifacts and integration points
- Add TC-924 and TC-925 entries to INDEX.md
- Update STATUS_BOARD.md if needed

### Out of scope
- Changing implementation logic in TC-924 or TC-925
- Modifying code files (this is pure taskcard hygiene)

## Allowed paths
- plans/taskcards/TC-928_taskcard_hygiene_tc924_tc925.md
- plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md
- plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-928/**

## Inputs
- TC-924 and TC-925 taskcard files (missing required sections)
- validate_swarm_ready.py output showing Gate A2 and Gate B failures
- INDEX.md (missing TC-924/TC-925 entries)
- plans/taskcards/00_TASKCARD_CONTRACT.md (reference for required sections)

## Outputs
- TC-924 with added sections: E2E verification, Integration boundary proven, Inputs, Outputs, Implementation steps, Deliverables, Acceptance checks, Self-review
- TC-925 with enhanced E2E and Integration sections (explicit artifacts and integration points)
- INDEX.md with TC-924, TC-925, TC-928 entries
- validate_swarm_ready.py output showing Gate A2 and Gate B PASS (or reduced failures)

## Implementation steps

### Step 1: Add missing sections to TC-924
Add after `## Success Criteria`:

```markdown
## E2E verification
Run full pilot VFV with both runs:
```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output report.json
```

Expected artifacts:
- VFV preflight PASS (no URL validation errors)
- Both pilots' GitHub repo URLs validated successfully
- Run 1 and Run 2 proceed past W1 (Repo Scout)

## Integration boundary proven
**Upstream:** VFV harness calls validate_github_url() before attempting git clone in W1.
**Downstream:** W1 Repo Scout receives validated GitHub URL and proceeds with shallow clone.
**Contract:** validate_github_url() returns ValidatedRepoUrl with is_legacy_pattern=True for both pilot URLs, allowing W1 to proceed.
```

### Step 2: Enhance TC-925 sections
The existing sections need explicit markers. Update TC-925's `## E2E verification` to:

```markdown
## E2E verification
Run full pilot VFV with both runs:
```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output report.json --goldenize
```

Expected artifacts:
- **artifacts/page_plan.json** in both run1 and run2 directories
- **artifacts/validation_report.json** in both run1 and run2 directories
- W4 log entries showing "Starting page planning for run <run_id>"
- W4 log entries showing "Page plan written successfully"
- No TypeError about missing config_path parameter
```

Update TC-925's `## Integration boundary proven` to:

```markdown
## Integration boundary proven
**Upstream integration:** W4 receives `run_config` dict from orchestrator graph via execute_ia_planner() parameter. Orchestrator loads config using load_and_validate_run_config(repo_root, config_path) and passes as dict.

**Downstream integration:** W4 uses RunConfig.from_dict(run_config) to convert to model object, then passes to determine_launch_tier() and plan_pages_for_section(). These functions consume launch_tier, product_facts, and platform fields.

**Contract:** W4 must NOT reload config from file when run_config parameter is provided (follows W2 pattern). Only reload if run_config is None.
```

### Step 3: Add to INDEX.md
Add entries in chronological order:

```markdown
| TC-924 | Add legacy FOSS pattern to repo URL validator | Critical | In-Progress | SUPERVISOR | 2026-02-01 |
| TC-925 | Fix W4 IAPlanner load_and_validate_run_config signature | Critical | In-Progress | SUPERVISOR | 2026-02-02 |
```

## Deliverables
- Updated TC-924 with E2E and Integration sections
- Updated TC-925 with enhanced E2E and Integration sections
- Updated INDEX.md with TC-924 and TC-925 entries
- validate_swarm_ready.py output showing 21/21 gates PASS

## Acceptance checks
1. Gate A2 PASS (no warnings)
2. Gate B PASS (TC-924 and TC-925 validated successfully)
3. TC-924 and TC-925 present in INDEX.md
4. validate_swarm_ready reports 21/21 PASS (or reduces failures from 5 to acceptable baseline)

## E2E verification
Run validate_swarm_ready.py:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py > runs\w6_fix_and_finish_vfv_20260202_215057\logs\validate_after_tc928.txt
```

Expected result:
- Gate A2: PASS (zero warnings)
- Gate B: PASS (TC-924 and TC-925 validated)
- Gate E: May still fail due to critical path overlap (addressed separately)
- Gate P: May still fail due to TC-681 (out of scope)
- Gate R: May still fail due to subprocess wrapper (out of scope)

## Integration boundary proven
**Upstream:** Gate A2 and Gate B validators parse taskcard markdown files looking for required section headers (`## E2E verification`, `## Integration boundary proven`).

**Downstream:** Once taskcards pass validation, they can be used to track implementation work and generate status reports.

**Contract:** All taskcards must include required sections per specs/37_taskcard_format.md. Missing sections cause Gate A2/B to fail and block validate_swarm_ready.

## Self-review
- [x] Only taskcard markdown files modified (no code changes)
- [x] TC-924 and TC-925 gain missing required sections
- [x] INDEX.md updated with both taskcard entries
- [x] Allowed paths strictly enforced (only taskcards and INDEX)
- [x] E2E verification specifies exact expected artifacts
- [x] Integration boundary specifies upstream/downstream/contract
