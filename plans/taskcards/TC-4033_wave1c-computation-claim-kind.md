---
id: TC-4033
title: "Wave 1C: Add computation claim kind to planner + understand"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-1]
depends_on: [TC-4031]
allowed_paths:
  - plans/taskcards/TC-4033_wave1c-computation-claim-kind.md
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/understand/extract/_deterministic.py
evidence_required:
  - reports/TC-4033/evidence.md
---

# Taskcard TC-4033 — Add computation claim kind

## Objective
Claims about formulas, calculation, and computation have no dedicated kind, so they get classified as "format" or "feature" and leak onto wrong pages. Add kind="computation" to route these claims to workflow_page and howto_article pages.

## Required spec references
- `crispy-growing-pebble.md` Wave 1C
- DEFECT-1 from human editorial review

## Scope
### In scope
- Add "computation" to _KIND_TO_ROLES in plan.py
- Add ("computation", [...]) to _KIND_PATTERNS in _deterministic.py
### Out of scope
- LLM-based claim extraction (LLM claims are already typed at extraction time)

## Inputs
- `src/launcher/workers/planner/plan.py` _KIND_TO_ROLES (line 111)
- `src/launcher/workers/understand/extract/_deterministic.py` _KIND_PATTERNS (line 20)

## Outputs
- plan.py: new "computation" entry in _KIND_TO_ROLES
- _deterministic.py: new pattern tuple for computation claims

## Allowed paths
- plans/taskcards/TC-4033_wave1c-computation-claim-kind.md
- src/launcher/workers/planner/plan.py
- src/launcher/workers/understand/extract/_deterministic.py

## Implementation steps
### Step 1: Add "computation" to _KIND_TO_ROLES in plan.py
### Step 2: Add computation pattern to _KIND_PATTERNS in _deterministic.py

## Failure modes
### Failure mode 1: Existing formula claims already classified as "format"
**Detection**: Old claims from prior runs still have kind="format"
**Resolution**: New pattern only applies to new understand runs; old runs need re-extraction
**Gate**: Not a regression — existing behavior unchanged for already-typed claims

### Failure mode 2: Computation pattern too broad, misclassifies non-formula claims
**Detection**: install/config claims typed as computation
**Resolution**: Use specific terms: "formula", "calculate", "compute", "math", "sum" — these are distinct
**Gate**: _KIND_PATTERNS is ordered; earlier patterns win

### Failure mode 3: No computation claims in cells repo
**Detection**: formula-calculation page still gets 0 relevant claims
**Resolution**: Valid evidence gap; page will get saturation warning; TC-4030/4031 are the primary fixes

## Task-specific review checklist
1. [ ] _KIND_TO_ROLES["computation"] = {"workflow_page", "howto_article", "comprehensive_guide"}
2. [ ] _KIND_PATTERNS entry: ("computation", ["formula", "calculate", "compute", "math", "sum"])
3. [ ] New entry inserted BEFORE "feature" fallback in _KIND_PATTERNS
4. [ ] Tests pass

## Deliverables
1. Updated src/launcher/workers/planner/plan.py
2. Updated src/launcher/workers/understand/extract/_deterministic.py

## Acceptance checks
1. [ ] "computation" in _KIND_TO_ROLES
2. [ ] _KIND_PATTERNS has computation tuple before feature fallback
3. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "planner or understand" --tb=short -q
```

## Integration boundary proven
**Upstream**: _deterministic.py classify_claim() → claim.kind = "computation"
**Downstream**: _assign_claims() eligible_kinds includes "computation" for workflow_page
**Contract**: claim.kind is a plain string; no schema enforcement needed
