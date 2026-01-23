---
id: TC-422
title: "W3.2 Snippet selection and normalization rules"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/workers/w3_snippet_curator/selection.py
  - tests/unit/workers/test_tc_422_snippet_selection.py
  - reports/agents/**/TC-422/**
evidence_required:
  - reports/agents/<agent>/TC-422/report.md
  - reports/agents/<agent>/TC-422/self_review.md
---

# Taskcard TC-422 — W3.2 Snippet selection and normalization rules

## Objective
Implement the deterministic selection rules that map snippet candidates to page-plan needs (feature coverage, runnable preference, asset constraints).

## Required spec references
- specs/05_example_curation.md
- specs/06_page_planning.md
- specs/10_determinism_and_caching.md
- specs/schemas/snippet_catalog.schema.json
- specs/schemas/page_plan.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Rules to pick “best” snippet(s) for a given feature/section deterministically
- Normalization rules for code formatting (indent, fences, language tags)
- Emitting Issues when no suitable snippet exists for a required claim group

### Out of scope
- Writing markdown pages (W5)
- Running snippets (validator gate)

## Inputs
- `RUN_DIR/artifacts/snippet_catalog.json`
- `RUN_DIR/artifacts/page_plan.json` (or planner output) specifying needed features/claims

## Outputs
- Selection mapping artifact (if defined) OR embedded selection fields within page_plan (as per schema)
- Issues for missing snippet coverage

## Allowed paths
- src/launch/workers/w3_snippet_curator/selection.py
- tests/unit/workers/test_tc_422_snippet_selection.py
- reports/agents/**/TC-422/**
## Implementation steps
1) Define selection scoring (deterministic tie-breakers):
   - runnable > non-runnable
   - closer feature tag match > broader
   - fewer required assets > more
   - stable tie-breaker by snippet_id
2) Normalize selected snippet presentation (fence + language tag + trimming rules).
3) Record selections with stable ordering.
4) Tests:
   - deterministic selection given equal candidates
   - missing coverage => Issue

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w3_snippet_curator.select --inventory artifacts/snippet_inventory.json
```

**Expected artifacts:**
- artifacts/snippet_catalog.json

**Success criteria:**
- [ ] Selection rules applied
- [ ] Output deterministic

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-421 (snippet inventory)
- Downstream: TC-430 (IAPlanner)
- Contracts: specs/05_example_curation.md selection rules

## Deliverables
- Code:
  - selection rules + normalization
- Tests:
  - tie-break determinism tests
- Reports (required):
  - reports/agents/<agent>/TC-422/report.md
  - reports/agents/<agent>/TC-422/self_review.md

## Acceptance checks
- [ ] selection rules are deterministic with stable tie-breakers
- [ ] missing required snippets emits Issues
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
