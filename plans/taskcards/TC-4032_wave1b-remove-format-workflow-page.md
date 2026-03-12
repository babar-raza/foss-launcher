---
id: TC-4032
title: "Wave 1B: Remove workflow_page from _KIND_TO_ROLES[format]"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-1]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4032_wave1b-remove-format-workflow-page.md
  - src/launcher/workers/planner/plan.py
evidence_required:
  - reports/TC-4032/evidence.md
---

# Taskcard TC-4032 — Remove workflow_page from _KIND_TO_ROLES["format"]

## Objective
PDF/format-conversion claims (kind="format") currently eligible for workflow_page roles, causing formula-calculation pages to receive PDF content. Remove workflow_page from the format kind's eligible roles.

## Required spec references
- `crispy-growing-pebble.md` Wave 1B
- DEFECT-1 from human editorial review

## Scope
### In scope
- Remove `"workflow_page"` from `_KIND_TO_ROLES["format"]` set
### Out of scope
- Other claim kinds or role assignments

## Inputs
- `src/launcher/workers/planner/plan.py` line 68-70

## Outputs
- Updated plan.py: `"format": {"format_conversion", "feature_showcase"}`

## Allowed paths
- plans/taskcards/TC-4032_wave1b-remove-format-workflow-page.md
- src/launcher/workers/planner/plan.py

## Implementation steps
### Step 1: Remove "workflow_page" from _KIND_TO_ROLES["format"]

## Failure modes
### Failure mode 1: spreadsheet-operations page loses format claims
**Detection**: spreadsheet-operations gets 0 format claims
**Resolution**: If spreadsheet-operations needs format claims, give it topic_category: "spreadsheet_ops" and add broader keywords. But it should get workflow claims instead.
**Gate**: TC-4031 topic filter is the right mechanism, not this

### Failure mode 2: format_conversion pages unaffected
**Detection**: format_conversion pages still get format claims (correct behavior)
**Resolution**: No action needed

### Failure mode 3: Feature showcase pages still get format claims
**Detection**: feature_showcase gets PDF claims (acceptable — landing/showcase pages do cover formats)
**Resolution**: No action needed

## Task-specific review checklist
1. [ ] Line 68-70 in plan.py: workflow_page removed from format set
2. [ ] format_conversion and feature_showcase remain in format set
3. [ ] All tests pass
4. [ ] Confirm format_conversion role still gets format claims

## Deliverables
1. Updated src/launcher/workers/planner/plan.py (1-line change)

## Acceptance checks
1. [ ] `"workflow_page" not in _KIND_TO_ROLES["format"]`
2. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "planner" --tb=short -q
```

## Integration boundary proven
**Upstream**: claim.kind = "format" → _assign_claims()
**Downstream**: PlannedPage.assigned_claims (format claims no longer on workflow_page)
**Contract**: _KIND_TO_ROLES is a pure data structure with no side effects
