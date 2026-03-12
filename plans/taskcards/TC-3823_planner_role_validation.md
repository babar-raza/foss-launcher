---
id: TC-3823
title: "Planner self-review: validate page_role against skeleton registry"
status: In-Progress
priority: Normal
owner: agent
updated: "2026-03-07"
tags: [phase-7a, engineering-fix, planner, page-role]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3823_planner_role_validation.md
  - src/launcher/workers/planner/worker.py
  - tests/test_planner_worker.py
evidence_required:
  - reports/TC-3823/evidence.md
---

# Taskcard TC-3823 --- Planner self-review: validate page_role against skeleton registry

## Objective

Add page_role validation to the planner worker's self-review, catching invalid roles BEFORE generation runs. This is the early-catch layer complementing the defense-in-depth frontmatter gate (TC-3821).

## Required spec references

- `specs/worker_planner.md` (Section: Self-review -- validation checks)
- `src/launcher/shared/page_skeletons.py` (Section: PAGE_ROLE_SKELETONS -- canonical role registry)

## Scope

### In scope
- Add page_role validation in planner worker self-review
- Validate against `PAGE_ROLE_SKELETONS.keys()` from page_skeletons.py
- Tests for the validation

### Out of scope
- Changes to page_skeletons.py role definitions
- Frontmatter-side role validation (TC-3821)
- Template selection changes

## Inputs

- `PlanBundle` with list of `PlannedPage` objects, each with `page_role` field
- `PAGE_ROLE_SKELETONS` dict from `src/launcher/shared/page_skeletons.py`

## Outputs

- Self-review findings for pages with unregistered roles

## Allowed paths

- plans/taskcards/TC-3823_planner_role_validation.md
- src/launcher/workers/planner/worker.py
- tests/test_planner_worker.py

### Allowed paths rationale
- worker.py: Add role validation to existing self-review loop
- tests/: Unit tests for the new validation

## Implementation steps

### Step 1: Add role validation in planner self-review

In the self-review section of `worker.py` (after the existing thin_page check around line 88-94), add:

```python
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS
valid_roles = set(PAGE_ROLE_SKELETONS.keys())
for page in plan.pages:
    if page.page_role not in valid_roles:
        findings.append({
            "category": "invalid_role",
            "message": f"Page '{page.page_id}' has unregistered role '{page.page_role}'",
            "severity": "high",
        })
```

### Step 2: Write tests

- Test planner self-review rejects page with `page_role: "invented_role"`
- Test planner self-review accepts all 17 standard roles
- Test that the valid_roles set matches PAGE_ROLE_SKELETONS.keys()

## Failure modes

### Failure mode 1: Planner generates role not in PAGE_ROLE_SKELETONS

**Detection**: Self-review finding with category "invalid_role"
**Resolution**: Either add the role to PAGE_ROLE_SKELETONS (if legitimate) or fix the planner logic that produced it
**Gate**: Planner self-review

### Failure mode 2: _policy_kind_to_role returns unmapped role

**Detection**: Self-review catches it immediately after plan generation
**Resolution**: Add the missing mapping in `_policy_kind_to_role()` or add the role to PAGE_ROLE_SKELETONS
**Gate**: Planner self-review

### Failure mode 3: Import of PAGE_ROLE_SKELETONS adds startup overhead

**Detection**: Noticeable slowdown during planner import
**Resolution**: The import is already used by the planner (via resolve_skeleton). No additional overhead.
**Gate**: N/A

## Task-specific review checklist

1. [ ] Role validation added to planner self-review
2. [ ] Uses `PAGE_ROLE_SKELETONS.keys()` not hardcoded set
3. [ ] Finding severity is "high" for unregistered roles
4. [ ] Test covers invalid role rejection
5. [ ] Test covers valid role acceptance
6. [ ] No duplicate import of page_skeletons (check existing imports)

## Deliverables

1. Modified `src/launcher/workers/planner/worker.py`
2. New/updated tests in `tests/`

## Acceptance checks

1. [ ] Planner self-review produces finding for `page_role: "fake_role"`
2. [ ] Planner self-review passes for all 17 PAGE_ROLE_SKELETONS roles
3. [ ] All existing tests pass with PYTHONHASHSEED=0

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3823/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v -k "planner"
```

**Expected results**:
- Planner tests pass with new validation
- No regressions

## Integration boundary proven

**Upstream**: Ruleset YAML + `_policy_kind_to_role()` produce page_role values
**Downstream**: Generate worker's template_selector and skeleton resolver consume page_role
**Contract**: page_role is always a key in PAGE_ROLE_SKELETONS after planner self-review passes
