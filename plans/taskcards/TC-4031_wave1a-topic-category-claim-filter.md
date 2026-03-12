---
id: TC-4031
title: "Wave 1A: Topic-category claim filter in _assign_claims()"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-1]
depends_on: [TC-4030]
allowed_paths:
  - plans/taskcards/TC-4031_wave1a-topic-category-claim-filter.md
  - src/launcher/workers/planner/plan.py
evidence_required:
  - reports/TC-4031/evidence.md
---

# Taskcard TC-4031 — Topic-category claim filter in _assign_claims()

## Objective
`_assign_claims()` uses only `page_role` for claim routing, ignoring `topic_category`. Add a keyword-based pre-filter so how-to-load pages only get load-related claims, formula-calculation pages only get computation/formula claims, etc.

## Required spec references
- `crispy-growing-pebble.md` Wave 1A
- `specs/rulesets/ruleset.yaml` (topic_category values)

## Scope
### In scope
- Add `_TOPIC_KEYWORDS` dict to plan.py
- Add topic_category filter in `_assign_claims()` loop (line 1031)
### Out of scope
- Changing eligible_kinds logic (Wave 1B handles format claims separately)

## Inputs
- `src/launcher/workers/planner/plan.py` _assign_claims() function

## Outputs
- Updated plan.py with topic_category-aware claim filtering

## Allowed paths
- plans/taskcards/TC-4031_wave1a-topic-category-claim-filter.md
- src/launcher/workers/planner/plan.py

## Implementation steps
### Step 1: Add _TOPIC_KEYWORDS constant near top of plan.py (after _KIND_TO_ROLES)
### Step 2: In _assign_claims() loop, after eligible_kinds check, add topic_category filter

## Failure modes
### Failure mode 1: All claims filtered out for a page
**Detection**: page gets 0 assigned_claims → boilerplate content
**Resolution**: Filter is AND-gated with eligible_kinds; if page has no matching claims, it's an evidence gap, not a bug
**Gate**: Saturation warning fires, honest outcome

### Failure mode 2: topic_category not in _TOPIC_KEYWORDS silently skips filter
**Detection**: pages with unknown topic_category get all claims (as before)
**Resolution**: Accept this — filter is additive, not breaking

### Failure mode 3: Keyword set too narrow misses relevant claims
**Detection**: Correct claims excluded by keyword filter
**Resolution**: Expand _TOPIC_KEYWORDS entries as needed after pilot run

## Task-specific review checklist
1. [ ] _TOPIC_KEYWORDS covers all topic_category values in ruleset.yaml
2. [ ] Filter only activates when page has topic_category AND category in _TOPIC_KEYWORDS
3. [ ] Filter is applied after eligible_kinds check (not instead of it)
4. [ ] Existing tests pass
5. [ ] Unit test for filter logic added
6. [ ] "formula_calculation" keywords include formula, calculate, compute

## Deliverables
1. Updated src/launcher/workers/planner/plan.py

## Acceptance checks
1. [ ] how-to-load page gets only load/open/read/parse/import claims
2. [ ] formula-calculation page gets only formula/calculate/compute claims
3. [ ] Pages with no topic_category get all eligible_kinds claims (unchanged)
4. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "planner" --tb=short -q
```

## Integration boundary proven
**Upstream**: page dicts with topic_category → _assign_claims()
**Downstream**: PlannedPage.assigned_claims → generate worker
**Contract**: assigned_claims is a list of claim_id strings
