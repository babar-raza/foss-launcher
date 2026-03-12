---
id: TC-4030
title: "Gap 1: Add topic_category to ruleset.yaml family_override entries"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-1]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4030_gap1-ruleset-topic-category.md
  - specs/rulesets/ruleset.yaml
evidence_required:
  - reports/TC-4030/evidence.md
---

# Taskcard TC-4030 — Add topic_category to ruleset family_override entries

## Objective
Family-override workflow pages (formula-calculation, spreadsheet-operations, etc.) have no `topic_category`, so the topic-category claim filter (TC-4031) never fires for them. Add `topic_category` to each family_override workflow_page entry so claim routing can be restricted by topic.

## Required spec references
- `specs/rulesets/ruleset.yaml` (family_overrides section)
- `crispy-growing-pebble.md` Gap 1

## Scope
### In scope
- Add `topic_category` fields to all family_override `workflow_page` entries in ruleset.yaml
### Out of scope
- Adding new pages or changing page_role assignments

## Inputs
- `specs/rulesets/ruleset.yaml` (current family_overrides section)

## Outputs
- Updated `specs/rulesets/ruleset.yaml` with topic_category on every workflow_page family_override entry

## Allowed paths
- plans/taskcards/TC-4030_gap1-ruleset-topic-category.md
- specs/rulesets/ruleset.yaml

### Allowed paths rationale
Ruleset drives page enumeration; adding topic_category is schema-compatible (optional field).

## Implementation steps
### Step 1: Add topic_category to cells family_override workflow_page entries
### Step 2: Add topic_category to note, 3d, words, pdf, slides family_override entries

## Failure modes
### Failure mode 1: Unknown topic_category value breaks _TOPIC_KEYWORDS lookup
**Detection**: Claim filter skips all claims for the page
**Resolution**: Ensure _TOPIC_KEYWORDS has an entry for the value, or use None to skip filtering
**Gate**: TC-4031 filter silently no-ops on unknown categories

### Failure mode 2: Duplicate topic_category across pages confuses routing
**Detection**: Two workflow_pages in same family get same claims
**Resolution**: Use distinct topic_category values per page

### Failure mode 3: Schema validation rejects new field
**Detection**: schema_validation.py raises on ruleset load
**Resolution**: Field is optional in schema; verify schema allows additional fields

## Task-specific review checklist
1. [ ] Every cells workflow_page family_override entry has topic_category
2. [ ] Every note, 3d, words, pdf, slides entry has topic_category
3. [ ] topic_category values are in _TOPIC_KEYWORDS (TC-4031) or None
4. [ ] Tests still pass (ruleset loading not broken)
5. [ ] No existing entries modified except topic_category addition
6. [ ] Values use snake_case consistently

## Deliverables
1. Updated specs/rulesets/ruleset.yaml
2. reports/TC-4030/evidence.md

## Acceptance checks
1. [ ] All workflow_page family_override entries have topic_category field
2. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "ruleset or planner" --tb=short -q
```

## Integration boundary proven
**Upstream**: ruleset.yaml → _enumerate_mandatory_pages() → page dicts
**Downstream**: page dicts → _assign_claims() reads topic_category
**Contract**: topic_category is an optional str field on page dicts
